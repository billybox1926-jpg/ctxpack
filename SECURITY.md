# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅        |

## Reporting a vulnerability

**Please do not open a public issue for security reports.**

Use GitHub's private vulnerability reporting
(**Security → Report a vulnerability** on this repository), or contact the
maintainer directly at billybox1926@gmail.com if that is unavailable.

Include: a description of the issue, steps to reproduce, and the affected
version/commit. You can expect an initial response within 7 days.

## Security model

ctxpack reads files from the directory it is run in and writes them into a
context pack intended for sharing with AI tools. The following boundaries
are enforced by design:

- **Secret-safe defaults**: credential-bearing files (`.env`, `*.pem`,
  `*.key`, `*.gpg`, `**/.aws/**`, `**/.ssh/**`, and others — see the README)
  are excluded by default. By default, `.ctxignore` negation patterns can
  re-include them as an explicit opt-in; pass `--strict-secrets` to make the
  default secret exclusions non-overridable.
- **Symlink containment**: file symlinks inside the scan root whose resolved
  target lies outside it are never read.
- **Path privacy**: packs reference the project root as `.` unless
  `--show-absolute-paths` is passed.

Known limitations (documented, not treated as vulnerabilities):

- Token estimation is a heuristic; CJK-heavy content uses a denser estimate
  (~1.5 chars/token) but exact tokenizer counts will differ.

## Out of scope

- Issues in repositories scanned by ctxpack (the tool faithfully includes
  whatever its rules admit).
- Social engineering of users into weakening their own ignore configuration
  outside of `--strict-secrets` mode — negation overrides are documented,
  deliberate behavior in default mode.
