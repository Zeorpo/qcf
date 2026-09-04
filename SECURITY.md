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
| Secret detection | `detect-secrets` with a reviewed baseline, in pre-commit and in CI |
| Log redaction | A structlog processor, so it cannot be forgotten at a call site |
| Least-privilege CI | `permissions: contents: read`; no secrets are exposed to any job |

GitHub Advanced Security is **not** assumed to be available on this repository,
so secret scanning is performed by a pinned tool in the dependency set rather
than by a platform feature.

## Dependencies

Dependencies are pinned in `uv.lock` and installed with `--frozen`, so CI
resolves nothing at build time. New dependencies require a written
justification: the current stage must import them, and no broker, exchange,
market-data, or order-routing client is admissible at any stage.

## Supported versions

None. QCF is pre-release research software with no supported version, no
security-update stream, and no stability promise. It is not intended for
deployment.
