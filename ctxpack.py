#!/usr/bin/env python3
"""
ctxpack - Dependency-free repo-to-prompt pack builder.
"""

import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path

DEFAULT_BUDGET_TOKENS = 8000
DEFAULT_IGNORE_FILE = ".ctxignore"
DEFAULT_CONFIG_FILE = "ctxpack.json"
OUTPUT_JSON = "ctxpack.context.json"
OUTPUT_MD = "ctxpack.context.md"

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".exe", ".dll",
    ".so", ".dylib", ".zip", ".tar", ".gz", ".7z", ".pyc", ".class",
    ".o", ".obj", ".bin", ".woff", ".woff2", ".ttf", ".eot"
}

MAX_FILE_BYTES = 500_000  # skip files larger than ~500KB by default

def load_ignore_patterns(root: Path) -> list[str]:
    """Load patterns from .ctxignore, returning default list if missing."""
    default_patterns = [
        ".git/**", ".svn/**", ".hg/**",
        "__pycache__/**", "*.pyc", "*.pyo",
        "node_modules/**", "venv/**", ".venv/**",
        "dist/**", "build/**",
        "*.log", "*.lock", "package-lock.json",
        ".DS_Store", "Thumbs.db", DEFAULT_CONFIG_FILE, OUTPUT_JSON, OUTPUT_MD
    ]
    ignore_file = root / DEFAULT_IGNORE_FILE
    if not ignore_file.exists():
        return default_patterns
    patterns = []
    with ignore_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns or default_patterns

def should_ignore(path: Path, root: Path, patterns: list[str]) -> bool:
    """Return True if path matches any ignore pattern."""
    rel = path.relative_to(root).as_posix()
    for pattern in patterns:
        pat = pattern.rstrip("/")
        # Check direct match or recursive directory match
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat + "/**"):
            return True
        # Handle directory patterns explicitly (e.g., ".git/" matching ".git" dir)
        if path.is_dir() and fnmatch.fnmatch(rel + "/", pat + "/"):
            return True
        # Handle directory patterns like ".git/**" - match the dir itself
        if path.is_dir() and pattern.endswith("/**"):
            dir_pattern = pattern[:-3]  # Remove "/**"
            if fnmatch.fnmatch(rel, dir_pattern):
                return True
        # Handle patterns like "*.log" matching anywhere in path
        if "/" not in pat and fnmatch.fnmatch(path.name, pat):
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

def build_file_inventory(root: Path, ignore_patterns: list[str]) -> list[dict]:
    """Walk root, collect non-ignored text files with metadata."""
    inventory = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath)
        # Filter dirs in-place to avoid descending ignored dirs
        dirnames[:] = [
            d for d in dirnames
            if not should_ignore(dirpath / d, root, ignore_patterns)
        ]
        for fname in filenames:
            fpath = dirpath / fname
            if should_ignore(fpath, root, ignore_patterns):
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
    # Sort by path for deterministic output
    inventory.sort(key=lambda x: x["path"])
    return inventory

def trim_to_budget(inventory: list[dict], budget_tokens: int) -> list[dict]:
    """Truncate file contents to fit token budget, keeping file list intact."""
    total = 0
    result = []
    for item in inventory:
        file_tokens = item["tokens_estimate"]
        if total + file_tokens <= budget_tokens:
            result.append(item)
            total += file_tokens
        else:
            # Add truncated version
            remaining = budget_tokens - total
            if remaining <= 0:
                break
            content = item["content"]
            # Roughly keep remaining*4 characters
            keep_chars = remaining * 4
            truncated = content[:keep_chars] + "\n\n...[TRUNCATED by ctxpack]..."
            item_copy = dict(item)
            item_copy["content"] = truncated
            item_copy["tokens_estimate"] = estimate_tokens(truncated)
            item_copy["truncated"] = True
            result.append(item_copy)
            total += item_copy["tokens_estimate"]
            break
    return result

def generate_markdown(inventory: list[dict], root: Path) -> str:
    lines = [
        "# ctxpack Context Pack",
        "",
        f"Generated from: `{root.resolve()}`",
        f"Files included: {len(inventory)}",
        "",
        "---",
        ""
    ]
    for item in inventory:
        lines.append(f"## {item['path']}")
        lines.append(f"Size: {item['size_bytes']} bytes | Est. tokens: {item['tokens_estimate']}")
        if item.get("truncated"):
            lines.append("*⚠️ Truncated to fit token budget*")
        lines.append("")
        lines.append("```text")
        lines.append(item["content"])
        lines.append("```")
        lines.append("")
    return "\n".join(lines)

def generate_json(inventory: list[dict], root: Path, budget: int) -> dict:
    return {
        "generator": "ctxpack",
        "root": str(root.resolve()),
        "budget_tokens": budget,
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
        OUTPUT_JSON, OUTPUT_MD
    ])
    default_config = json.dumps({
        "budget_tokens": 8000,
        "ignore_file": ".ctxignore",
        "include_binary": False
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
    root = Path.cwd()
    budget = args.budget
    
    # optional config override
    config_path = root / DEFAULT_CONFIG_FILE
    if config_path.exists() and not getattr(args, "no_config", False):
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        if "budget_tokens" in config and not getattr(args, "budget_set", False):
            budget = config["budget_tokens"]

    patterns = load_ignore_patterns(root)
    print(f"Scanning {root} ...")
    inventory = build_file_inventory(root, patterns)
    print(f"Found {len(inventory)} text files.")
    
    inventory = trim_to_budget(inventory, budget)

    md_path = root / OUTPUT_MD
    json_path = root / OUTPUT_JSON

    md_path.write_text(generate_markdown(inventory, root), encoding="utf-8")
    json_path.write_text(json.dumps(generate_json(inventory, root, budget), indent=2), encoding="utf-8")

    print(f"Wrote {md_path.name} ({md_path.stat().st_size} bytes)")
    print(f"Wrote {json_path.name} ({json_path.stat().st_size} bytes)")

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
    pack_parser.add_argument("--no-config", action="store_true",
                             help="ignore ctxpack.json settings")
    pack_parser.set_defaults(func=cmd_pack)

    args = parser.parse_args()
    # Mark if budget was explicitly set for config override logic
    args.budget_set = hasattr(args, "budget") and args.budget != DEFAULT_BUDGET_TOKENS
    args.func(args)

if __name__ == "__main__":
    main()
