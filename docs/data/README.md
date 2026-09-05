# Data

**Status: not implemented.**

**Owning stage: Stage 02A (contracts) and Stage 03 (ingestion).**

## Intended responsibility

Define versioned, vendor-neutral schemas for trades, quotes, depth, bars, session events, contract metadata, roll observations, economic events, and data-quality findings.

Establish the raw, normalised, and research layer contracts, file manifests and fingerprints, the quarantine policy, and the vendor-adapter interface.

Every event distinguishes its event timestamp, its receive timestamp where available, and its **availability** timestamp. The availability timestamp is what determines whether research logic may use a value at all.

## Premature implementation is forbidden

Stage 03 begins only after historical data has been supplied **and its use authorised**.

Fabricating sample `6E` history to unblock development is prohibited. A backtest built on invented data measures the invention.

If only OHLCV bars turn out to exist, that limitation is documented rather than modelled around: queue position, spread, partial fills, and intrabar path cannot be reconstructed from bars, and no conclusion may claim tick-level realism.

Nothing in this area may be built before its stage begins, and its stage may not begin before the stages it depends on have been reviewed and accepted. Building ahead of the gate produces work that was never validated against the evidence the earlier stages were meant to produce.
