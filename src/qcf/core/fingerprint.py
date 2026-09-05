"""Deterministic fingerprints for configuration, metadata, and files.

Every completed QCF run must record what produced it: the configuration, the
policy versions, the data. A fingerprint is how those records are compared
across machines and across time, so the mapping from value to fingerprint has to
be stable in the ways that matter and sensitive in the ways that matter.

Guaranteed properties, each asserted by the test-suite:

* mapping key order does not change a fingerprint;
* changing any supported value does change it;
* sequence order is significant, because a list is not a set;
* a mapping is always encoded as a mapping, even when its keys imitate an
  envelope, so a typed value and a lookalike dictionary never collide;
* :data:`~qcf.core.unknown.UNKNOWN` has a stable canonical form that no ordinary
  string can collide with;
* unsupported input types raise rather than being coerced to ``str``.

The last point is the reason this module is stricter than ``json.dumps``. A
fingerprint that silently accepts an unexpected type by stringifying it will
happily report that two different objects are identical.

Input contract
    :func:`canonicalize` takes **raw values**, never its own output. Feeding a
    canonical structure back in escapes it, because that structure is a mapping
    and mappings encode as mappings. An earlier version passed
    envelope-shaped mappings through unchanged to make canonicalisation
    idempotent, which made a lookalike dictionary indistinguishable from the
    typed value it imitated. See ADR-0008.

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

#: Version of the canonical encoding. Bumped by ADR-0008.
CANONICAL_FORMAT_VERSION: Final = 2

#: Prefix reserved for this module's own structural keys.
RESERVED_PREFIX: Final = "__qcf_"

#: Marker inserted to escape a raw key that would otherwise use the prefix.
ESCAPE_PREFIX: Final = "__qcf_esc_"

_CHUNK_SIZE: Final = 1 << 20


def escape_key(key: str) -> str:
    """Escape a raw mapping key so it cannot imitate a canonical envelope.

    Any key using the reserved prefix gains an escape marker. The transform is
    injective -- removing exactly one :data:`ESCAPE_PREFIX` inverts it -- so a
    raw mapping can never produce a bare :data:`TAG_KEY`, and an envelope is
    therefore only ever produced by a typed value.
    """
    return f"{ESCAPE_PREFIX}{key}" if key.startswith(RESERVED_PREFIX) else key


def unescape_key(key: str) -> str:
    """Invert :func:`escape_key`."""
    return key[len(ESCAPE_PREFIX) :] if key.startswith(ESCAPE_PREFIX) else key


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
    """Canonicalise a mapping as ordinary data, escaping reserved keys."""
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(
                f"mapping keys must be strings to be fingerprinted; got "
                f"{type(key).__name__}. Convert the key explicitly so that the "
                f"conversion is visible in the record."
            )
        # No collision check is needed: escape_key is injective, so distinct
        # keys stay distinct. That is asserted by the test-suite rather than
        # guarded by an unreachable branch here.
        result[escape_key(key)] = canonicalize(item)
    return result


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
