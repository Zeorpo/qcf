# Risk

**Status: not implemented.**

**Owning stage: Stage 12.**

## Intended responsibility

Provide an independent risk engine with versioned paper limits: maximum contracts, risk per trade, aggregate exposure, open orders, daily loss, rolling drawdown, session exposure, cost and slippage deviation, stale-data duration, clock uncertainty, reconciliation difference, policy age, and the new-entry cutoff before a required flatten.

Sizing derives from a predefined risk budget and estimated adverse movement, then is capped by every independent limit.

## Premature implementation is forbidden

The risk engine is independent of strategy logic. It may approve, reduce, reject, or require simulated flattening. It may never create or increase directional exposure.

Martingale, recovery mode, revenge sizing, and averaging down without a fully predeclared total-risk plan are prohibited outright — not configurable, not gated behind a flag.

Size is never chosen to reach a profit target, and never increased because of a loss or a drawdown.

Nothing in this area may be built before its stage begins, and its stage may not begin before the stages it depends on have been reviewed and accepted. Building ahead of the gate produces work that was never validated against the evidence the earlier stages were meant to produce.
