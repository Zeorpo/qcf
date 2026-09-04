"""Deterministic fingerprints for configuration, metadata, and files.

Every completed QCF run must record what produced it: the configuration, the
policy versions, the data. A fingerprint is how those records are compared
across machines and across time, so the mapping from value to fingerprint has to
be stable in the ways that matter and sensitive in the ways that matter.

Guaranteed properties, each asserted by the test-suite:

* mapping key order does not change a fingerprint;
* changing any supported value does change it;
* sequence order is significant, because a list is not a set;
* canonicalisation is idempotent, so already-canonical structures round-trip;
* :data:`~qcf.core.unknown.UNKNOWN` has a stable canonical form that no ordinary
  string can collide with;
* unsupported input types raise rather than being coerced to ``str``.

The last point is the reason this module is stricter than ``json.dumps``. A
fingerprint that silently accepts an unexpected type by stringifying it will
happily report that two different objects are identical.

Canonical forms
    ``Decimal`` becomes its exact ``str`` form, so ``Decimal("1.10")`` and
    ``Decimal("1.1")`` fingerprint differently: a fingerprint records what was
    configured, not what it is numerically equal to. ``Path`` becomes its POSIX
    spelling. ``datetime`` must be timezone-aware and is normalised to UTC;
    naive datetimes are rejected because a timestamp whose zone is unknown
    cannot be compared. ``date`` becomes its ISO form. Enum members become their
    canonicalised ``value``.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path, PurePath
from typing import Final
from uuid import UUID

from qcf.core.unknown import UNKNOWN, UNKNOWN_CANONICAL

__all__ = [
    "TAG_KEY",
    "canonical_json",
    "canonicalize",
    "fingerprint",
    "fingerprint_file",
]

#: Key marking a canonical envelope for a type JSON cannot represent directly.
TAG_KEY: Final = "__qcf_type__"

_CHUNK_SIZE: Final = 1 << 20

# Envelope tag -> the keys that envelope must carry, beyond TAG_KEY itself.
_ENVELOPE_SHAPES: Final[dict[str, frozenset[str]]] = {
    "unknown": frozenset(),
    "decimal": frozenset({"value"}),
    "date": frozenset({"value"}),
    "datetime": frozenset({"value"}),
    "path": frozenset({"value"}),
    "uuid": frozenset({"value"}),
}


def _envelope(tag: str, value: str) -> dict[str, str]:
    """Build a canonical envelope for a type JSON cannot represent directly.

    UNKNOWN is not built here: it carries no payload and its canonical form is
    the constant :data:`~qcf.core.unknown.UNKNOWN_CANONICAL`.
    """
    return {TAG_KEY: tag, "value": value}


def _canonical_datetime(value: datetime) -> dict[str, str]:
    """Return the canonical form of a timezone-aware datetime, normalised to UTC."""
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(
            "naive datetime cannot be fingerprinted: a timestamp whose timezone is "
            "unknown cannot be compared. Attach a timezone (QCF uses UTC internally)."
        )
    normalised = value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return _envelope("datetime", normalised)


def _canonical_mapping(value: Mapping[object, object]) -> dict[str, object]:
    """Canonicalise a mapping, passing through already-canonical envelopes."""
    if TAG_KEY in value:
        return _validated_envelope(value)
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(
                f"mapping keys must be strings to be fingerprinted; got "
                f"{type(key).__name__}. Convert the key explicitly so that the "
                f"conversion is visible in the record."
            )
        result[key] = canonicalize(item)
    return result


def _validated_envelope(value: Mapping[object, object]) -> dict[str, object]:
    """Validate and return an already-canonical envelope unchanged.

    Canonicalisation must be idempotent, so a structure this module produced has
    to survive a second pass. Validating the shape here means an ordinary
    mapping cannot impersonate an envelope and collide with a real value.
    """
    tag = value[TAG_KEY]
    if not isinstance(tag, str) or tag not in _ENVELOPE_SHAPES:
        raise TypeError(
            f"{TAG_KEY!r} is reserved for canonical envelopes produced by this "
            f"module; {tag!r} is not a recognised tag."
        )
    expected = _ENVELOPE_SHAPES[tag] | {TAG_KEY}
    actual = {str(key) for key in value}
    if actual != expected:
        raise TypeError(
            f"malformed canonical envelope for tag {tag!r}: expected keys "
            f"{sorted(expected)}, got {sorted(actual)}."
        )
    for key in _ENVELOPE_SHAPES[tag]:
        if not isinstance(value[key], str):
            raise TypeError(f"canonical envelope {tag!r} requires a string {key!r}.")
    return {str(key): value[key] for key in value}


def canonicalize(value: object) -> object:  # noqa: PLR0911, PLR0912 - a flat type dispatch
    """Convert ``value`` into a canonical, JSON-compatible structure.

    Args:
        value: The object to canonicalise.

    Returns:
        A structure built only from ``None``, ``bool``, ``int``, ``float``,
        ``str``, ``list``, and ``dict``.

    Raises:
        TypeError: If ``value`` contains a type with no canonical form, or a
            mapping with a non-string key, or a malformed canonical envelope.
        ValueError: If ``value`` contains a non-finite float or a naive
            datetime.
    """
    if value is None:
        return None
    if value is UNKNOWN:
        return dict(UNKNOWN_CANONICAL)
    if isinstance(value, Enum):
        return canonicalize(value.value)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(
                f"non-finite float {value!r} cannot be fingerprinted. NaN and "
                f"infinity are not permitted stand-ins for an unknown value; use "
                f"UNKNOWN instead."
            )
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, Decimal):
        return _envelope("decimal", str(value))
    if isinstance(value, datetime):
        return _canonical_datetime(value)
    if isinstance(value, date):
        return _envelope("date", value.isoformat())
    if isinstance(value, PurePath):
        return _envelope("path", value.as_posix())
    if isinstance(value, UUID):
        return _envelope("uuid", str(value))
    if isinstance(value, Mapping):
        return _canonical_mapping(value)
    if isinstance(value, (set, frozenset)):
        raise TypeError(
            "sets cannot be fingerprinted because their order is undefined. Sort "
            "the members explicitly so that the ordering is recorded in the code."
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [canonicalize(item) for item in value]
    raise TypeError(
        f"{type(value).__name__} has no canonical form and will not be coerced. "
        f"Add an explicit canonical form if this type must be fingerprinted."
    )


def canonical_json(value: object) -> str:
    """Return the canonical JSON text for ``value``.

    Keys are sorted at every level and separators carry no incidental
    whitespace, so the text depends only on the content.
    """
    return json.dumps(
        canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def fingerprint(value: object) -> str:
    """Return the SHA-256 hex digest of the canonical JSON for ``value``."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def fingerprint_file(path: Path | str) -> str:
    """Return the SHA-256 hex digest of a single file's bytes.

    Directories are refused rather than walked. Recursive hashing is a
    reasonable operation, but it is not what a caller asking to hash *a file*
    expects, and quietly doing it would make a manifest's meaning depend on the
    shape of the tree at the moment it ran.

    Args:
        path: Path to an existing regular file.

    Returns:
        The SHA-256 hex digest of the file's bytes.

    Raises:
        FileNotFoundError: If the path does not exist.
        IsADirectoryError: If the path is a directory.
    """
    resolved = Path(path)
    if resolved.is_dir():
        raise IsADirectoryError(
            f"{resolved} is a directory. fingerprint_file hashes one file; build a "
            f"manifest explicitly if a tree must be fingerprinted."
        )
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()
