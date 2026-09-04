# ADR-0003: Frozen configuration and explicit UNKNOWN values

- **Status:** Accepted
- **Date:** 2026-09-03
- **Stage:** 00

## Context

Later stages will hold values that must come from an authoritative source: tick
values, exchange fees, account limits, final trading dates, policy versions.
Between "this field exists" and "this field has been established" there is a gap
that most systems fill with a default.

That default is the failure this project is built to avoid. A fee that silently
defaults to zero produces a net profit-and-loss figure that looks like a result
and is not one, and nothing in the output distinguishes it from a real one.
`None`, `0`, `""`, `False`, and `NaN` are all equally dangerous, because
arithmetic accepts every one of them.

Separately, configuration that can change during a run makes the recorded
configuration fingerprint a description of *some* moment rather than of the run.

## Decision

Configuration is a frozen Pydantic model. It is validated once, cannot be
mutated afterwards, and rejects unknown keys (`extra="forbid"`) so that a
misspelled setting fails loudly instead of being ignored.

Values that have not been established are represented by a dedicated sentinel,
`qcf.core.unknown.UNKNOWN`, which:

- is a singleton, so `is` comparisons are reliable across copy and pickle;
- raises `UnknownValueError` on every numeric coercion — including `bool`, since
  `if value:` is the likeliest accidental use;
- raises on all arithmetic, in both directions, and on all ordering comparisons;
- supports equality and hashing, because asking whether a value is unknown must
  never itself be an error;
- has a tagged canonical form that cannot collide with the string `"UNKNOWN"`.

`require_known(value, field=...)` is the guard later stages call before
arithmetic. It names the field in the error, which a coercion failure raised
deep inside an expression could not.

Precedence is explicit arguments, then `QCF_`-prefixed environment variables,
then YAML. Dotenv files and secret directories are deliberately not consulted:
QCF configuration carries no secrets, so reading credential sources would only
create somewhere for one to hide.

## Alternatives considered

**`None` for unknown values.** Rejected. `None` is used throughout Python for
"not applicable" and "not yet computed"; overloading it with "must not be used"
guarantees the three get confused. `None` also passes silently through `if`.

**`NaN` for unknown numerics.** Rejected, and specifically prohibited. NaN
propagates through arithmetic without raising, so a missing fee would surface as
a NaN profit figure far from its cause — or worse, be filtered out along the
way.

**Mutable configuration with a snapshot taken for the record.** Rejected: the
snapshot and the values actually used can then diverge, and the fingerprint
stops meaning what it appears to mean.

**Allowing unknown configuration keys for forward compatibility.** Rejected. A
risk limit set in a file and never read is a worse outcome than a startup
failure, and it is invisible.

## Consequences

Later stages must handle `UNKNOWN` explicitly before computing. That is
deliberate friction placed exactly where a silent default would otherwise be.

A known limitation: `decimal.Decimal` inspects concrete types rather than
calling a coercion protocol, so `Decimal(UNKNOWN)` raises `TypeError` from the
standard library rather than `UnknownValueError`. The conversion remains
impossible, which is the property that matters, but the exception type differs.
This is asserted by a test so that it cannot change unnoticed, and
`require_known` is the recommended guard where the distinction matters.

Adding a configuration field now requires touching the model, so configuration
cannot grow by accident in a YAML file.

## Verification

- `tests/unit/core/test_unknown.py` asserts every prohibited coercion,
  arithmetic operation in both directions, and ordering comparison raises.
- `tests/unit/core/test_config.py` asserts immutability, unknown-key rejection,
  precedence, and that `policy_version` defaults to UNKNOWN.
- `tests/property/test_fingerprint_properties.py` asserts prohibited coercions
  fail for arbitrary generated operands.
- `fingerprint(UNKNOWN) != fingerprint("UNKNOWN")` is asserted directly.
