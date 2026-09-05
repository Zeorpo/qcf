# Security policy

## Scope

QCF is private research software. It performs historical research, deterministic
backtesting, replay, and simulated paper execution. It holds no credentials,
connects to no broker or prop firm, and has no capability to transmit, modify,
or cancel a real order.

The security concerns that apply here are therefore narrower than for a trading
system, and different in kind:

- a credential accidentally committed or written into a log or incident bundle;
- a dependency that introduces network or order-routing capability;
- a change that weakens or removes a project boundary;
- research output that leaks account or personal information.

## Reporting a vulnerability

**Reporting contact: `UNKNOWN`.**

No security contact has been supplied by the repository owner. This is recorded
as `UNKNOWN` rather than filled in with a plausible address, in keeping with the
project rule that an unestablished value is never invented. The owner should
replace this section with a real contact before the repository is shared with
anyone.

Until then, report privately to the repository owner through whatever channel
you already use to reach them.

**Do not open a public issue containing** credentials, API keys, account
identifiers, account balances, or personal financial information — whether or
not you believe them to be real, and whether or not they appear to be expired.

## If a secret is exposed

1. **Revoke first.** Treat the secret as compromised from the moment it was
   written, not from the moment it was noticed. Rotate it at the issuing service
   before doing anything else.
2. **Then contain.** Remove it from the working tree and from any log, report,
   or incident bundle that captured it.
3. **Then assess history.** A secret in git history is still exposed after the
   file is deleted. Removing it requires rewriting history, which invalidates
   every existing clone, so decide deliberately rather than reflexively — the
   revocation in step 1 is what actually protects you.
4. **Record it.** Note what was exposed, for how long, and what was revoked.
   Do not record the value itself.

## Controls in this repository

| Control | Mechanism |
| --- | --- |
| No live order capability | No `LIVE` operating mode; `scripts/check_project_boundary.py`; contract tests |
| No broker or network clients | Import deny-list enforced by AST inspection over `src/qcf` |
| No tracked market data | `.gitignore` rules, verified by an executable test rather than by reading the patterns |
| No committed `.env` | `.gitignore` plus a tracked-file check |
| Secret detection | `detect-secrets` with a reviewed baseline, in pre-commit and in CI, driven by `scripts/run_secret_scan.py` — NUL-delimited enumeration and argument arrays, so a path containing a space cannot silently go unscanned |
| Log redaction | A structlog processor, so it cannot be forgotten at a call site. Key-based: see ADR-0004 for what it does **not** cover |
| Exception output | `exception_output="safe"` by default — type and error code only, never the message or traceback |
| Configuration diagnostics | Rejected values are never echoed, and the underlying validation error is detached rather than chained |
| Least-privilege CI | `permissions: contents: read`; no secrets are exposed to any job |

GitHub Advanced Security is **not** assumed to be available on this repository,
so secret scanning is performed by a pinned tool in the dependency set rather
than by a platform feature.

## Dependencies

Project, optional and development dependencies are recorded in `uv.lock` with
resolved versions and hashes, and installed with `--frozen`, which prevents uv
from updating that lock during a sync. New dependencies require a written
justification: the current stage must import them, and no broker, exchange,
market-data, or order-routing client is admissible at any stage.

**`--frozen` does not mean nothing is resolved.** QCF's own package is built in
an isolated PEP 517 environment from `[build-system].requires`, and those build
requirements are resolved separately from `uv.lock` on every sync. Observed on a
clean cache with the CI command: `hatchling` (declared as `>=1.27`) plus
`editables`, `packaging`, `pathspec`, `pluggy`, `tomlkit` and
`trove-classifiers`. Four of those seven appear nowhere in `uv.lock`; the other
three share a name with a locked entry but are selected independently, so
equality today is coincidence rather than a constraint. Nor is installation
offline: with an empty cache a sync needs the index for runtime and build
requirements alike.

This is a real and currently unclosed gap in supply-chain control — recorded as
finding R-10 — not a claim that it is safe. See
[ADR-0006](docs/architecture/decisions/0006-reproducible-locking.md) for the
boundary table and what a stronger guarantee would require.

## Supported versions

None. QCF is pre-release research software with no supported version, no
security-update stream, and no stability promise. It is not intended for
deployment.
