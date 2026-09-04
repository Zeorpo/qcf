# ADR-0005: Permitted operating modes and the absence of a live mode

- **Status:** Accepted
- **Date:** 2026-09-03
- **Stage:** 00

## Context

QCF is authorised for research, backtesting, replay, and paper simulation only.
It must not be able to transmit a real order.

The realistic threat is not that someone maliciously adds live trading. It is
drift: a mode enum gains a `LIVE` member "for completeness", an adapter is
stubbed "to define the interface", a flag is added "for a future integration" —
and each step is individually reasonable. What was a boundary becomes a
configuration value, and the only thing preventing a real order is that nobody
has set it yet.

## Decision

`OperatingMode` declares exactly five members: `DISABLED`, `RESEARCH`,
`BACKTEST`, `REPLAY`, `PAPER`. The default, everywhere, is `DISABLED`.

There is no `LIVE` member, and there never may be. Nor may there be a
placeholder live adapter, a hidden flag, a stubbed broker interface, or a
function that submits, modifies, or cancels an order outside the process.

Enabling live trading is not a change to this repository. It would be a
different project, under separate authorisation and review.

`HaltState` is declared alongside it so that later stages share one vocabulary
for paper halt states. Stage 00 declares the values only; the latched state
machine is Stage 16.

## Alternatives considered

**A `LIVE` member guarded by a configuration flag.** Rejected. It converts a
boundary into a setting, and settings get set.

**No enum at all until a mode is needed.** Rejected: without a declared
vocabulary, later stages invent competing spellings, and "is there a live mode?"
becomes a question that has to be answered by reading everything.

**A stubbed live adapter to define the interface.** Rejected. An interface for a
capability that must not exist is a design for that capability, and the stub is
the hardest kind of code to argue against filling in.

## Consequences

The default `DISABLED` means a QCF process that has not been told what it is for
does nothing. Every entry point must state its mode explicitly.

Adding a mode requires an ADR that supersedes this one, and the boundary check
and contract tests must both be changed. That is deliberately more friction than
editing an enum.

If live execution is ever wanted, none of this work is wasted — but it happens
elsewhere, under its own review.

## Verification

- `tests/unit/core/test_enums.py` asserts the member set exactly and that
  `LIVE`, `live`, `Live`, `REAL`, and `PRODUCTION` are all absent and rejected.
- `tests/unit/core/test_config.py` asserts no live mode can be configured and
  that the default is `DISABLED`.
- `scripts/check_project_boundary.py` re-derives the member set from the source
  tree and fails on any forbidden member or unexpected difference.
- The same checker asserts no order-transmission function exists in `src/qcf`.
