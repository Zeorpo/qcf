"""Explicit UNKNOWN value semantics.

Later stages will hold fields -- fees, tick values, account limits, policy
versions, final trading dates -- whose real values must come from an
authoritative source. Until such a value is supplied it is *unknown*, and this
module makes that state explicit and hostile to accidental use.

``None``, ``0``, ``""``, ``False``, and ``NaN`` are all rejected as stand-ins.
Each of them is a value some arithmetic will happily consume, producing a number
that looks like a result and is not one. :data:`UNKNOWN` cannot be consumed:
every coercion and every arithmetic or ordering operation raises
:class:`~qcf.core.exceptions.UnknownValueError`.

Typical use::

    fee = config.exchange_fee  # may be UNKNOWN
    if is_unknown(fee):
        ...  # block the dependent claim
    net = gross - require_known(fee, field="exchange_fee")

Known limitation -- ``Decimal``
    ``decimal.Decimal`` inspects the concrete type of its argument instead of
    calling a coercion protocol, so ``Decimal(UNKNOWN)`` raises ``TypeError``
    from the standard library rather than :class:`UnknownValueError`. The
    conversion is still impossible, which is the property that matters, but the
    exception type differs. Code that must report the distinction should call
    :func:`require_known` before constructing a ``Decimal``. This limitation is
    asserted by the test-suite rather than left to be rediscovered.
"""

from __future__ import annotations

from typing import Any, ClassVar, Final, NoReturn, TypeGuard, final

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from qcf.core.exceptions import UnknownValueError

__all__ = ["UNKNOWN", "UNKNOWN_CANONICAL", "UnknownType", "is_unknown", "require_known"]

_LITERAL: Final = "UNKNOWN"

#: Canonical, JSON-compatible form of :data:`UNKNOWN`.
#:
#: A tagged mapping rather than the bare string ``"UNKNOWN"``, so that a genuine
#: string value of ``"UNKNOWN"`` and a genuinely unknown value never produce the
#: same fingerprint.
UNKNOWN_CANONICAL: Final[dict[str, str]] = {"__qcf_type__": "unknown"}


@final
class UnknownType:
    """The type of :data:`UNKNOWN`; a single immutable sentinel.

    The class is a singleton: constructing it always returns the same object, so
    ``is`` comparisons are reliable and pickling or copying cannot produce a
    second, subtly different unknown.

    Every prohibited operation is routed to :meth:`_prohibited` so that the
    prohibition is defined in exactly one place. Prohibited operations are all
    numeric coercions (``bool``, ``int``, ``float``, ``complex``, ``index``),
    all arithmetic including reflected forms, and all ordering comparisons.
    Equality and hashing remain available, because asking whether a value is
    unknown must not itself be an error.
    """

    _instance: ClassVar[UnknownType | None] = None
    __slots__ = ()

    def __new__(cls) -> UnknownType:
        """Return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # -- representation ----------------------------------------------------
    def __repr__(self) -> str:
        """Return the stable representation ``UNKNOWN``."""
        return _LITERAL

    def __str__(self) -> str:
        """Return the stable representation ``UNKNOWN``."""
        return _LITERAL

    # -- identity ----------------------------------------------------------
    def __eq__(self, other: object) -> bool:
        """Return ``True`` only for the sentinel itself."""
        return other is self

    def __ne__(self, other: object) -> bool:
        """Return ``True`` for anything that is not the sentinel."""
        return other is not self

    def __hash__(self) -> int:
        """Return a stable hash so UNKNOWN may be a mapping key or set member."""
        return hash(("qcf.core.unknown", _LITERAL))

    # -- immutability across copy, deepcopy, and pickle ---------------------
    def __copy__(self) -> UnknownType:
        """Return the singleton; copying cannot produce a second unknown."""
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> UnknownType:
        """Return the singleton; deep-copying cannot produce a second unknown."""
        del memo
        return self

    def __reduce__(self) -> tuple[type[UnknownType], tuple[()]]:
        """Support pickling by reconstructing through the singleton constructor."""
        return (UnknownType, ())

    # -- the single prohibition ---------------------------------------------
    def _prohibited(self, *args: object, **kwargs: object) -> NoReturn:
        """Raise :class:`UnknownValueError` for any prohibited operation."""
        del args, kwargs
        raise UnknownValueError(
            "UNKNOWN cannot be coerced, compared by order, or used in arithmetic. "
            "Establish the value from an authoritative source, or block the "
            "dependent calculation."
        )

    # Numeric coercions. `bool` is included deliberately: `if value:` on an
    # unknown quantity is the most likely way a missing value would slip through.
    __bool__ = _prohibited
    __int__ = _prohibited
    __float__ = _prohibited
    __complex__ = _prohibited
    __index__ = _prohibited

    # Arithmetic, including reflected forms so `1 + UNKNOWN` fails as loudly as
    # `UNKNOWN + 1`.
    __add__ = _prohibited
    __radd__ = _prohibited
    __sub__ = _prohibited
    __rsub__ = _prohibited
    __mul__ = _prohibited
    __rmul__ = _prohibited
    __truediv__ = _prohibited
    __rtruediv__ = _prohibited
    __floordiv__ = _prohibited
    __rfloordiv__ = _prohibited
    __mod__ = _prohibited
    __rmod__ = _prohibited
    __pow__ = _prohibited
    __rpow__ = _prohibited
    __neg__ = _prohibited
    __pos__ = _prohibited
    __abs__ = _prohibited
    __round__ = _prohibited

    # Ordering. Equality is permitted; "is this larger" is not.
    __lt__ = _prohibited
    __le__ = _prohibited
    __gt__ = _prohibited
    __ge__ = _prohibited

    # -- integration -------------------------------------------------------
    def to_canonical(self) -> dict[str, str]:
        """Return the canonical JSON-compatible form used for fingerprinting."""
        return dict(UNKNOWN_CANONICAL)

    @classmethod
    def _validate(cls, value: object) -> UnknownType:
        """Accept the sentinel itself or the exact literal ``"UNKNOWN"``."""
        if value is UNKNOWN:
            return UNKNOWN
        if isinstance(value, str) and value.strip().upper() == _LITERAL:
            return UNKNOWN
        raise ValueError(f"expected the literal {_LITERAL!r} or the UNKNOWN sentinel")

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,  # noqa: ANN401 - signature fixed by pydantic
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """Let pydantic validate and serialise UNKNOWN as a first-class value."""
        del source_type, handler
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda _: _LITERAL,
                return_schema=core_schema.str_schema(),
                # JSON only: a Python-mode dump keeps the sentinel so that
                # fingerprinting can tell UNKNOWN from the string "UNKNOWN".
                when_used="json",
            ),
        )


#: The single unknown-value sentinel.
UNKNOWN: Final[UnknownType] = UnknownType()


def is_unknown(value: object) -> TypeGuard[UnknownType]:
    """Return ``True`` if ``value`` is the UNKNOWN sentinel.

    Args:
        value: Any object.

    Returns:
        ``True`` only for :data:`UNKNOWN` itself. The string ``"UNKNOWN"``,
        ``None``, and ``NaN`` are not unknown values in this sense; they are
        ordinary values that happen to look like one.
    """
    return value is UNKNOWN


def require_known[T](value: T | UnknownType, *, field: str) -> T:
    """Return ``value`` if it is known, otherwise raise.

    This is the guard later stages call before any arithmetic. It exists so that
    the failure names the field, which a coercion error raised deep inside an
    expression could not.

    Args:
        value: A value that may be :data:`UNKNOWN`.
        field: The name of the field being read, used in the error message.

    Returns:
        The value, narrowed to its known type.

    Raises:
        UnknownValueError: If ``value`` is :data:`UNKNOWN`.
    """
    if value is UNKNOWN:
        raise UnknownValueError(
            f"{field!r} is UNKNOWN and must be established from an authoritative "
            f"source before it can be used."
        )
    return value  # type: ignore[return-value]
