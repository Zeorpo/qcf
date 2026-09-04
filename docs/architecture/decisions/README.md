# Architecture decision records

Numbered, immutable records of decisions that constrain later stages. The
process is defined in [ADR-0000](0000-adr-process.md); the shape of a record is
in [`template.md`](template.md).

## Accepted

| ADR | Decision | Stage |
| --- | --- | --- |
| [0000](0000-adr-process.md) | ADR process and template | 00 |
| [0001](0001-src-layout-and-boundaries.md) | `src` layout and boundary enforcement | 00 |
| [0002](0002-python-and-environment.md) | Python 3.12+, uv, and the CI matrix | 00 |
| [0003](0003-configuration-and-unknown-values.md) | Frozen configuration and explicit UNKNOWN values | 00 |
| [0004](0004-structured-logging-and-redaction.md) | structlog, UTC, and centralised redaction | 00 |
| [0005](0005-operating-modes.md) | Permitted operating modes and no LIVE mode | 00 |
| [0006](0006-reproducible-locking.md) | Committed lockfile and reproducibility | 00 |
| [0007](0007-branching-and-bootstrap.md) | Branch workflow and the initial-`main` bootstrap exception | 00 |

## Deliberately deferred

Recorded so that an open question cannot be lost by being merely unwritten. None
of these is decided, and none may be settled implicitly by the first code that
assumes an answer.

| Question | Owning stage | Why it is not decided now |
| --- | --- | --- |
| Authoritative monetary representation: `Decimal`, scaled integers, or a dedicated type | 02B | The choice should follow the tick and P&L primitives that will use it, not precede them |
| Dataframe engine: pandas or polars | 03 | The project rule is to profile the real workload first; no data exists yet |
| Continuous-futures adjustment: unadjusted splice, back-adjusted, or ratio-adjusted | 02B | Depends on the roll rules and the research uses that consume the series |
| Lucid policy encoding and versioning | 01 | Requires retrieving, reviewing, and hashing the source articles |
| Strategy and model families | 08+ | Selecting one before the falsification harness exists would invert the method |
