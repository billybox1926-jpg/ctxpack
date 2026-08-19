# ctxpack

**Dependency-free repo-to-prompt pack builder.**

`ctxpack` is the missing bridge between raw repository scanning and AI-ready context. It takes a local project, respects ignore rules, token-budgets the output, and emits two clean artifacts:

- `ctxpack.context.json` — machine-readable inventory for agents/tools
- `ctxpack.context.md` — human-readable prompt pack for pasting into an LLM

No dependencies. No network. No secrets by default.

## Features

- 📁 Recursively scans the current directory
- 🚫 Respects `.ctxignore` (gitignore-style patterns)
- 🪶 Skips binary and overly large files by default
- 🧮 Estimates token usage (approx `chars / 4`)
- ✂️ Respects a max token budget (`--budget`) and truncates gracefully
- ⚙️ Simple configuration via optional `ctxpack.json`

## Installation

No installation required. Just download the single file:

```bash
curl -O https://raw.githubusercontent.com/billybox1926-jpg/ctxpack/main/ctxpack.py
chmod +x ctxpack.py
```

## Usage

### Initialize a project
Create default `.ctxignore` and `ctxpack.json` files in your current directory:
```bash
python ctxpack.py init
```

### Pack a repository
Scan the current directory and generate context files:
```bash
python ctxpack.py pack
```

### Advanced options
```bash
# Set a specific token budget
python ctxpack.py pack --budget 12000

# Ignore ctxpack.json settings and use CLI defaults/flags only
python ctxpack.py pack --no-config --budget 4000
```

## Configuration

### `.ctxignore`
Uses standard gitignore-style patterns. Lines starting with `#` are comments.
```text
# Ignore virtual environments
venv/
.env

# Ignore all log files
*.log
```

### `ctxpack.json`
Optional configuration file. Created via `python ctxpack.py init`.
```json
{
  "budget_tokens": 8000,
  "ignore_file": ".ctxignore",
  "include_binary": false
}
```

## Output Examples

See the [`examples/`](./examples/) directory for sample outputs:
- [`sample.context.md`](./examples/sample.context.md)
- [`sample.context.json`](./examples/sample.context.json)

## License

MIT License. See [LICENSE](LICENSE) for details.
