# Project state

Updated at the end of every stage. This is the current position; what was
actually done and observed is in the stage reports under `../reports/stages/`.

## Current stage

**Stage 00 — Professional Repository Foundation.** Implemented, validated
locally and on remote CI (Python 3.12 and 3.13, all gates green), and awaiting
independent adversarial review in
[Zeorpo/qcf#1](https://github.com/Zeorpo/qcf/pull/1).

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
| 00 | Awaiting review — see [`../reports/stages/stage-00-report.md`](../reports/stages/stage-00-report.md) |

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

## Open decisions

Recorded in [the ADR index](architecture/decisions/README.md): authoritative
monetary representation (Stage 02B), dataframe engine (Stage 03),
continuous-futures adjustment method (Stage 02B), external policy encoding
(Stage 01), and strategy and model families (Stage 08+).

## Next permitted stage

**Stage 01 — Governance and Versioned Policy Contracts**, and only if the
independent adversarial review of Stage 00 records no unresolved blockers.

## Prohibited premature work

No data ingestion, instrument arithmetic, feature engineering, strategy,
backtest, execution simulation, paper account, risk engine, or compliance engine
may be built before its owning stage. No stage may begin before the stages it
depends on have been reviewed and accepted.
