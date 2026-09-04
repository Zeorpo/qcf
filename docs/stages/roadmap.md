# Roadmap

Twenty stages, implemented one at a time. No delivery dates are given, no
returns are projected, and no real deployment is planned or implied.

| Stage | Name | Status |
| --- | --- | --- |
| 00 | Professional repository foundation | **In review** |
| 01 | Governance and versioned policy contracts | Not started |
| 02A | Historical-data contracts | Not started |
| 02B | Instrument, session, expiry, and roll foundation | Not started |
| 03 | Authorised data ingestion and forensic quality | **Blocked** — awaiting authorised data |
| 04 | Event-driven backtest kernel | Not started |
| 05 | Execution cost and fill uncertainty | Not started |
| 06 | Baselines and falsification harness | Not started |
| 07 | Point-in-time features | Not started |
| 08 | Pre-registered strategy family A | Not started |
| 09 | Pre-registered strategy family B | Not started |
| 10 | Event, liquidity, and abnormal-market gates | Not started |
| 11 | Champion/challenger and ensemble research | Not started |
| 12 | Independent risk engine | Not started |
| 13 | Anti-overfitting validation | Not started |
| 14 | Stress and failure testing | Not started |
| 15 | Compliance replay | Not started |
| 16 | Paper execution and automatic halt | Not started |
| 17 | Incident learning and monitoring | Not started |
| 18 | Frozen forward paper observation | Not started |
| 19 | Final research dossier | Not started |

## Scope of each stage

**00 — Foundation.** Package layout, typed configuration, structured logging,
core enums and exceptions, documentation hierarchy, ADR process, test hierarchy,
quality tooling, CI, security, project state.

**01 — Governance.** Project charter, model-risk policy, hypothesis registry,
append-only experiment ledger, traceability framework, versioned external policy
schema with expiry and ambiguity handling, research-only boundary tests.

**02A — Data contracts.** Trade, quote, depth, bar, metadata, event, and quality
schemas; timestamp and availability policy; layer contracts; manifests and
fingerprints; quarantine policy; vendor-adapter interface. No ingestion.

**02B — Instrument and time.** Versioned `6E` instrument master; exact tick and
P&L primitives; individual-expiry model; CME calendar interface; daylight-saving
and early-close behaviour; point-in-time roll rules; continuous-series research
contracts, with tests preventing execution on adjusted prices.

**03 — Ingestion.** Begins **only** after historical data is supplied and its use
authorised. File inventory and hashes, vendor adapter, immutable raw ingestion,
canonical normalisation, quarantine flow, quality metrics, deterministic bars,
point-in-time metadata join, dataset fingerprint. No strategy work.

**04 — Backtest kernel.** Causal event types, deterministic clock and ordering,
paper ledger primitives, simulated orders and fills, position and cash
reconciliation, restart and replay semantics, adversarial timing tests.

**05 — Execution costs.** Fee configuration, bid/ask handling, latency and
slippage scenarios, partial fills, passive non-fill and queue assumptions, gap
behaviour, base and stress models, cost-sensitivity reporting.

**06 — Baselines.** No-position benchmark, matched random controls, transparent
trend and reversion baselines, shuffled-label and time-shift leakage controls,
trial registry.

**07 — Features.** Feature registry with availability timestamps, fold-local
transformations, future-row mutation tests, missingness and quality flags,
stability reporting.

**08 / 09 — Strategy families.** One pre-registered, transparent, non-HFT
hypothesis each: continuation/trend, then displacement/reversion. Base and
stressed costs, matched baselines, predeclared rejection criteria. No promotion
on in-sample performance.

**10 — Gates.** Veto-only gates for news policy, stale data, spread and
liquidity anomalies, volatility jumps, session transitions, roll periods, and
holidays. A gate may block exposure; it may never create a trade.

**11 — Combination.** Champion and limited interpretable challengers, equal-weight
and constrained combinations, nested chronological validation. The simpler model
is preferred when the evidence is not decisive.

**12 — Risk.** Independent exposure limits, contract caps, drawdown and daily-loss
controls, cost deviation limits, internal flatten buffer, kill switches, property
tests, fail-closed decisions.

**13 — Anti-overfitting.** Rolling and anchored walk-forward, purge and embargo,
block bootstrap, multiple-testing adjustment, probability of backtest overfitting
and deflated Sharpe where the assumptions hold, parameter and subperiod stability,
concentration analysis. Outcome is REJECT, INCONCLUSIVE, or PAPER-CANDIDATE.

**14 — Stress.** Execution stresses, data and clock failures, event, roll, and
holiday scenarios, order and state failures, restart and duplicate delivery,
block simulations, assessed against tolerances declared in advance.

**15 — Compliance replay.** Refresh policy sources, version changes, replay
candidate behaviour through every relevant paper profile, report duration, order
activity, session, news, and hedging telemetry. A pass means conformity to an
encoded policy version in simulation.

**16 — Paper execution.** Simulated execution adapter only, latched halt state
machine, incident evidence bundles, manual review and resume. No automatic
retraining, no automatic resume, and a boundary test proving no live adapter
exists.

**17 — Incident learning.** Classification, deterministic reproduction, regression
fixtures, offline correction workflow, drift and health monitoring, dashboards,
runbooks, versioned restart.

**18 — Forward observation.** Freeze code, model, features, parameters, costs,
risk limits, and compliance version. Run a predeclared forward paper window with
no tuning. Any change creates a new candidate and a new window.

**19 — Dossier.** Data lineage, all trials, validation evidence, cost and stress
outcomes, compliance replay, paper observation, incidents, reproducibility
instructions, limitations, and an independent-review checklist.

The final classification is exactly one of **REJECTED**, **INCONCLUSIVE**, or
**RESEARCH-VALIDATED FOR CONTINUED PAPER OBSERVATION**. There is no
"live-ready" classification, and no stage adds real-order capability.
