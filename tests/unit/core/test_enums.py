"""Enum values are a contract, so they are asserted exactly."""

from __future__ import annotations

import pytest

from qcf.core.enums import DataQualityDisposition, HaltState, OperatingMode, Severity


def test_operating_mode_has_exactly_the_permitted_members() -> None:
    assert {member.value for member in OperatingMode} == {
        "DISABLED",
        "RESEARCH",
        "BACKTEST",
        "REPLAY",
        "PAPER",
    }


@pytest.mark.boundary
@pytest.mark.parametrize("forbidden", ["LIVE", "live", "Live", "REAL", "PRODUCTION"])
def test_operating_mode_has_no_live_member(forbidden: str) -> None:
    """No live mode may exist, under any spelling."""
    assert forbidden not in OperatingMode.__members__
    with pytest.raises(ValueError, match="is not a valid OperatingMode"):
        OperatingMode(forbidden)


def test_halt_state_has_exactly_the_declared_members() -> None:
    assert {member.value for member in HaltState} == {
        "DISABLED",
        "READY",
        "RUNNING_PAPER",
        "ENTRY_BLOCKED",
        "FLATTENING_SIMULATED",
        "HALTED",
        "INVESTIGATION_REQUIRED",
        "REVALIDATION_REQUIRED",
    }


def test_severity_has_exactly_the_declared_members() -> None:
    assert {member.value for member in Severity} == {"INFO", "WARNING", "ERROR", "CRITICAL"}


def test_data_quality_disposition_has_exactly_the_declared_members() -> None:
    assert {member.value for member in DataQualityDisposition} == {
        "ACCEPT",
        "FLAG",
        "QUARANTINE",
        "REJECT_DATASET",
        "REQUIRES_HUMAN_DECISION",
    }


def test_data_quality_disposition_offers_no_silent_drop() -> None:
    """Every finding must be dispositioned; discarding one is not an option."""
    values = {member.value for member in DataQualityDisposition}
    assert not values & {"DROP", "IGNORE", "SKIP", "DISCARD"}


@pytest.mark.parametrize("enum_cls", [OperatingMode, HaltState, Severity, DataQualityDisposition])
def test_enums_are_string_valued_and_round_trip(enum_cls: type[OperatingMode]) -> None:
    """StrEnum members compare equal to their text, so serialisation is lossless."""
    for member in enum_cls:
        assert member == member.value
        assert enum_cls(member.value) is member
