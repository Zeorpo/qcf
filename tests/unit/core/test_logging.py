"""Logs are evidence, so redaction is tested as a security control.

The values used below are obvious placeholders. No real credential appears in
this repository, including in its tests.
"""

from __future__ import annotations

import io
import json

import pytest

from qcf.core.logging import (
    REDACTED,
    bind_run_context,
    clear_run_context,
    configure_logging,
    get_logger,
    is_sensitive_key,
    redact,
)

PLACEHOLDER = "placeholder-not-a-real-credential"


@pytest.mark.parametrize(
    "key",
    [
        "password",
        "PASSWORD",
        "user_password",
        "secret",
        "client_secret",
        "token",
        "access-token",
        "api_key",
        "API-KEY",
        "apiKey",
        "credential",
        "authorization",
        "Cookie",
        "account_id",
        "accountId",
        "ACCOUNT.ID",
    ],
)
def test_sensitive_keys_are_recognised_in_any_spelling(key: str) -> None:
    assert is_sensitive_key(key)


@pytest.mark.parametrize(
    "key", ["mode", "data_root", "random_seed", "tick_size", "contract", "account_equity"]
)
def test_ordinary_keys_are_not_redacted(key: str) -> None:
    assert not is_sensitive_key(key)


def test_redaction_replaces_values_not_keys() -> None:
    assert redact({"password": PLACEHOLDER}) == {"password": REDACTED}


def test_redaction_reaches_nested_mappings() -> None:
    payload = {"outer": {"inner": {"api_key": PLACEHOLDER, "mode": "PAPER"}}}
    assert redact(payload) == {"outer": {"inner": {"api_key": REDACTED, "mode": "PAPER"}}}


def test_redaction_reaches_inside_sequences() -> None:
    payload = {"items": [{"token": PLACEHOLDER}, {"mode": "PAPER"}]}
    assert redact(payload) == {"items": [{"token": REDACTED}, {"mode": "PAPER"}]}


def test_redaction_replaces_a_whole_nested_value() -> None:
    """A sensitive key hides everything beneath it, not just a scalar."""
    payload = {"credentials": {"user": "alex", "password": PLACEHOLDER}}
    assert redact(payload) == {"credentials": REDACTED}


def test_redaction_does_not_mutate_its_input() -> None:
    payload = {"password": PLACEHOLDER, "nested": {"token": PLACEHOLDER}}
    snapshot = {"password": PLACEHOLDER, "nested": {"token": PLACEHOLDER}}
    redact(payload)
    assert payload == snapshot


def test_redaction_preserves_list_and_tuple_kinds() -> None:
    assert redact(["a", "b"]) == ["a", "b"]
    assert redact(("a", "b")) == ("a", "b")


def test_redaction_leaves_scalars_alone() -> None:
    assert redact(7) == 7
    assert redact("plain") == "plain"
    assert redact(None) is None


def test_console_output_carries_a_utc_timestamp_and_level() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="console", stream=stream)
    get_logger("test").info("session started", mode="RESEARCH")
    rendered = stream.getvalue()
    assert "session started" in rendered
    assert "mode=RESEARCH" in rendered
    # An ISO-8601 UTC timestamp, not a local one.
    assert "Z" in rendered.split()[0] or "+00:00" in rendered


def test_json_output_is_machine_readable_with_utc_timestamps() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    get_logger("test").info("session started", mode="RESEARCH")
    record = json.loads(stream.getvalue())
    assert record["event"] == "session started"
    assert record["mode"] == "RESEARCH"
    assert record["level"] == "info"
    assert record["timestamp"].endswith("Z")


def test_a_sensitive_value_never_reaches_rendered_output() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    get_logger("test").info("connecting", api_key=PLACEHOLDER, nested={"token": PLACEHOLDER})
    rendered = stream.getvalue()
    assert PLACEHOLDER not in rendered
    assert rendered.count(REDACTED) == 2


def test_a_sensitive_value_bound_into_context_is_also_redacted() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    bind_run_context(session_token=PLACEHOLDER)
    get_logger("test").info("running")
    assert PLACEHOLDER not in stream.getvalue()


def test_run_context_carries_version_and_mode() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream, version="0.0.0", mode="DISABLED")
    get_logger("test").info("started")
    record = json.loads(stream.getvalue())
    assert record["version"] == "0.0.0"
    assert record["mode"] == "DISABLED"


def test_levels_below_the_threshold_are_dropped() -> None:
    stream = io.StringIO()
    configure_logging(level="WARNING", fmt="json", stream=stream)
    logger = get_logger("test")
    logger.info("ignored")
    logger.warning("kept")
    lines = [line for line in stream.getvalue().splitlines() if line]
    assert len(lines) == 1
    assert json.loads(lines[0])["event"] == "kept"


def test_reconfiguring_does_not_duplicate_output() -> None:
    """Calling configure twice must replace the configuration, not add to it."""
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    configure_logging(level="INFO", fmt="json", stream=stream)
    get_logger("test").info("once")
    assert len([line for line in stream.getvalue().splitlines() if line]) == 1


def test_an_unknown_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown log level"):
        configure_logging(level="VERBOSE", stream=io.StringIO())


def test_clearing_the_run_context_removes_bound_values() -> None:
    """Bound context is process-global; leaving it set would leak between runs."""
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream, version="0.0.0")
    clear_run_context()
    get_logger("test").info("after clear")
    assert "version" not in json.loads(stream.getvalue())
