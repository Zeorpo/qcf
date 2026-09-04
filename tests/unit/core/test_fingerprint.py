"""Fingerprints must be stable where content is equal and sensitive everywhere else."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path, PurePosixPath, PureWindowsPath
from uuid import UUID

import pytest

from qcf.core.enums import OperatingMode
from qcf.core.fingerprint import (
    TAG_KEY,
    canonical_json,
    canonicalize,
    fingerprint,
    fingerprint_file,
)
from qcf.core.unknown import UNKNOWN

# The published NIST SHA-256 vector for b"abc". A public test value, not a
# credential.
SHA256_OF_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"  # pragma: allowlist secret  # noqa: E501


def test_mapping_key_order_does_not_change_the_fingerprint() -> None:
    assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})


def test_nested_mapping_key_order_does_not_change_the_fingerprint() -> None:
    left = {"outer": {"a": 1, "b": {"x": 1, "y": 2}}}
    right = {"outer": {"b": {"y": 2, "x": 1}, "a": 1}}
    assert fingerprint(left) == fingerprint(right)


def test_changing_a_value_changes_the_fingerprint() -> None:
    assert fingerprint({"a": 1}) != fingerprint({"a": 2})


def test_sequence_order_is_significant() -> None:
    """A list is not a set; reordering it is a different configuration."""
    assert fingerprint([1, 2, 3]) != fingerprint([3, 2, 1])


def test_int_and_float_of_equal_value_differ() -> None:
    assert fingerprint(1) != fingerprint(1.0)


def test_int_and_boolean_do_not_collide() -> None:
    assert fingerprint(True) != fingerprint(1)
    assert fingerprint(False) != fingerprint(0)


def test_unknown_does_not_collide_with_the_string_unknown() -> None:
    """The distinction between "no value" and the word is load-bearing."""
    assert fingerprint(UNKNOWN) != fingerprint("UNKNOWN")
    assert fingerprint({"fee": UNKNOWN}) != fingerprint({"fee": "UNKNOWN"})


def test_unknown_does_not_collide_with_none_or_zero() -> None:
    assert fingerprint(UNKNOWN) != fingerprint(None)
    assert fingerprint(UNKNOWN) != fingerprint(0)


def test_decimal_records_scale() -> None:
    """A fingerprint records what was configured, not what it equals."""
    assert Decimal("1.10") == Decimal("1.1")
    assert fingerprint(Decimal("1.10")) != fingerprint(Decimal("1.1"))


def test_decimal_does_not_collide_with_its_string_form() -> None:
    assert fingerprint(Decimal("6.25")) != fingerprint("6.25")


def test_enum_canonicalises_to_its_value() -> None:
    assert canonicalize(OperatingMode.PAPER) == "PAPER"
    assert fingerprint(OperatingMode.PAPER) == fingerprint("PAPER")


def test_paths_use_posix_spelling() -> None:
    assert canonicalize(PurePosixPath("a/b")) == {TAG_KEY: "path", "value": "a/b"}
    assert fingerprint(PureWindowsPath(r"a\b")) == fingerprint(PurePosixPath("a/b"))


def test_path_does_not_collide_with_its_string_form() -> None:
    assert fingerprint(PurePosixPath("data")) != fingerprint("data")


def test_dates_and_datetimes_have_distinct_canonical_forms() -> None:
    assert canonicalize(date(2026, 9, 3)) == {TAG_KEY: "date", "value": "2026-09-03"}
    moment = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
    assert canonicalize(moment) == {TAG_KEY: "datetime", "value": "2026-09-03T12:00:00Z"}


def test_datetimes_are_normalised_to_utc() -> None:
    """The same instant fingerprints identically however it was expressed."""
    utc_moment = datetime(2026, 9, 3, 17, 0, tzinfo=UTC)
    offset_moment = datetime(2026, 9, 3, 13, 0, tzinfo=timezone(timedelta(hours=-4)))
    assert fingerprint(utc_moment) == fingerprint(offset_moment)


def test_naive_datetimes_are_rejected() -> None:
    with pytest.raises(ValueError, match="naive datetime"):
        canonicalize(datetime(2026, 9, 3, 12, 0))  # noqa: DTZ001 - that is the point


def test_uuid_has_a_canonical_form() -> None:
    identifier = UUID("12345678-1234-5678-1234-567812345678")
    assert canonicalize(identifier) == {TAG_KEY: "uuid", "value": str(identifier)}


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_floats_are_rejected(value: float) -> None:
    """NaN is not an unknown value; it is a float that propagates silently."""
    with pytest.raises(ValueError, match="non-finite"):
        canonicalize(value)


def test_non_string_mapping_keys_are_rejected() -> None:
    with pytest.raises(TypeError, match="mapping keys must be strings"):
        canonicalize({1: "one"})


def test_sets_are_rejected_rather_than_silently_ordered() -> None:
    with pytest.raises(TypeError, match="order is undefined"):
        canonicalize({1, 2, 3})


def test_unsupported_types_raise_instead_of_being_stringified() -> None:
    class Opaque:
        pass

    with pytest.raises(TypeError, match="has no canonical form"):
        canonicalize(Opaque())


def test_bytes_are_rejected() -> None:
    with pytest.raises(TypeError, match="has no canonical form"):
        canonicalize(b"bytes")


def test_tuples_canonicalise_to_lists_preserving_order() -> None:
    assert canonicalize((1, 2)) == [1, 2]
    assert fingerprint((1, 2)) == fingerprint([1, 2])


def test_canonical_json_sorts_keys_and_omits_incidental_whitespace() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_canonical_json_preserves_non_ascii() -> None:
    assert canonical_json({"k": "é"}) == '{"k":"é"}'


def test_an_envelope_shaped_mapping_round_trips() -> None:
    """Canonicalisation must be idempotent, so envelopes survive a second pass."""
    once = canonicalize(Decimal("1.5"))
    assert canonicalize(once) == once


def test_a_forged_envelope_tag_is_rejected() -> None:
    with pytest.raises(TypeError, match="not a recognised tag"):
        canonicalize({TAG_KEY: "fabricated", "value": "x"})


def test_a_malformed_envelope_is_rejected() -> None:
    with pytest.raises(TypeError, match="malformed canonical envelope"):
        canonicalize({TAG_KEY: "decimal"})


def test_an_envelope_with_a_non_string_payload_is_rejected() -> None:
    with pytest.raises(TypeError, match="requires a string"):
        canonicalize({TAG_KEY: "decimal", "value": 1})


def test_fingerprint_is_a_sha256_hex_digest() -> None:
    digest = fingerprint({"a": 1})
    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")


def test_fingerprint_is_stable_across_calls() -> None:
    payload = {"mode": OperatingMode.RESEARCH, "seed": 7, "policy": UNKNOWN}
    assert fingerprint(payload) == fingerprint(payload)


def test_fingerprint_file_hashes_bytes(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_bytes(b"abc")
    assert fingerprint_file(target) == SHA256_OF_ABC


def test_fingerprint_file_accepts_a_string_path(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_bytes(b"abc")
    assert fingerprint_file(str(target)) == fingerprint_file(target)


def test_fingerprint_file_rejects_directory(tmp_path: Path) -> None:
    """Hashing a tree by surprise would make a manifest's meaning ambient."""
    with pytest.raises(IsADirectoryError):
        fingerprint_file(tmp_path)


def test_fingerprint_file_reports_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        fingerprint_file(tmp_path / "absent.txt")


def test_large_files_hash_across_chunk_boundaries(tmp_path: Path) -> None:
    payload = b"x" * ((1 << 20) + 17)
    target = tmp_path / "large.bin"
    target.write_bytes(payload)
    assert fingerprint_file(target) == hashlib.sha256(payload).hexdigest()
