# Compliance

**Status: not implemented.**

**Owning stage: Stage 01 (policy contracts) and Stage 15 (replay).**

## Intended responsibility

Encode external programme rules as *versioned* policy profiles, each carrying a source URL, retrieval timestamp, effective date where known, reviewer, content hash, policy version, next review date, and ambiguity status.

The compliance engine is an independent control. It may allow, reduce, reject, or require flattening. It may never create or increase directional exposure.

A rule that is missing, ambiguous, expired, or contradictory blocks new simulated exposure and records the exact ambiguity. It is never resolved by guessing, and never by falling back to the last known version.

## Premature implementation is forbidden

No policy text may be encoded from memory. Rules must be retrieved from their source and hashed.

Modelling a programme's rules in simulation is not approval by that programme, and nothing here may be represented as legal or compliance advice. A passing compliance replay means conformity to an encoded policy version in simulation — nothing more.

Where a timezone label is ambiguous, the interpretation stays marked as requiring written confirmation rather than being silently resolved to a fixed offset.

Nothing in this area may be built before its stage begins, and its stage may not begin before the stages it depends on have been reviewed and accepted. Building ahead of the gate produces work that was never validated against the evidence the earlier stages were meant to produce.
