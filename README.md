# ctxpack

**Dependency-free repo-to-prompt pack builder.**

`ctxpack` is the missing bridge between raw repository scanning and AI-ready context. It takes a local project, respects ignore rules, token-budgets the output, and emits two clean artifacts:

- `ctxpack.context.json` — machine-readable inventory for agents/tools
- `ctxpack.context.md` — human-readable prompt pack for pasting into an LLM

No dependencies. No network. **Secrets excluded by default.**

## Features

- 📁 Recursively scans the current directory
- 🚫 Respects `.ctxignore` (gitignore-style patterns)
- 🪶 Skips binary and overly large files by default
- 🔒 **Excludes secrets by default**: `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`
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
Negation patterns (starting with `!`) can re-include previously excluded files.

```text
# Ignore virtual environments
venv/

# Ignore all log files
*.log

# Secret-bearing files are excluded by default for security:
# .env, .env.*, *.pem, *.key, *.p12, *.pfx

# Allow template env files (the default policy includes !.env.example)
!.env.example
```

**Default secret exclusions:** ctxpack excludes the following secret-bearing files by default:
- `.env` — environment variable files
- `.env.*` — environment variants (e.g., `.env.local`, `.env.production`)
- `!.env.example` — template files are explicitly allowed
- `*.pem`, `*.key` — private keys and certificates
- `*.p12`, `*.pfx` — PKCS#12 certificate bundles

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

## Security

### Secret-safe by default

`ctxpack` excludes credential-bearing files by default so they never reach the generated pack. The built-in ignore policy covers:

- **Local env files**: `.env`, `.env.*` (but not `.env.example`, the conventional template)
- **Private keys & certificates**: `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`, `*.cer`
- **Keystores**: `*.jks`, `*.keystore`
- **GPG / signing material**: `*.gpg`, `*.asc`
- **Credential directories**: `**/.aws/**`, `**/.ssh/**`
- **Auth dotfiles**: `**/.netrc`, `**/.npmrc`, `**/.pypirc`

These defaults are applied automatically; you do not need to list them in `.ctxignore`. Custom `.ctxignore` entries are merged with these defaults and can add further exclusions.

To opt a specific secret file back in (e.g., a test fixture), add a negation pattern to `.ctxignore`:

```text
!important/test-fixture.pem
```

## License

MIT License. See [LICENSE](LICENSE) for details.
