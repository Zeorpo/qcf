# Project state

Updated at the end of every stage. This is the current position; what was
actually done and observed is in the stage reports under `../reports/stages/`.

## Current stage

**Stage 00 — Professional Repository Foundation**, correction pass **00-C**.

The Stage 00-R review returned **CHANGES REQUIRED** with 13 findings, 12
reproduced. That review was performed by the original implementer and is
therefore a **self-review**; it does not satisfy the independent-review gate.

Correction pass 00-C has been applied **locally and is uncommitted**: six
corrections covering R-01 to R-08 and R-11, then Stage 00-D corrected H-01, R-12,
R-13 and CR-01, and Stage 00-E corrected DR-01 and DR-02. Two findings (R-09,
R-10) remain deferred, both packaging-related and neither blocking. See
[`../reports/stages/stage-00-c-corrections.md`](../reports/stages/stage-00-c-corrections.md).

Remote CI status for the corrections is **NOT RUN**: no push was authorised, so
the green run recorded against `3941e61` predates every change in this pass and
is not evidence for it.

## Starting state

The repository was created empty: private, zero commits, zero refs, no files.
Re-verified immediately before the bootstrap commit.

- **Starting commit:** none — empty repository
- **Bootstrap commit:** `bd2586223b7542ee46924a0c224168777fbccb6e` on `main`
- **Working branch:** `claude/new-session-19lczd`
  (see [ADR-0007](architecture/decisions/0007-branching-and-bootstrap.md))

## Completed

| Stage | Outcome |
| --- | --- |
| 00 | Implemented — [`../reports/stages/stage-00-report.md`](../reports/stages/stage-00-report.md) |
| 00-R | Self-review, CHANGES REQUIRED (13 findings, 12 reproduced) |
| 00-C | Corrections applied locally — [`../reports/stages/stage-00-c-corrections.md`](../reports/stages/stage-00-c-corrections.md) |

## What exists

`src/qcf/core` only: operating modes and the halt-state vocabulary, the
exception hierarchy, explicit UNKNOWN semantics, deterministic fingerprints,
frozen non-financial configuration, structured logging with redaction, and
version metadata. Plus the project-boundary checker, the test hierarchy,
documentation, ADRs 0000–0007, and the CI and pre-commit gates.

## What does not exist

No market data. No data ingestion, schemas, or adapters. No instrument,
calendar, expiry, or roll logic. No tick or profit-and-loss arithmetic. No
features, strategies, signals, or position sizing. No backtester, execution
simulator, or paper broker. No risk or compliance engine. No model. No broker,
prop-firm, or account connectivity, and no capability to transmit, modify, or
cancel a real order.

The vocabulary for several of these exists as enum values. The vocabulary is not
the behaviour.

## Limitations

- No historical `6E` data has been supplied or authorised, so **Stage 03 is
  blocked**. Fabricating sample history to unblock it is prohibited.
- The security reporting contact is `UNKNOWN` until the owner supplies one.
- No open-source license is selected; all rights reserved.
- `decimal.Decimal(UNKNOWN)` raises `TypeError` rather than `UnknownValueError`,
  because `Decimal` inspects concrete types instead of calling a coercion
  protocol. The conversion remains impossible; the exception type differs. See
  [ADR-0003](architecture/decisions/0003-configuration-and-unknown-values.md).
- Log redaction is key-based. It does not sanitise free text a caller puts in an
  event message. See [ADR-0004](architecture/decisions/0004-structured-logging-and-redaction.md).
- Configuration fingerprints are machine-specific where paths differ between
  machines. No cross-machine equivalence is claimed. See
  [ADR-0009](architecture/decisions/0009-effective-path-context.md).
- Two review findings remain open, both non-blocking and both packaging-related:
  **R-09** — the sdist `include` patterns are unanchored, so they match a basename
  at any depth and the archive can admit files the declaration never names. A
  clean observed archive and `.gitignore` are not confidentiality guarantees; what
  bounds this today is that the distribution is marked `Private :: Do Not Upload`
  and is never published, and that the wheel — the installable artefact — is
  correct. Precondition for closing: before any sdist is shared with anyone.
  **R-10** — resolved in Stage 00-F by **contract correction, not by pinning**.
  `uv sync --all-groups --frozen` builds QCF's own package in an isolated PEP 517
  environment and selects seven build requirements outside `uv.lock`: `hatchling`
  (declared `>=1.27`) plus `editables`, `packaging`, `pathspec`, `pluggy`,
  `tomlkit` and `trove-classifiers`. `SECURITY.md` and ADR-0006 previously stated
  that nothing was resolved at build or install time; both were false and are now
  corrected. The residual limitation — build-time resolution is outside the lock —
  is stated in the ADR-0006 boundary table along with what a stronger guarantee
  would require. `scripts/check_project_boundary.py` rejects the retired phrasings.
  Pinning `hatchling` alone was deliberately **not** done: it would leave
  transitive build requirements, artifact availability and offline installation
  uncontrolled while restoring the impression that they were.
- **H-01, R-12 and R-13 are corrected** in Stage 00-D. Configuration now fails
  closed on all three input channels, and diagnostics name only declared schema
  fields. See
  [ADR-0010](architecture/decisions/0010-fail-closed-configuration-and-safe-diagnostics.md).
- **CR-01 is corrected**: the circular patch digest has been removed from the
  Stage 00-C report. Patch digests live in an external handoff manifest generated
  after export, which is never included in the patch it describes.
- **DR-01 and DR-02 are corrected** in Stage 00-E. Configuration fields may not
  declare aliases of any form — enforced at class-definition time, not merely
  documented — and the safe-diagnostic boundary now states plainly that a
  traceback prints the caller's own source line, which no library can prevent.

## Open decisions

Recorded in [the ADR index](architecture/decisions/README.md): authoritative
monetary representation (Stage 02B), dataframe engine (Stage 03),
continuous-futures adjustment method (Stage 02B), external policy encoding
(Stage 01), and strategy and model families (Stage 08+).

## Next permitted stage

**None yet.** Stage 01 is not justified until a **fresh review** examines the
00-C corrections and the deferred findings, and records no unresolved blockers.
The 00-R review was a self-review and does not satisfy that gate.

## Prohibited premature work

No data ingestion, instrument arithmetic, feature engineering, strategy,
backtest, execution simulation, paper account, risk engine, or compliance engine
may be built before its owning stage. No stage may begin before the stages it
depends on have been reviewed and accepted.
