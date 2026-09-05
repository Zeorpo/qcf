# ADR-0008: Raw values and canonical output are separate input contracts

- **Status:** Accepted
- **Date:** 2026-09-04
- **Stage:** 00 (correction pass 00-C)
- **Supersedes:** the idempotence clause of the original `qcf.core.fingerprint` contract

## Context

Stage 00 shipped a canonicalisation function with two properties that cannot
both hold.

The first was **idempotence**: `canonicalize(canonicalize(x)) == canonicalize(x)`,
asserted by a property test. To satisfy it, a mapping already shaped like a
canonical envelope was passed through unchanged.

The second was **injectivity**, claimed by a comment in `_validated_envelope`:
*"an ordinary mapping cannot impersonate an envelope and collide with a real
value."*

Pass-through makes injectivity false, and the review reproduced it for every
recognised tag:

```text
canonicalize(Decimal("1.25"))                          -> {'__qcf_type__':'decimal','value':'1.25'}
canonicalize({"__qcf_type__":"decimal","value":"1.25"}) -> {'__qcf_type__':'decimal','value':'1.25'}
identical canonical bytes; identical fingerprint
```

This is not a SHA-256 collision. The two inputs serialise to the same bytes, so
equal digests follow arithmetically. The defect is that two different inputs are
*encoded* the same way, and that the code claimed otherwise.

The root cause is an ambiguous input contract: one function accepted both raw
values and its own already-encoded output, and could not tell them apart.

## Decision

`canonicalize` accepts **raw values only**. A mapping is always encoded as a
mapping, including one whose keys resemble an envelope.

Reserved keys are escaped structurally. Any mapping key beginning with the
reserved prefix `__qcf_` is rewritten with an escape marker:

```text
raw key "__qcf_type__"  ->  encoded key "__qcf_esc___qcf_type__"
```

The transform is injective — strip one `__qcf_esc_` to invert it — so no raw
mapping can produce a bare `__qcf_type__` key, and an envelope is therefore
producible only by a typed value.

`CANONICAL_FORMAT_VERSION` records the encoding version, now `2`.

**The blanket idempotence property is withdrawn.** Feeding canonical output back
into `canonicalize` now escapes it, which is correct: that output is a mapping,
and mappings encode as mappings. Determinism and stability are retained and
still tested; they were always the properties that mattered.

## Alternatives considered

**Keep pass-through and just fix the comment.** Rejected. It documents an
ambiguity rather than removing it, and leaves a foreseeable trap: the first
caller to fingerprint an untrusted mapping alongside typed values gets a silent
equivalence, which is precisely the class of error this project exists to catch.

**A separate `CanonicalValue` result type with its own serialisation entry
point.** A sound design, and the cleaner one for a larger system. Rejected as
disproportionate here: it introduces a wrapper type through every call site to
solve a problem that key escaping solves in ten lines, and Stage 00 has two
callers.

**Reject mappings containing reserved keys outright.** Rejected: it turns a
representable value into an error, and the caller could not encode a legitimate
mapping that happens to use the prefix.

## Consequences

`canonicalize` is now injective with respect to envelope shape: a typed value
and a lookalike mapping produce different bytes and different fingerprints.

Callers may pass any JSON-compatible mapping without knowing the reserved
prefix.

**Compatibility.** Fingerprints of mappings whose keys start with `__qcf_`
change. No such fingerprint has ever been persisted: Stage 00 stores no run
records, and the only fingerprinted structure is `AppConfig`, whose field names
contain no reserved prefix. Configuration fingerprints are therefore unchanged
by this ADR. There is no migration and no compatibility shim — a shim would be a
second, weaker code path for a value nothing has stored.

The old property test asserting blanket idempotence is replaced, not deleted
silently: its replacement asserts the distinctions this ADR creates.

## Verification

- `tests/unit/core/test_fingerprint.py` asserts a typed value and its lookalike
  mapping differ, for every recognised tag including UNKNOWN, and at nesting
  depth.
- The same suite asserts the escape transform is injective and that escaping
  round-trips distinctly.
- `tests/property/test_fingerprint_properties.py` retains determinism, key-order
  invariance and sequence-order sensitivity, and replaces the idempotence
  property with escape-stability.
- Encoding tests are separate from digest tests: they compare `canonical_json`
  bytes, never manufacturing a hash collision as a stand-in.
