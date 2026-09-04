"""Invariants that must hold for every input, not only chosen examples.

A hand-written example demonstrates a case someone thought of. These state the
property and let Hypothesis look for the case nobody thought of.
"""

from __future__ import annotations

import copy
import json
import operator

from hypothesis import assume, given
from hypothesis import strategies as st

from qcf.core.exceptions import UnknownValueError
from qcf.core.fingerprint import TAG_KEY, canonical_json, canonicalize, fingerprint
from qcf.core.logging import redact
from qcf.core.unknown import UNKNOWN

# Keys must be strings, and must not impersonate a canonical envelope; the
# reserved tag is documented as belonging to the fingerprint module.
_keys = st.text(min_size=1, max_size=12).filter(lambda key: key != TAG_KEY)

_scalars = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=16),
    st.just(UNKNOWN),
    st.decimals(allow_nan=False, allow_infinity=False),
    st.dates(),
)

_values = st.recursive(
    _scalars,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(_keys, children, max_size=4),
    ),
    max_leaves=10,
)

_mappings = st.dictionaries(_keys, _values, max_size=5)


@given(mapping=_mappings)
def test_key_order_never_changes_the_fingerprint(mapping: dict[str, object]) -> None:
    reordered = dict(reversed(list(mapping.items())))
    assert fingerprint(mapping) == fingerprint(reordered)


@given(mapping=_mappings, replacement=_values)
def test_changing_a_value_changes_the_fingerprint(
    mapping: dict[str, object], replacement: object
) -> None:
    assume(mapping)
    key = sorted(mapping)[0]
    assume(canonical_json(mapping[key]) != canonical_json(replacement))
    changed = {**mapping, key: replacement}
    assert fingerprint(mapping) != fingerprint(changed)


@given(items=st.lists(_scalars, min_size=2, max_size=5))
def test_sequence_order_stays_significant(items: list[object]) -> None:
    reversed_items = list(reversed(items))
    assume(canonical_json(items) != canonical_json(reversed_items))
    assert fingerprint(items) != fingerprint(reversed_items)


@given(value=_values)
def test_canonicalisation_is_idempotent(value: object) -> None:
    """An already-canonical structure must survive a second pass unchanged."""
    once = canonicalize(value)
    assert canonicalize(once) == once


@given(value=_values)
def test_fingerprinting_is_deterministic(value: object) -> None:
    assert fingerprint(value) == fingerprint(value)


@given(value=_values)
def test_canonical_json_is_parseable(value: object) -> None:
    assert json.loads(canonical_json(value)) == canonicalize(value)


@given(mapping=_mappings)
def test_redaction_never_mutates_input(mapping: dict[str, object]) -> None:
    snapshot = copy.deepcopy(mapping)
    redact(mapping)
    assert mapping == snapshot


@given(mapping=_mappings)
def test_redaction_preserves_the_key_set(mapping: dict[str, object]) -> None:
    """Redaction hides values; it must never drop or invent a key."""
    result = redact(mapping)
    assert isinstance(result, dict)
    assert set(result) == set(mapping)


@given(other=st.one_of(st.integers(), st.floats(allow_nan=False), st.text(max_size=8)))
def test_unknown_arithmetic_always_fails(other: object) -> None:
    """No operand makes arithmetic with UNKNOWN succeed."""
    for operation in (operator.add, operator.sub, operator.mul, operator.truediv):
        for left, right in ((UNKNOWN, other), (other, UNKNOWN)):
            try:
                operation(left, right)
            except (UnknownValueError, TypeError):
                continue
            msg = f"{operation.__name__} succeeded with UNKNOWN and {other!r}"
            raise AssertionError(msg)


@given(other=st.one_of(st.integers(), st.floats(allow_nan=False), st.text(max_size=8)))
def test_unknown_ordering_always_fails(other: object) -> None:
    for operation in (operator.lt, operator.le, operator.gt, operator.ge):
        for left, right in ((UNKNOWN, other), (other, UNKNOWN)):
            try:
                # mypy also rejects this, which is the static half of the same
                # guarantee. The test covers the runtime half.
                operation(left, right)  # type: ignore[arg-type]
            except (UnknownValueError, TypeError):
                continue
            msg = f"{operation.__name__} succeeded with UNKNOWN and {other!r}"
            raise AssertionError(msg)


@given(value=_values)
def test_unknown_is_never_equal_to_an_ordinary_value(value: object) -> None:
    assume(value is not UNKNOWN)
    assert value != UNKNOWN
