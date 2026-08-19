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

Uses a **documented subset of gitignore-style patterns**. Lines starting with `#` are comments.

**Supported pattern semantics:**

| Pattern | Description | Example |
|---------|-------------|---------|
| `*.ext` | Bare patterns match by filename anywhere in tree | `*.log` matches all `.log` files |
| `dir/**` | Matches directory and all contents recursively | `node_modules/**` |
| `**/*.ext` | Recursive match from any depth (including root) | `**/*.log` |
| `/pattern` | Leading `/` is stripped; treated as bare pattern | `/test.log` = `test.log` |
| `pattern/` | Trailing `/` stripped; matches dir and contents | `.git/` |
| `!pattern` | Negation: re-includes previously excluded files | `!.env.example` |

**Documented limitations (not full gitignore compatibility):**
- Leading `/` does not strictly anchor to root (stripped for matching)
- No support for escaped patterns (e.g., `\!important.txt`)
- No directory-only patterns that exclude files with same name

```text
# Ignore virtual environments
venv/

# Ignore all log files (anywhere in tree)
*.log

# Ignore specific directory and contents
node_modules/**

# Secret-bearing files are excluded by default for security:
# .env, .env.*, *.pem, *.key, *.p12, *.pfx

# Re-include template env files using negation
!.env.example
```

**Default secret exclusions:** ctxpack excludes the following secret-bearing files by default:
- `.env` — environment variable files
- `.env.*` — environment variants (e.g., `.env.local`, `.env.production`)
- `!.env.example` — template files are explicitly allowed via negation
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

## Token Budget Semantics

### How token estimation works

ctxpack uses a simple heuristic to estimate token count: **~4 characters per token**. This approximates typical LLM tokenization for English text and code. Key details:

- **Empty content = 0 tokens**: Files with no content contribute zero tokens
- **Minimum 1 token**: Any non-empty file gets at least 1 token estimate
- **Truncation marker overhead**: When files are truncated, the truncation message (`...[TRUNCATED by ctxpack to fit budget]...`) accounts for ~11 tokens

### Budget enforcement behavior

When the total estimated tokens exceed the budget:

1. Files are processed in sorted path order
2. Files that fit entirely within remaining budget are included as-is
3. The first file that would exceed the budget is **truncated** (not dropped), with a truncation marker appended
4. Remaining files are marked as **omitted** (empty content, listed in output)

This ensures:
- **No silent drops**: Every discovered file appears in the output (either full, truncated, or omitted)
- **Budget never exceeded**: The truncation marker's token cost is reserved before slicing
- **Transparent about missing content**: Omitted files are listed with their original size/token estimates

### Edge cases

| Scenario | Behavior |
|----------|----------|
| Empty repository | Outputs header only, 0 tokens used |
| Single file > budget | File truncated to fit budget + marker |
| Exact budget match | All files included without truncation |
| Very small budget (< 20 tokens) | First file may be truncated immediately or omitted |

### Limitations

- This is a **rough estimate**, not an exact token count. Actual LLM tokenizers (e.g., tiktoken, sentencepiece) may vary by ±20-30%
- Code with many symbols, non-English text, or unusual formatting may have different actual token counts
- For critical workflows, verify actual token usage with your target model's tokenizer

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
