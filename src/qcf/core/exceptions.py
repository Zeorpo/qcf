"""Exception hierarchy for QCF.

Only exceptions that Stage 00 code actually raises are defined, plus
:class:`PolicyExpiredError`, which is declared here because policy expiry is a
fail-closed condition that later stages must not invent a local spelling for.

Exception messages name *what* failed and *where*, never the offending value
when that value could be a credential. Callers that need to report a value are
responsible for redacting it first; see :mod:`qcf.core.logging`.
"""

from __future__ import annotations

__all__ = [
    "BoundaryViolationError",
    "ConfigurationError",
    "InvariantViolationError",
    "PolicyExpiredError",
    "QCFError",
    "UnknownValueError",
]


class QCFError(Exception):
    """Base class for every error QCF raises deliberately.

    Catching :class:`QCFError` catches conditions QCF detected and chose to
    signal. It does not catch programming errors from the standard library or
    third-party code, which should surface unmodified.
    """


class ConfigurationError(QCFError):
    """Configuration is missing, malformed, or internally inconsistent.

    Raised in preference to falling back to a default, because a silently
    defaulted financial setting is the failure mode this project is built to
    avoid.
    """


class UnknownValueError(QCFError):
    """An UNKNOWN value was used where a known value is required.

    Raised when code attempts to coerce, compare, or compute with
    :data:`qcf.core.unknown.UNKNOWN`. The correct response is to establish the
    value from an authoritative source, or to block the dependent claim -- never
    to substitute zero, ``None``, an empty string, or NaN.
    """


class BoundaryViolationError(QCFError):
    """A non-negotiable project boundary was violated.

    Boundaries include the absence of a live operating mode, the absence of
    broker connectivity, and the prohibition on tracking market data. This error
    signals a defect in QCF itself rather than bad input.
    """


class InvariantViolationError(QCFError):
    """An invariant that the system relies upon does not hold.

    Raised where continuing would produce results that cannot be trusted. It is
    always preferable to fail here than to record a number whose meaning is
    unknown.
    """


class PolicyExpiredError(QCFError):
    """A versioned external policy is expired, missing, or unreviewed.

    Declared in Stage 00 for use by later policy validation. A policy whose age
    or provenance cannot be established blocks new simulated exposure; it does
    not fall back to the last known version.
    """
