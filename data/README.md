# Data directories

This is a **skeleton only**. No market data exists in this repository, and none
may ever be committed — real or fabricated.

## Layers

| Directory | Layer | Contents |
| --- | --- | --- |
| `raw/` | Bronze | Original supplied bytes, immutable, content-hashed, never manually corrected |
| `interim/` | — | Working intermediates that may be regenerated at any time |
| `processed/` | Silver / Gold | Canonical normalised records and point-in-time research inputs |
| `quarantine/` | — | Rows withheld from research use, preserved with the finding that withheld them |

Only `README.md` and each directory's `.gitkeep` are tracked. Every other path
under `data/` is ignored by `.gitignore`, and
`tests/contract/test_data_directory_protection.py` asserts that behaviour with
real files rather than trusting the patterns by inspection.

## Status

**Not implemented.** Owning stages:

- **Stage 02A** — data contracts: schemas, timestamp and availability policy,
  layer contracts, manifests, quarantine policy, vendor-adapter interface.
- **Stage 03** — authorised ingestion and forensic quality, which begins only
  after historical data has been supplied **and its use authorised**.

Stage 03 is blocked until then. Fabricating sample `6E` history to unblock it is
prohibited: a backtest built on invented data measures the invention.

## Rules

- Never overwrite a raw file.
- Never silently drop suspicious data; every finding gets an explicit
  disposition (see `qcf.core.enums.DataQualityDisposition`).
- Never use a repaired dataset without preserving the repair rule and its
  lineage.
- Never commit a price row.
