# Contributing to ctxpack

Thanks for your interest in contributing! ctxpack is a small, focused tool:
a dependency-free Python CLI that packages a repository into a
token-budgeted prompt pack. Contributions that keep it simple, correct, and
dependency-free are especially welcome.

## Development setup

```bash
git clone https://github.com/billybox1926-jpg/ctxpack
cd ctxpack

python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install pytest ruff build
```

## Running the checks

Every PR must pass all four CI gates (test matrix 3.9–3.12, lint, security,
packaging). Locally:

```bash
# Tests
pytest tests/ -v

# Lint + format (must be clean)
ruff check .
ruff format --check ctxpack.py tests/test_ctxpack.py
```

## Project conventions

- **Single-file design**: the entire implementation lives in `ctxpack.py`.
  Do not introduce runtime dependencies — stdlib only. New features should
  justify themselves against the "dependency-free" promise.
- **Conventional commits**: use prefixes like `feat:`, `fix:`, `chore:`,
  `ci:`, `docs:`, `security:`, `test:`.
- **Tests for every behavior change**: bug fixes need a regression test that
  fails before the fix; new features need coverage of their edge cases.
- **Document rather than infer**: README claims about behavior must match
  what the code actually does; cite the relevant flag/function where useful.

## Submitting a change

1. Create a feature branch from `main`.
2. Make your change with tests.
3. Run the full suite and lint locally.
4. Open a PR describing *what* changed and *why*, including any trade-offs
   or known gaps.

## Reporting bugs

Open a GitHub issue with: the command you ran, the expected vs. actual
output, and your Python version. For security-sensitive reports, see
[SECURITY.md](SECURITY.md).
