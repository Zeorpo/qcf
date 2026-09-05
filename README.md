# QCF — Quant Currency Futures

Research and paper-simulation tooling for CME Euro FX futures (`6E`).

**Status: Stage 00 — Professional Repository Foundation. In review.**

QCF exists to find out whether an apparent edge is false, fragile, overfit, too
costly, or operationally unsafe. It is not built to produce a profitable-looking
backtest, and most of its machinery is there to make an unjustified result
harder to reach than an honest one.

Nothing in this repository trades. Nothing in it can.

---

## Boundary

**QCF must not transmit a real order, and is built so that it cannot.**

There is no live operating mode, no broker or prop-firm authentication, no
account credentials, no order routing, and no broker client library. This is
enforced by `scripts/check_project_boundary.py` and by contract tests that run
in CI and at commit time — not by convention.

### Permitted operating modes

| Mode | Meaning |
| --- | --- |
| `DISABLED` | **Default.** Does nothing. |
| `RESEARCH` | Historical research and point-in-time data processing |
| `BACKTEST` | Deterministic backtesting |
| `REPLAY` | Historical market replay |
| `PAPER` | Simulated execution and paper-account accounting |

There is no `LIVE` mode. Adding one is not a change to this repository; it would
be a different project under separate authorisation. See
[ADR-0005](docs/architecture/decisions/0005-operating-modes.md).

### Non-goals

Broker or funded-account connectivity · real order submission, modification, or
cancellation · high-frequency or latency-arbitrage infrastructure · exploiting
simulated-fill artefacts · martingale or loss-recovery sizing · cross-account
coordination · automatic self-modification while running · automatic resumption
after an incident.

---

## Engineering principles

The ordering is the substance. Each item precedes the next for a reason, and
reversing any pair produces a specific, well-known failure.

1. Capital preservation before return optimisation.
2. Point-in-time truth before feature quantity.
3. Robustness before historical return.
4. Net performance before gross performance.
5. Realistic execution before convenient execution.
6. Out-of-sample evidence before in-sample evidence.
7. Transparent baselines before complex models.
8. Statistical correction before selecting a winner.
9. Reproducibility before manual exploration.
10. Falsification before promotion.
11. Independent risk controls before strategy freedom.
12. Independent compliance controls before simulated execution.
13. Fail-closed behaviour before operational convenience.
14. Honest rejection before impressive presentation.
15. Human-reviewed changes before automated adaptation.

Assume every signal is noise until evidence suggests otherwise. Assume every
backtest is overfit until it survives adversarial validation. Assume every
component will eventually fail, and design what it does when it does.

---

## Architecture today

Only `qcf.core` exists. It holds what must mean the same thing everywhere:

| Module | Responsibility |
| --- | --- |
| `enums` | Operating modes, halt states, severities, data-quality dispositions |
| `exceptions` | The `QCFError` hierarchy |
| `unknown` | An `UNKNOWN` sentinel that cannot be coerced or used in arithmetic |
| `fingerprint` | Canonical JSON and SHA-256 fingerprints with proven determinism |
| `config` | Frozen, validated, non-financial application settings |
| `logging` | structlog with centralised, non-optional redaction |
| `version` | Package version and best-effort revision resolution |

The full intended structure, with the stage that owns each package, is in
[`docs/architecture/target-layout.md`](docs/architecture/target-layout.md).
Those packages are documented rather than stubbed: an empty package looks like
scaffolding but reads as a claim that a stage has begun.

The layering rules that later stages must obey — strategies emit intents and
never orders; risk and compliance may only subtract; monitoring may halt but
never create exposure — are in
[`docs/architecture/layering-rules.md`](docs/architecture/layering-rules.md).

---

## Repository map

```
config/     Example configuration (base only; others ship with their stages)
data/       Directory skeleton. Contents ignored. No market data, ever.
docs/       Architecture, ADRs, development guides, stage documents
notebooks/  Exploratory only; never canonical logic
reports/    Stage reports; incident and research output (generated, ignored)
scripts/    check_project_boundary.py, run_secret_scan.py, repo_files.py
src/qcf/    The package. core/ only.
tests/      unit, integration, property, contract, regression
```

---

## Getting started

Requires **Python 3.12 or newer** and [uv](https://docs.astral.sh/uv/). Note
that a machine's default `python3` may be older; select 3.12 explicitly.

### Linux and macOS

```bash
git clone https://github.com/Zeorpo/qcf.git
cd qcf
uv venv --python 3.12
uv sync --all-groups --frozen
uv run pre-commit install
uv run python -c "import qcf; print(qcf.__version__)"
```

### Windows PowerShell

```powershell
git clone https://github.com/Zeorpo/qcf.git
Set-Location qcf
uv venv --python 3.12
uv sync --all-groups --frozen
uv run pre-commit install
uv run python -c "import qcf; print(qcf.__version__)"
```

### Validation

Every command runs through `uv run`, against the locked environment. Tools
installed globally are not the project toolchain and are never cited as
evidence.

```bash
uv run ruff format --check .                       # formatting
uv run ruff check .                                # linting
uv run mypy src tests scripts                      # strict typing for src/qcf
uv run pytest                                      # tests, branch coverage, 90% gate
uv run python scripts/check_project_boundary.py --strict    # project boundaries
uv run python scripts/run_secret_scan.py
```

---

## Documentation

| Document | Contents |
| --- | --- |
| [Architecture](docs/architecture/layering-rules.md) | Dependency direction, the decision pipeline, point-in-time rules |
| [Target layout](docs/architecture/target-layout.md) | Every future package and its owning stage |
| [Decisions](docs/architecture/decisions/README.md) | ADRs, and the decisions deliberately deferred |
| [Environment](docs/development/environment.md) | Setup, dependency updates, troubleshooting |
| [Testing](docs/development/testing.md) | Test categories, standards, full validation sequence |
| [Workflow](docs/development/workflow.md) | Branches, commits, pull requests, stage review |
| [Roadmap](docs/stages/roadmap.md) | All twenty stages |
| [Project state](docs/project-state.md) | Where the project currently is |
| [Contributing](CONTRIBUTING.md) | How to work on this |
| [Security](SECURITY.md) | Scope, reporting, controls |

---

## Data and licensing

**No market data is committed to this repository, real or fabricated.** The
`data/` tree is a skeleton whose contents are ignored, and that behaviour is
verified by an executable test rather than by reading the ignore patterns.

No historical `6E` data has been supplied or authorised, so **Stage 03 is
blocked**. Fabricating sample history to unblock it is prohibited: a backtest
built on invented data measures the invention.

**No open-source license is granted.** All rights are reserved by the repository
owner. See [LICENSE_POLICY.md](LICENSE_POLICY.md).

---

## Security

No credentials, API keys, account identifiers, or personal financial
information may appear in this repository, its logs, or its reports. Log
redaction is a processor in the logging pipeline rather than a convention at
call sites, and `detect-secrets` runs at commit time and in CI against a
reviewed baseline.

The security reporting contact is currently `UNKNOWN` — no contact has been
supplied, and one has not been invented. See [SECURITY.md](SECURITY.md).

---

## Limitations

Stated plainly, because a limitation discovered later costs more than one
written down now:

- **This is pre-release research software.** There is no supported version, no
  stability promise, and no intended deployment.
- **No trading system exists.** There is no market data, data pipeline,
  instrument model, feature, strategy, backtester, execution simulator, paper
  broker, risk engine, or compliance engine. Some of the *vocabulary* for these
  exists as enum values. Vocabulary is not behaviour.
- **No result has been produced, and none is claimed.** Nothing here suggests an
  intraday `6E` edge exists.
- **Stage 03 is blocked** pending authorised historical data.
- **The authoritative monetary representation is undecided**, deferred to
  Stage 02B along with the tick and profit-and-loss primitives that will use it.
- **`Decimal(UNKNOWN)` raises `TypeError`, not `UnknownValueError`**, because
  `Decimal` inspects concrete types rather than calling a coercion protocol. The
  conversion remains impossible; only the exception type differs.

QCF models external programme rules for simulation purposes. Doing so is not
approval by any external party, and nothing here is legal or compliance advice.
