# Instruments

**Status: not implemented.**

**Owning stage: Stage 02B.**

## Intended responsibility

Hold the versioned instrument master for CME Euro FX futures (`6E`): product code, individual contract symbols, contract unit, quote currency, price precision, tick size, tick value, contract month, listing and expiry metadata, final trading date from an authoritative source, settlement flags, and the session-calendar version.

Provide the exact tick and profit-and-loss primitives that every later stage computes with.

## Premature implementation is forbidden

Contract specifications, expiry dates, roll dates, and holiday calendars must never be inferred from memory. Each comes from an authoritative source with a retrieval timestamp, and is encoded as versioned metadata rather than scattered as constants.

Individual expiries are the executable instruments. A continuous series is a research construct, and adjusted continuous prices may never enter fill or profit-and-loss accounting.

The authoritative monetary representation is an open decision owned by this stage; see [the ADR index](../architecture/decisions/README.md).

Nothing in this area may be built before its stage begins, and its stage may not begin before the stages it depends on have been reviewed and accepted. Building ahead of the gate produces work that was never validated against the evidence the earlier stages were meant to produce.
