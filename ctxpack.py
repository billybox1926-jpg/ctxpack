#!/usr/bin/env python3
"""
ctxpack - Dependency-free repo-to-prompt pack builder.
"""

# Postponed annotation evaluation: the signatures below use `str | None` and
# builtin generics, which are 3.10+ syntax when evaluated eagerly. This keeps
# the module importable on Python 3.9, which pyproject.toml and the CI matrix
# both claim to support.
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
import re
from pathlib import Path

DEFAULT_BUDGET_TOKENS = 8000
DEFAULT_IGNORE_FILE = ".ctxignore"
DEFAULT_CONFIG_FILE = "ctxpack.json"
DEFAULT_BASE_NAME = "ctxpack"
DEFAULT_OUTPUT_DIR = "."

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".exe", ".dll",
    ".so", ".dylib", ".zip", ".tar", ".gz", ".7z", ".pyc", ".class",
    ".o", ".obj", ".bin", ".woff", ".woff2", ".ttf", ".eot"
}

MAX_FILE_BYTES = 500_000  # skip files larger than ~500KB by default

def load_config(root: Path) -> dict:
    """Load config from ctxpack.json if it exists."""
    config_path = root / DEFAULT_CONFIG_FILE
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def load_ignore_patterns(root: Path, cli_exclude: list[str]) -> list[str]:
    """Load patterns from .ctxignore, merged with CLI excludes."""
    default_patterns = [
        ".git/**", ".svn/**", ".hg/**",
        "__pycache__/**", "*.pyc", "*.pyo",
        "node_modules/**", "venv/**", ".venv/**",
        "dist/**", "build/**",
        ".ruff_cache/**", ".pytest_cache/**", ".mypy_cache/**",
        ".tox/**", ".eggs/**", "*.egg-info/**", "htmlcov/**",
        ".coverage", ".coverage.*",
        "*.log", "*.lock", "package-lock.json",
        ".DS_Store", "Thumbs.db", 
        DEFAULT_CONFIG_FILE, f"{DEFAULT_BASE_NAME}.context.json", f"{DEFAULT_BASE_NAME}.context.md",
        # Secret-bearing files: exclude by default for security
        ".env",
        ".env.*",
        "!.env.example",
        "*.pem",
        "*.key",
        "*.p12",
        "*.pfx"
    ]
    ignore_file = root / DEFAULT_IGNORE_FILE
    patterns = list(default_patterns)
    
    if ignore_file.exists():
        with ignore_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
                    
    # CLI excludes take precedence and are appended
    patterns.extend(cli_exclude)
    return patterns

def matches_pattern(rel: str, name: str, pattern: str) -> bool:
    """Check if a path matches a gitignore-style pattern.
    
    Supported semantics (documented subset of gitignore):
    - Bare patterns (e.g., `*.log`) match by filename anywhere in tree
    - Patterns with `/` are matched against relative path from root
    - Leading `/` anchors pattern to root (currently treated same as without for simplicity)
    - Trailing `/` matches directories only (currently stripped for matching)
    - `**` matches zero or more directory levels
    - `dir/**` matches everything inside dir (including dir itself)
    - Negation patterns (`!foo`) handled in should_process(), not here
    
    Note: This is a simplified subset of full gitignore semantics. See README
    for exactly which patterns are supported.
    """
    pat = pattern.rstrip("/")
    
    # Handle ** in patterns first (most general case)
    if "**" in pat:
        # Convert gitignore-style ** to regex
        # ** matches zero or more directory components
        regex_pat = re.escape(pat)
        regex_pat = regex_pat.replace(r"\*\*", ".*")  # ** -> .*
        regex_pat = regex_pat.replace(r"\*", "[^/]*")  # * -> [^/]*
        regex = "^" + regex_pat + "$"
        if re.match(regex, rel):
            return True
        
        # For patterns like **/*.ext, also allow matching at root level
        # where ** matches zero directories
        if pat.startswith("**/"):
            suffix = pat[3:]  # Remove **/
            # Try matching the suffix as a bare pattern
            if "/" not in suffix:
                # It's just a filename pattern like *.log
                if fnmatch.fnmatch(name, suffix):
                    return True
    
    # Exact relative path match
    if fnmatch.fnmatch(rel, pat):
        return True
    
    # Recursive directory match (e.g., ".git/config" matching ".git/**")
    if fnmatch.fnmatch(rel, pat + "/**"):
        return True
    
    # A "dir/**" pattern must also match the directory itself and its contents
    if pat.endswith("/**"):
        base = pat[:-3]
        if fnmatch.fnmatch(rel, base) or rel.startswith(base + "/"):
            return True
    
    # Bare filename match (e.g., "*.log") - matches anywhere in tree
    # Only do this if pattern has no path separators (after stripping leading /)
    pat_clean = pat.lstrip("/")
    if "/" not in pat_clean:
        if fnmatch.fnmatch(name, pat_clean):
            return True
    
    # Pattern with slash: match against full relative path
    if "/" in pat_clean:
        if fnmatch.fnmatch(rel, pat_clean):
            return True
    
    return False

def should_process(path: Path, root: Path, include_patterns: list[str], exclude_patterns: list[str]) -> bool:
    """Determine if a file should be processed based on include/exclude rules.
    
    Supports gitignore-style negation patterns: patterns starting with '!' 
    re-include files that matched a previous exclusion pattern.
    """
    rel = path.relative_to(root).as_posix()
    name = path.name
    
    # Track whether the file has been excluded so far
    is_excluded = False
    
    # Process patterns in order, allowing negation patterns to re-include
    for pat in exclude_patterns:
        if pat.startswith("!"):
            # Negation pattern: re-include if it matches
            neg_pat = pat[1:]
            if is_excluded and matches_pattern(rel, name, neg_pat):
                is_excluded = False
        else:
            # Normal exclusion pattern
            if matches_pattern(rel, name, pat):
                is_excluded = True
    
    if is_excluded:
        return False
            
    # 2. If no include patterns, everything not excluded is included
    if not include_patterns:
        return True
        
    # 3. Must match at least one include pattern
    for pat in include_patterns:
        if matches_pattern(rel, name, pat):
            return True
            
    return False

def estimate_tokens(text: str) -> int:
    """Estimate token count for text content.
    
    Uses a simple heuristic of ~4 characters per token, which approximates
    typical LLM tokenization for English text and code. This is a rough
    estimate intended for budgeting purposes, not an exact count.
    
    Edge cases:
    - Empty strings return 0 tokens (no content = no tokens)
    - Very short strings (< 4 chars) return 1 token to avoid zero estimates
    - The truncation marker accounts for its own token cost
    
    Args:
        text: The text content to estimate tokens for
        
    Returns:
        Estimated token count (minimum 1 for non-empty text, 0 for empty)
    """
    if not text:
        return 0
    return max(1, len(text) // 4)

def looks_binary(path: Path, probe_bytes: int = 8192) -> bool:
    """Detect binary content by inspecting bytes, not just the extension.

    Extension checks alone let files like .coverage (a SQLite database),
    .db, .sqlite, or any unknown suffix through, where errors="replace"
    turns them into thousands of replacement characters that consume the
    token budget and crowd out real source.
    """
    try:
        with path.open("rb") as f:
            chunk = f.read(probe_bytes)
    except OSError:
        return True
    if not chunk:
        return False
    if b"\x00" in chunk:
        return True
    # A high proportion of undecodable bytes means this is not text.
    try:
        chunk.decode("utf-8")
    except UnicodeDecodeError:
        decoded = chunk.decode("utf-8", errors="replace")
        if decoded.count("\ufffd") / max(1, len(decoded)) > 0.05:
            return True
    return False


def read_text_file(path: Path) -> str | None:
    """Read file as text if not binary and not too large."""
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return None
    try:
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            return f"[File skipped: too large ({size} bytes)]"
        if looks_binary(path):
            return None
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        return f"[Error reading file: {e}]"

def build_file_inventory(root: Path, include_patterns: list[str], exclude_patterns: list[str]) -> list[dict]:
    """Walk root, collect non-ignored text files with metadata."""
    inventory = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath)
        
        # Filter dirs in-place to avoid descending ignored dirs
        valid_dirs = []
        for d in dirnames:
            if should_process(dirpath / d, root, include_patterns, exclude_patterns):
                valid_dirs.append(d)
        dirnames[:] = valid_dirs
        
        for fname in filenames:
            fpath = dirpath / fname
            if not should_process(fpath, root, include_patterns, exclude_patterns):
                continue
                
            content = read_text_file(fpath)
            if content is None:
                continue
                
            rel = fpath.relative_to(root).as_posix()
            inventory.append({
                "path": rel,
                "size_bytes": fpath.stat().st_size,
                "tokens_estimate": estimate_tokens(content),
                "content": content
            })
            
    inventory.sort(key=lambda x: x["path"])
    return inventory

TRUNCATION_MARKER = "\n\n...[TRUNCATED by ctxpack to fit budget]..."


def trim_to_budget(inventory: list[dict], budget_tokens: int) -> tuple[list[dict], bool]:
    """Truncate file contents to fit token budget. Returns (trimmed_inventory, is_incomplete).

    Every input file appears in the result so the pack is never silently
    missing paths: files past the budget are recorded with empty content and
    omitted=True. The truncation marker is accounted for BEFORE slicing, so
    the emitted total stays within budget rather than overshooting by the
    length of the marker.
    """
    total_original_tokens = sum(item["tokens_estimate"] for item in inventory)
    is_incomplete = total_original_tokens > budget_tokens

    marker_tokens = estimate_tokens(TRUNCATION_MARKER)
    total = 0
    result = []
    budget_spent = False

    for item in inventory:
        if budget_spent:
            omitted = dict(item)
            omitted["tokens_estimate_original"] = item["tokens_estimate"]
            omitted["content"] = ""
            omitted["tokens_estimate"] = 0
            omitted["omitted"] = True
            result.append(omitted)
            continue

        file_tokens = item["tokens_estimate"]
        if total + file_tokens <= budget_tokens:
            result.append(item)
            total += file_tokens
            continue

        # Reserve room for the marker so the result does not exceed budget.
        remaining = budget_tokens - total - marker_tokens
        if remaining <= 0:
            omitted = dict(item)
            omitted["tokens_estimate_original"] = item["tokens_estimate"]
            omitted["content"] = ""
            omitted["tokens_estimate"] = 0
            omitted["omitted"] = True
            result.append(omitted)
            budget_spent = True
            continue

        truncated = item["content"][:remaining * 4] + TRUNCATION_MARKER
        item_copy = dict(item)
        item_copy["content"] = truncated
        item_copy["tokens_estimate"] = estimate_tokens(truncated)
        item_copy["truncated"] = True
        result.append(item_copy)
        total += item_copy["tokens_estimate"]
        budget_spent = True

    return result, is_incomplete

def generate_markdown(inventory: list[dict], root: Path, is_incomplete: bool) -> str:
    """Generate markdown output."""
    included = [i for i in inventory if not i.get("omitted")]
    omitted = [i for i in inventory if i.get("omitted")]
    lines = [
        "# ctxpack Context Pack",
        "",
        f"Generated from: `{root.resolve()}`",
        f"Files included: {len(included)}",
    ]
    if omitted:
        lines.append(f"Files omitted (over budget): {len(omitted)}")
    if is_incomplete:
        lines.append("⚠️ **WARNING**: Total repository tokens exceeded the budget. Some files are truncated or omitted.")
    lines.extend(["", "---", ""])

    for item in included:
        lines.append(f"## {item['path']}")
        lines.append(f"Size: {item['size_bytes']} bytes | Est. tokens: {item['tokens_estimate']}")
        if item.get("truncated"):
            lines.append("*⚠️ Truncated to fit token budget*")
        lines.extend(["", "```text", item["content"], "```", ""])

    if omitted:
        # List omitted paths so the reader knows what is missing from the pack.
        lines.extend(["## Omitted files", "",
                      "These files were not included because the token budget was exhausted:",
                      ""])
        for item in omitted:
            lines.append(f"- `{item['path']}` ({item['size_bytes']} bytes, "
                         f"~{item.get('tokens_estimate_original', 0) or 0} tokens)")
        lines.append("")

    return "\n".join(lines)

def generate_json(inventory: list[dict], root: Path, budget: int, is_incomplete: bool) -> dict:
    """Generate JSON output."""
    included = [i for i in inventory if not i.get("omitted")]
    return {
        "generator": "ctxpack",
        "root": str(root.resolve()),
        "budget_tokens": budget,
        "is_incomplete": is_incomplete,
        "files_included": len(included),
        "files_omitted": len(inventory) - len(included),
        "files": [
            {
                "path": item["path"],
                "size_bytes": item["size_bytes"],
                "tokens_estimate": item["tokens_estimate"],
                "truncated": item.get("truncated", False),
                "omitted": item.get("omitted", False),
                "content": item["content"]
            }
            for item in inventory
        ]
    }

def print_summary(inventory: list[dict], original_inventory: list[dict], budget: int):
    """Print human-readable summary to stdout."""
    total_tokens = sum(item["tokens_estimate"] for item in inventory)
    original_tokens = sum(item["tokens_estimate"] for item in original_inventory)
    truncated_count = sum(1 for item in inventory if item.get("truncated"))
    
    largest = max(original_inventory, key=lambda x: x["tokens_estimate"]) if original_inventory else {"path": "N/A", "tokens_estimate": 0}
    
    pct = (total_tokens / budget * 100) if budget > 0 else 0
    
    print("\n" + "="*40)
    print(" ctxpack Summary")
    print("="*40)
    print(f"Files included:    {len(inventory)}")
    print(f"Total tokens:      {total_tokens:,} / {budget:,} ({pct:.1f}%)")
    print(f"Largest file:      {largest['path']} ({largest['tokens_estimate']:,} tokens)")
    print(f"Truncated files:   {truncated_count}")
    if original_tokens > budget:
        print("⚠️ WARNING: Original repo exceeded budget. Pack is incomplete.")
    print("="*40 + "\n")

def cmd_init(args):
    """Create default .ctxignore and ctxpack.json if missing."""
    root = Path.cwd()
    default_ignore = "\n".join([
        "# ctxpack ignore patterns (gitignore-style)",
        ".git/", ".svn/", ".hg/",
        "__pycache__/", "*.pyc", "*.pyo",
        "node_modules/", "venv/", ".venv/",
        "dist/", "build/",
        ".ruff_cache/", ".pytest_cache/", ".mypy_cache/",
        ".tox/", ".eggs/", "htmlcov/",
        ".coverage",
        "*.log", "*.lock", "package-lock.json",
        ".DS_Store", "Thumbs.db",
        "# Secret-bearing files: excluded by default for security",
        ".env",
        ".env.*",
        "!.env.example",  # Allow template files
        "*.pem", "*.key", "*.p12", "*.pfx",
        "ctxpack.context.json", "ctxpack.context.md"
    ])
    default_config = json.dumps({
        "budget_tokens": 8000,
        "include": [],
        "exclude": [],
        "output_dir": ".",
        "base_name": "ctxpack"
    }, indent=2)

    ignore_path = root / DEFAULT_IGNORE_FILE
    config_path = root / DEFAULT_CONFIG_FILE
    
    if not ignore_path.exists():
        ignore_path.write_text(default_ignore, encoding="utf-8")
        print(f"Created {DEFAULT_IGNORE_FILE}")
    else:
        print(f"{DEFAULT_IGNORE_FILE} already exists")
        
    if not config_path.exists():
        config_path.write_text(default_config, encoding="utf-8")
        print(f"Created {DEFAULT_CONFIG_FILE}")
    else:
        print(f"{DEFAULT_CONFIG_FILE} already exists")

def resolve_settings(args, config: dict) -> tuple[int, str, str]:
    """Resolve budget/output_dir/base_name with precedence CLI > config > default.

    Uses None as the "not supplied" sentinel rather than comparing against the
    default value. Comparing against the default made `--budget 8000` (or
    `--output-dir .`) indistinguishable from omitting the flag, so config
    silently overrode an explicit choice.
    """
    budget = getattr(args, "budget", None)
    if budget is None:
        budget = config.get("budget_tokens", DEFAULT_BUDGET_TOKENS)

    output_dir = getattr(args, "output_dir", None)
    if output_dir is None:
        output_dir = config.get("output_dir", DEFAULT_OUTPUT_DIR)

    base_name = getattr(args, "base_name", None)
    if base_name is None:
        base_name = config.get("base_name", DEFAULT_BASE_NAME)

    return budget, output_dir, base_name


def resolve_patterns(args, config: dict) -> tuple[list[str], list[str]]:
    """Resolve include/exclude patterns with precedence CLI > config."""
    include_patterns: list[str] = []
    if getattr(args, "include", None):
        include_patterns.extend(p.strip() for p in args.include.split(",") if p.strip())
    elif config.get("include"):
        include_patterns.extend(config["include"])

    exclude_patterns: list[str] = []
    if getattr(args, "exclude", None):
        exclude_patterns.extend(p.strip() for p in args.exclude.split(",") if p.strip())
    elif config.get("exclude"):
        exclude_patterns.extend(config["exclude"])

    return include_patterns, exclude_patterns

def cmd_pack(args):
    """Scan repo and build context pack."""
    root = Path.cwd()

    # Load config unless --no-config is set
    config = {}
    if not getattr(args, "no_config", False):
        config = load_config(root)

    budget, output_dir, base_name = resolve_settings(args, config)
    include_patterns, cli_exclude = resolve_patterns(args, config)

    # Merge the built-in defaults and .ctxignore with any CLI/config excludes.
    # The v0.2.0 rewrite left load_ignore_patterns() defined but never called,
    # so .ctxignore and every default (.git, venv, *.log, ...) were ignored.
    exclude_patterns = load_ignore_patterns(root, cli_exclude)

    print(f"Scanning {root} ...")
    original_inventory = build_file_inventory(root, include_patterns, exclude_patterns)
    print(f"Found {len(original_inventory)} text files before budget trim.")
    
    inventory, is_incomplete = trim_to_budget(original_inventory, budget)

    # Resolve output paths relative to the scanned root, not the process cwd,
    # so ctxpack writes beside the repo it scanned rather than wherever the
    # shell happens to be.
    out_dir = Path(output_dir)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{base_name}.context.md"
    json_path = out_dir / f"{base_name}.context.json"

    md_path.write_text(generate_markdown(inventory, root, is_incomplete), encoding="utf-8")
    json_path.write_text(json.dumps(generate_json(inventory, root, budget, is_incomplete), indent=2), encoding="utf-8")

    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    
    print_summary(inventory, original_inventory, budget)

def main():
    parser = argparse.ArgumentParser(
        description="ctxpack - build token-budgeted context packs for AI workflows"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create default .ctxignore and ctxpack.json")
    init_parser.set_defaults(func=cmd_init)

    pack_parser = subparsers.add_parser("pack", help="scan repo and build context pack")
    pack_parser.add_argument("--budget", type=int, default=None,
                             help=f"max token budget (default {DEFAULT_BUDGET_TOKENS})")
    pack_parser.add_argument("--include", type=str, default=None,
                             help="comma-separated include patterns (e.g., 'src/**,tests/**')")
    pack_parser.add_argument("--exclude", type=str, default=None,
                             help="comma-separated exclude patterns (takes precedence)")
    pack_parser.add_argument("--output-dir", type=str, default=None,
                             help="directory for output files (default: '.')")
    pack_parser.add_argument("--base-name", type=str, default=None,
                             help="base name for output files (default: 'ctxpack')")
    pack_parser.add_argument("--no-config", action="store_true",
                             help="ignore ctxpack.json settings")
    pack_parser.set_defaults(func=cmd_pack)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
