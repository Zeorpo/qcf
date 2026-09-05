---
name: Data quality finding
about: A defect, ambiguity, or anomaly in a dataset
labels: data-quality
---

> Stages 02A and 03 are not implemented and no data has been authorised. This
> template exists so that findings have a home from the moment they can occur.

## Finding

<!-- What was observed. Describe the anomaly; do not paste price rows. -->

## Where

- Dataset / vendor:
- File manifest entry or fingerprint:
- Contract(s) affected:
- Time range affected:

## Category

<!-- e.g. missing timestamps, duplicates, out-of-order events, sequence gaps,
     off-tick prices, crossed quotes, impossible OHLC relations, stale quotes,
     partial sessions, symbol inconsistency, price scaling, roll gap, timezone
     or daylight-saving anomaly, truncation, vendor correction. -->

## Proposed disposition

One of `ACCEPT`, `FLAG`, `QUARANTINE`, `REJECT_DATASET`, or
`REQUIRES_HUMAN_DECISION` — see `qcf.core.enums.DataQualityDisposition`.

- Proposed:
- Reasoning:

## Could this reverse a research result?

<!-- If yes, no strategy work may proceed on the affected data until the finding
     is resolved. Say so plainly. -->

## Boundary check

- [ ] No market data rows are pasted into this issue
