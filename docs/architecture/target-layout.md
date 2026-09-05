# Target layout

The complete intended structure of `src/qcf`, with the stage that owns the
creation of each package.

**Only `core/` exists today.** The rest are documented here and deliberately not
created. An empty package with an `__init__.py` and a docstring looks like
scaffolding but behaves like a claim: it appears in the tree, it gets imported
by mistake, and it suggests that a stage has begun when nothing has been
designed or validated. Documenting the target costs nothing and claims nothing.

## Packages

| Package | Owning stage | Responsibility |
| --- | --- | --- |
| `core/` | **00 (exists)** | Modes, exceptions, unknowns, fingerprints, configuration, logging, version |
| `data/` | 02A / 03 | Canonical schemas, vendor adapters, layer contracts, quality findings |
| `instruments/` | 02B | Versioned `6E` instrument master, contract identity, tick and P&L primitives |
| `calendars/` | 02B | CME sessions, maintenance breaks, holidays, early closes, DST transitions |
| `rolls/` | 02B | Point-in-time roll rules and continuous-series research constructs |
| `features/` | 07 | Point-in-time features with availability timestamps and leakage tests |
| `strategies/` | 08 / 09 | Pre-registered hypotheses emitting research intents, never orders |
| `models/` | 11 | Interpretable models, fitted inside training folds only |
| `portfolio/` | 11 | Conversion of intents into proposed exposure |
| `risk/` | 12 | Independent limits that may only reduce or reject |
| `compliance/` | 15 | Independent policy checks that may only allow, reduce, reject, or flatten |
| `backtesting/` | 04 | Deterministic event-driven kernel with an append-only ledger |
| `execution/` | 05 | Cost, latency, slippage, partial-fill, and queue models |
| `replay/` | 04 / 16 | Deterministic historical replay from the event ledger |
| `paper/` | 16 | Simulated execution adapter and paper account state |
| `monitoring/` | 17 | Freshness, drift, reconciliation, and health monitoring |
| `incidents/` | 17 | Incident classification, evidence bundles, reproduction |
| `reporting/` | 19 | Read-only reports over recorded state |

## Directories outside the package

| Directory | Status |
| --- | --- |
| `config/` | `base.example.yaml` exists; `research`, `replay`, and `paper` examples ship with their stages |
| `data/` | Skeleton only; contents ignored. See [`../../data/README.md`](../../data/README.md) |
| `docs/` | Exists |
| `notebooks/` | Placeholder only. See [`../../notebooks/README.md`](../../notebooks/README.md) |
| `reports/` | `stages/` populated; `incidents/` and `research/` are generated output and are ignored |
| `scripts/` | `check_project_boundary.py`, `run_secret_scan.py`, `repo_files.py` |
| `tests/` | `unit/`, `integration/`, `property/`, `contract/` populated; `regression/` intentionally empty |

## Rule

A package is created by the stage that owns it, together with its tests and its
documentation. Creating one early — even empty — anticipates a design that has
not been reviewed, and the anticipation tends to survive the review.
