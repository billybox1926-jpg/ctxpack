#!/usr/bin/env python3
"""
ctxpack - Dependency-free repo-to-prompt pack builder.
"""

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
        "*.log", "*.lock", "package-lock.json",
        ".DS_Store", "Thumbs.db", 
        DEFAULT_CONFIG_FILE, f"{DEFAULT_BASE_NAME}.context.json", f"{DEFAULT_BASE_NAME}.context.md"
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
    """Check if a path matches a gitignore-style pattern."""
    pat = pattern.rstrip("/")
    # Exact match (for directories like ".git" matching pattern ".git/**")
    if fnmatch.fnmatch(rel, pat):
        return True
    # Recursive directory match (e.g., ".git/config" matching ".git/**")
    if fnmatch.fnmatch(rel, pat + "/**"):
        return True
    # Bare filename match (e.g., "*.log")
    if fnmatch.fnmatch(name, pat):
        return True
    # Handle ** in the middle of paths (simple regex fallback)
    if "**" in pat:
        regex = "^" + re.escape(pat).replace(r"\*\*", ".*").replace(r"\*", "[^/]*") + "$"
        if re.match(regex, rel):
            return True
    return False

def should_process(path: Path, root: Path, include_patterns: list[str], exclude_patterns: list[str]) -> bool:
    """Determine if a file should be processed based on include/exclude rules."""
    rel = path.relative_to(root).as_posix()
    name = path.name
    
    # 1. Exclude takes absolute precedence
    for pat in exclude_patterns:
        if matches_pattern(rel, name, pat):
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
    """Very rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)

def read_text_file(path: Path) -> str | None:
    """Read file as text if not binary and not too large."""
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return None
    try:
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            return f"[File skipped: too large ({size} bytes)]"
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

def trim_to_budget(inventory: list[dict], budget_tokens: int) -> tuple[list[dict], bool]:
    """Truncate file contents to fit token budget. Returns (trimmed_inventory, is_incomplete)."""
    total_original_tokens = sum(item["tokens_estimate"] for item in inventory)
    is_incomplete = total_original_tokens > budget_tokens
    
    total = 0
    result = []
    for item in inventory:
        file_tokens = item["tokens_estimate"]
        if total + file_tokens <= budget_tokens:
            result.append(item)
            total += file_tokens
        else:
            remaining = budget_tokens - total
            if remaining <= 0:
                break
            content = item["content"]
            keep_chars = remaining * 4
            truncated = content[:keep_chars] + "\n\n...[TRUNCATED by ctxpack to fit budget]..."
            item_copy = dict(item)
            item_copy["content"] = truncated
            item_copy["tokens_estimate"] = estimate_tokens(truncated)
            item_copy["truncated"] = True
            result.append(item_copy)
            total += item_copy["tokens_estimate"]
            break
            
    return result, is_incomplete

def generate_markdown(inventory: list[dict], root: Path, is_incomplete: bool) -> str:
    """Generate markdown output."""
    lines = [
        "# ctxpack Context Pack",
        "",
        f"Generated from: `{root.resolve()}`",
        f"Files included: {len(inventory)}",
    ]
    if is_incomplete:
        lines.append("⚠️ **WARNING**: Total repository tokens exceeded the budget. Some files are truncated or omitted.")
    lines.extend(["", "---", ""])
    
    for item in inventory:
        lines.append(f"## {item['path']}")
        lines.append(f"Size: {item['size_bytes']} bytes | Est. tokens: {item['tokens_estimate']}")
        if item.get("truncated"):
            lines.append("*⚠️ Truncated to fit token budget*")
        lines.extend(["", "```text", item["content"], "```", ""])
        
    return "\n".join(lines)

def generate_json(inventory: list[dict], root: Path, budget: int, is_incomplete: bool) -> dict:
    """Generate JSON output."""
    return {
        "generator": "ctxpack",
        "root": str(root.resolve()),
        "budget_tokens": budget,
        "is_incomplete": is_incomplete,
        "files": [
            {
                "path": item["path"],
                "size_bytes": item["size_bytes"],
                "tokens_estimate": item["tokens_estimate"],
                "truncated": item.get("truncated", False),
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
        "*.log", "*.lock", "package-lock.json",
        ".DS_Store", "Thumbs.db",
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

def cmd_pack(args):
    """Scan repo and build context pack."""
    root = Path.cwd()
    
    # Load config unless --no-config is set
    config = {}
    if not getattr(args, "no_config", False):
        config = load_config(root)
    
    # Resolve settings: CLI > Config > Default
    budget = args.budget if args.budget_set else config.get("budget_tokens", DEFAULT_BUDGET_TOKENS)
    output_dir = args.output_dir if args.output_dir_set else config.get("output_dir", DEFAULT_OUTPUT_DIR)
    base_name = args.base_name if args.base_name_set else config.get("base_name", DEFAULT_BASE_NAME)
    
    # Merge include/exclude patterns
    include_patterns = []
    if args.include:
        include_patterns.extend([p.strip() for p in args.include.split(",")])
    elif config.get("include"):
        include_patterns.extend(config["include"])
        
    exclude_patterns = []
    if args.exclude:
        exclude_patterns.extend([p.strip() for p in args.exclude.split(",")])
    elif config.get("exclude"):
        exclude_patterns.extend(config["exclude"])

    print(f"Scanning {root} ...")
    original_inventory = build_file_inventory(root, include_patterns, exclude_patterns)
    print(f"Found {len(original_inventory)} text files before budget trim.")
    
    inventory, is_incomplete = trim_to_budget(original_inventory, budget)

    # Resolve output paths
    out_dir = Path(output_dir)
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
    pack_parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET_TOKENS,
                             help=f"max token budget (default {DEFAULT_BUDGET_TOKENS})")
    pack_parser.add_argument("--include", type=str, default=None,
                             help="comma-separated include patterns (e.g., 'src/**,tests/**')")
    pack_parser.add_argument("--exclude", type=str, default=None,
                             help="comma-separated exclude patterns (takes precedence)")
    pack_parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR,
                             help="directory for output files (default: '.')")
    pack_parser.add_argument("--base-name", type=str, default=DEFAULT_BASE_NAME,
                             help="base name for output files (default: 'ctxpack')")
    pack_parser.add_argument("--no-config", action="store_true",
                             help="ignore ctxpack.json settings")
    pack_parser.set_defaults(func=cmd_pack)

    args = parser.parse_args()
    
    # Track if args were explicitly set to override config
    args.budget_set = hasattr(args, "budget") and args.budget != DEFAULT_BUDGET_TOKENS
    args.output_dir_set = hasattr(args, "output_dir") and args.output_dir != DEFAULT_OUTPUT_DIR
    args.base_name_set = hasattr(args, "base_name") and args.base_name != DEFAULT_BASE_NAME
    
    if getattr(args, "no_config", False):
        args.budget_set = True
        args.output_dir_set = True
        args.base_name_set = True

    args.func(args)

if __name__ == "__main__":
    main()
