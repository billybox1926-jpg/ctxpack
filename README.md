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
- 🧮 Estimates token usage (approx `chars / 4` — **not** a model tokenizer count)
- ✂️ Respects a max estimated token budget (`--budget`) and truncates gracefully
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

Uses ctxignore patterns — a tested subset of gitignore syntax. Lines starting with `#` are comments. Blank lines are ignored.

**Supported pattern types:**

| Pattern | Matches | Example |
|---------|---------|---------|
| `foo` | Exact path at any depth | `build/` matches `build/`, `src/build/` |
| `foo/` | Directory and everything inside | `venv/` skips `venv/lib/x.py` |
| `foo/**` | Directory and everything inside | `node_modules/**` skips `node_modules/pkg/x.js` |
| `*.ext` | Files with extension at any depth | `*.log` skips `debug.log` and `logs/debug.log` |
| `/foo` | Exact path at the scan root only | `/build/` skips `build/` but NOT `src/build/` |
| `**` | Spans path segments | `**/.aws/**` skips `.aws/` and `nested/.aws/` |
| `!foo` | Negation — re-includes a previous exclusion | `*.pem` then `!fixture.pem` |
| `\*`, `\[`, etc. | Escaped wildcard/bracket (literal) | `file\*.txt` matches the literal `file*.txt` |

**Pattern precedence:** Patterns are processed in order. The last matching pattern wins — so `!foo` can override an earlier `foo`.

**Include vs. exclude:** `--include` patterns restrict to specific files. `--exclude` patterns remove files. Excludes always override includes.

**Not supported:** Character classes (`[...]`), trailing whitespace significance, or full regex.

```text
# Ignore virtual environments
venv/
.venv/

# Ignore build artifacts at the root only
/build/
/dist/

# Ignore all log files anywhere
*.log

# But keep the main log file
!important.log

# Allow template env files
!.env.example
```

**Default secret exclusions:** ctxpack excludes these by default (not shown in generated `.ctxignore`):
`.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`, `*.cer`, `*.jks`, `*.keystore`, `*.gpg`, `*.asc`, `**/.aws/**`, `**/.ssh/**`, `**/.netrc`, `**/.npmrc`, `**/.pypirc`

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
