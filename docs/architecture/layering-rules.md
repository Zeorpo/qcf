# Layering rules

QCF's architecture exists to make certain mistakes structurally impossible
rather than merely discouraged. The rules below are the ones that carry that
weight.

## Dependency direction

```
core  ←  everything
```

`qcf.core` holds what must mean the same thing everywhere: operating modes, the
exception hierarchy, explicit unknowns, fingerprints, configuration, logging,
version metadata. Everything depends on it, so nothing market-specific may be
placed in it.

Data modules must not import strategy modules. The direction is one-way because
a data layer that knows what a strategy wants is a data layer that can be
shaped, unconsciously, to give the strategy what it wants.

There is no `utils` package and there will not be one. A module named for what
it is *not* accumulates whatever nobody wanted to name, and the dependency graph
stops describing anything.

## The decision pipeline

Later stages implement this pipeline. Each stage may only narrow what the
previous one proposed:

```
Market data
  → point-in-time features
  → strategy intent
  → portfolio proposal
  → independent risk decision
  → independent compliance decision
  → simulated order intent
  → execution simulator
  → paper ledger
```

The constraints that make it worth having:

| Layer | May do | May never do |
| --- | --- | --- |
| Strategy | Emit research intents | Create an order |
| Portfolio | Convert intents to proposed exposure | Overrule risk or compliance |
| Risk | Approve, reduce, reject, require flattening | Create or increase directional exposure |
| Compliance | Allow, reduce, reject, require flattening | Create or increase directional exposure |
| Execution simulator | Fill approved intents | Accept an unapproved intent |
| Monitoring | Halt | Create exposure |
| Reporting | Read recorded state | Write state |

No layer may bypass a later one. Risk and compliance can only ever *subtract*,
which is what makes them independent controls rather than participants.

## Point-in-time truth

Every value carries the timestamp at which it became available, and research
logic may use a value only at or after that timestamp. This is checked by tests
rather than by review, because look-ahead is invisible in a diff and obvious
only in a suspiciously good result.

Internal timestamps are UTC without exception. Conversion to
`America/New_York` or `America/Chicago` happens at presentation and policy
boundaries, using IANA zone identifiers so that daylight-saving transitions are
handled by the zone database rather than by an assumed offset.

## Instruments and prices

Individual contract expiries are the executable instruments. A continuous
futures series is a research construct.

Adjusted continuous prices must never enter fill or profit-and-loss accounting.
Back-adjustment shifts historical prices by amounts derived from roll gaps; a
fill priced on an adjusted series is a fill at a price that never traded.

## Monetary arithmetic

Authoritative cash and price arithmetic must not use binary floating point where
rounding can change the result. The specific representation — `Decimal`, scaled
integers, or a dedicated type — is **deferred to Stage 02B**, which owns the
tick and profit-and-loss primitives. It is recorded as open in
[`decisions/README.md`](decisions/README.md) so that the choice is made
deliberately rather than settled by the first line of code that assumes one.

## Notebooks

Notebooks are never canonical. See [`../../notebooks/README.md`](../../notebooks/README.md).

## Enforcement

| Rule | Enforced by |
| --- | --- |
| No live mode | `scripts/check_project_boundary.py`, contract tests |
| No broker or network client in `src/qcf` | AST import inspection |
| No real-order function | AST function-name inspection |
| No tracked market data | `.gitignore` plus an executable test |
| UTC internally | `Literal["UTC"]` on the config field; boundary check |
| Layer direction | Reviewed today; a mechanical import-graph check arrives when the graph is large enough to need one |
