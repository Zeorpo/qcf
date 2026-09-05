"""The exception hierarchy is what callers catch, so its shape is asserted."""

from __future__ import annotations

import pytest

from qcf.core.exceptions import (
    BoundaryViolationError,
    ConfigurationError,
    InvariantViolationError,
    PolicyExpiredError,
    QCFError,
    UnknownValueError,
)

_SUBCLASSES = [
    BoundaryViolationError,
    ConfigurationError,
    InvariantViolationError,
    PolicyExpiredError,
    UnknownValueError,
]


@pytest.mark.parametrize("exc_cls", _SUBCLASSES)
def test_every_qcf_error_derives_from_the_base(exc_cls: type[QCFError]) -> None:
    assert issubclass(exc_cls, QCFError)
    assert issubclass(exc_cls, Exception)


def test_base_is_not_a_bare_exception_alias() -> None:
    """Catching QCFError must not catch unrelated library failures."""
    assert QCFError is not Exception
    assert not issubclass(ValueError, QCFError)
    assert not issubclass(KeyError, QCFError)


@pytest.mark.parametrize("exc_cls", _SUBCLASSES)
def test_errors_carry_their_message(exc_cls: type[QCFError]) -> None:
    error = exc_cls("tick_value could not be established")
    assert str(error) == "tick_value could not be established"


@pytest.mark.parametrize("exc_cls", _SUBCLASSES)
def test_errors_are_distinct_types(exc_cls: type[QCFError]) -> None:
    """A caller catching one condition must not silently catch another."""
    others = [other for other in _SUBCLASSES if other is not exc_cls]
    for other in others:
        assert not issubclass(exc_cls, other)
