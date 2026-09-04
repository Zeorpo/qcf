"""UNKNOWN must be impossible to use by accident.

These tests are adversarial on purpose: each one is a way a missing financial
value could otherwise slip into a calculation and produce a number that looks
like a result.
"""

from __future__ import annotations

import copy
import math
import pickle
from collections.abc import Callable
from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from qcf.core.exceptions import UnknownValueError
from qcf.core.unknown import UNKNOWN, UNKNOWN_CANONICAL, UnknownType, is_unknown, require_known


def test_unknown_is_a_singleton() -> None:
    assert UnknownType() is UNKNOWN
    assert UnknownType() is UnknownType()


def test_representation_is_stable() -> None:
    assert repr(UNKNOWN) == "UNKNOWN"
    assert str(UNKNOWN) == "UNKNOWN"
    assert f"{UNKNOWN}" == "UNKNOWN"


def test_equality_is_identity_only() -> None:
    same = UnknownType()
    # Called explicitly so that both dunders are exercised, and so the assertion
    # reads as "the sentinel implements these" rather than as a tautology.
    assert UNKNOWN.__eq__(same) is True
    assert UNKNOWN.__ne__(same) is False
    assert UNKNOWN.__eq__("UNKNOWN") is False
    assert UNKNOWN.__eq__(None) is False
    assert UNKNOWN.__eq__(0) is False
    assert UNKNOWN.__ne__(0) is True


def test_unknown_is_hashable_and_usable_as_a_key() -> None:
    """Asking whether something is unknown must never itself raise."""
    assert {UNKNOWN: "fee"}[UNKNOWN] == "fee"
    assert len({UNKNOWN, UNKNOWN}) == 1


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(lambda: bool(UNKNOWN), id="bool"),
        pytest.param(lambda: int(UNKNOWN), id="int"),
        pytest.param(lambda: float(UNKNOWN), id="float"),
        pytest.param(lambda: complex(UNKNOWN), id="complex"),
        pytest.param(lambda: [0][UNKNOWN], id="index"),
        pytest.param(lambda: round(UNKNOWN), id="round"),
        pytest.param(lambda: abs(UNKNOWN), id="abs"),
        pytest.param(lambda: -UNKNOWN, id="neg"),
        pytest.param(lambda: +UNKNOWN, id="pos"),
    ],
)
def test_coercions_raise(operation: Callable[[], object]) -> None:
    with pytest.raises(UnknownValueError):
        operation()


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(lambda: UNKNOWN + 1, id="add"),
        pytest.param(lambda: 1 + UNKNOWN, id="radd"),
        pytest.param(lambda: UNKNOWN - 1, id="sub"),
        pytest.param(lambda: 1 - UNKNOWN, id="rsub"),
        pytest.param(lambda: UNKNOWN * 2, id="mul"),
        pytest.param(lambda: 2 * UNKNOWN, id="rmul"),
        pytest.param(lambda: UNKNOWN / 2, id="truediv"),
        pytest.param(lambda: 2 / UNKNOWN, id="rtruediv"),
        pytest.param(lambda: UNKNOWN // 2, id="floordiv"),
        pytest.param(lambda: 2 // UNKNOWN, id="rfloordiv"),
        pytest.param(lambda: UNKNOWN % 2, id="mod"),
        pytest.param(lambda: 2 % UNKNOWN, id="rmod"),
        pytest.param(lambda: UNKNOWN**2, id="pow"),
        pytest.param(lambda: 2**UNKNOWN, id="rpow"),
    ],
)
def test_arithmetic_raises_in_both_directions(operation: Callable[[], object]) -> None:
    """`1 + UNKNOWN` must fail as loudly as `UNKNOWN + 1`."""
    with pytest.raises(UnknownValueError):
        operation()


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param(lambda: UNKNOWN < 1, id="lt"),
        pytest.param(lambda: UNKNOWN <= 1, id="le"),
        pytest.param(lambda: UNKNOWN > 1, id="gt"),
        pytest.param(lambda: UNKNOWN >= 1, id="ge"),
    ],
)
def test_ordering_raises(operation: Callable[[], object]) -> None:
    """ "Is this above the limit?" has no answer when the limit is unknown."""
    with pytest.raises(UnknownValueError):
        operation()


def test_decimal_conversion_is_impossible() -> None:
    """Decimal inspects concrete types rather than calling a protocol.

    The conversion is still impossible, which is the property that matters, but
    the standard library raises TypeError rather than UnknownValueError. This
    documented limitation is asserted so that it cannot change unnoticed.
    """
    with pytest.raises((UnknownValueError, TypeError)):
        Decimal(UNKNOWN)  # type: ignore[arg-type]


def test_truthiness_cannot_be_tested_silently() -> None:
    """`if value:` is the likeliest accidental use, so it must raise."""

    def branch_on_unknown() -> str:
        return "truthy" if UNKNOWN else "falsy"

    with pytest.raises(UnknownValueError):
        branch_on_unknown()


def test_unknown_is_not_confusable_with_the_usual_stand_ins() -> None:
    # Typed as object so that the identity checks are a runtime assertion rather
    # than something mypy folds away as trivially true.
    substitutes: list[object] = [0, 0.0, "", None, False]
    for substitute in substitutes:
        assert UNKNOWN is not substitute
        assert substitute != UNKNOWN
    # NaN is a float that propagates silently; UNKNOWN is not a substitute for it
    # and it is not a substitute for UNKNOWN.
    nan = float("nan")
    assert math.isnan(nan)
    assert not is_unknown(nan)


def test_is_unknown_recognises_only_the_sentinel() -> None:
    assert is_unknown(UNKNOWN)
    assert not is_unknown("UNKNOWN")
    assert not is_unknown(None)
    assert not is_unknown(0)
    assert not is_unknown(float("nan"))


def test_copy_and_pickle_preserve_the_singleton() -> None:
    """A second unknown object would break `is` comparisons everywhere."""
    assert copy.copy(UNKNOWN) is UNKNOWN
    assert copy.deepcopy(UNKNOWN) is UNKNOWN
    assert pickle.loads(pickle.dumps(UNKNOWN)) is UNKNOWN  # noqa: S301
    assert copy.deepcopy({"fee": UNKNOWN})["fee"] is UNKNOWN


def test_unknown_has_no_instance_dictionary() -> None:
    """__slots__ keeps the sentinel immutable in practice, not only by convention."""
    with pytest.raises(AttributeError):
        UNKNOWN.value = 1  # type: ignore[attr-defined]


def test_canonical_form_is_tagged_and_copied() -> None:
    assert UNKNOWN.to_canonical() == UNKNOWN_CANONICAL
    # A fresh mapping each time, so a caller cannot mutate the shared constant.
    assert UNKNOWN.to_canonical() is not UNKNOWN_CANONICAL
    # Tagged rather than the bare string, which is what stops a genuine
    # "UNKNOWN" string colliding with a genuinely unknown value. The collision
    # property itself is asserted in test_fingerprint.py.
    assert UNKNOWN_CANONICAL == {"__qcf_type__": "unknown"}


def test_require_known_returns_known_values_unchanged() -> None:
    assert require_known(6.25, field="tick_value") == 6.25
    assert require_known("Z25", field="contract") == "Z25"
    assert require_known(0, field="offset") == 0


def test_require_known_names_the_field_it_blocked_on() -> None:
    with pytest.raises(UnknownValueError, match="'tick_value'"):
        require_known(UNKNOWN, field="tick_value")


def test_pydantic_validation_accepts_the_literal_and_the_sentinel() -> None:
    class Model(BaseModel):
        value: UnknownType

    assert Model(value=UNKNOWN).value is UNKNOWN
    assert Model(value="UNKNOWN").value is UNKNOWN  # type: ignore[arg-type]
    assert Model(value=" unknown ").value is UNKNOWN  # type: ignore[arg-type]


def test_pydantic_validation_rejects_other_values() -> None:
    class Model(BaseModel):
        value: UnknownType

    with pytest.raises(ValidationError):
        Model(value="v1")  # type: ignore[arg-type]


def test_pydantic_json_serialisation_is_the_plain_literal() -> None:
    class Model(BaseModel):
        value: UnknownType

    assert Model(value=UNKNOWN).model_dump(mode="json") == {"value": "UNKNOWN"}
    assert Model(value=UNKNOWN).model_dump(mode="python")["value"] is UNKNOWN
