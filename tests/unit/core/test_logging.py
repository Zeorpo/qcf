"""Logs are evidence, so redaction is tested as a security control.

The values used below are obvious placeholders. No real credential appears in
this repository, including in its tests.
"""

from __future__ import annotations

import io
import json

import pytest

from qcf.core.config import AppConfig
from qcf.core.exceptions import ConfigurationError
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


# --------------------------------------------------------------------------
# Correction C (R-04): the exception-output contract.
#
# Key-based redaction cannot sanitise a traceback: it is one string under a key
# that is not sensitive by name, so no key rule inspects it at any position in
# the chain. Reordering the processors does not help, which is why the fix is to
# not emit the text.
# --------------------------------------------------------------------------


def _json_line(stream: io.StringIO) -> dict[str, object]:
    lines = [line for line in stream.getvalue().splitlines() if line]
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert isinstance(parsed, dict)
    return parsed


def test_safe_mode_omits_exception_text() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    try:
        raise ValueError(f"token {PLACEHOLDER}")
    except ValueError:
        get_logger("test").exception("operation failed")
    assert PLACEHOLDER not in stream.getvalue()


def test_safe_mode_reports_the_exception_type() -> None:
    """Omitting the message must not make failures unclassifiable."""
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    try:
        raise ValueError(f"token {PLACEHOLDER}")
    except ValueError:
        get_logger("test").exception("operation failed")
    record = _json_line(stream)
    assert record["error_type"] == "ValueError"
    assert "exception" not in record


def test_safe_mode_reports_a_stable_error_code_for_qcf_errors() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    try:
        raise ConfigurationError(f"bad {PLACEHOLDER}")
    except ConfigurationError:
        get_logger("test").exception("config failed")
    record = _json_line(stream)
    assert record["error_code"] == "QCF_CONFIG_INVALID"
    assert PLACEHOLDER not in stream.getvalue()


def test_safe_mode_does_not_leak_a_chained_cause() -> None:
    """A suppressed message must not reappear as the underlying exception."""
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    try:
        try:
            raise ValueError(f"inner {PLACEHOLDER}")
        except ValueError as inner:
            raise RuntimeError("outer") from inner
    except RuntimeError:
        get_logger("test").exception("failed")
    record = _json_line(stream)
    assert PLACEHOLDER not in stream.getvalue()
    assert record["error_type"] == "RuntimeError"


def test_safe_mode_covers_the_console_renderer_too() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="console", stream=stream)
    try:
        raise ValueError(f"token {PLACEHOLDER}")
    except ValueError:
        get_logger("test").exception("failed")
    assert PLACEHOLDER not in stream.getvalue()
    assert "ValueError" in stream.getvalue()


def test_an_invalid_configuration_does_not_leak_through_the_logger() -> None:
    """End-to-end for R-03 plus R-04: the path that compounded them."""
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    try:
        AppConfig.load(random_seed=PLACEHOLDER)
    except ConfigurationError:
        get_logger("test").exception("configuration rejected")
    assert PLACEHOLDER not in stream.getvalue()


def test_full_mode_is_opt_in_and_documented_as_unsafe() -> None:
    """The escape hatch exists for local debugging; pin that it is opt-in."""
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream, exception_output="full")
    try:
        raise ValueError(f"token {PLACEHOLDER}")
    except ValueError:
        get_logger("test").exception("failed")
    assert PLACEHOLDER in stream.getvalue(), "full mode is expected to emit the message"


def test_key_redaction_still_applies_alongside_the_exception_contract() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    try:
        raise ValueError("boom")
    except ValueError:
        get_logger("test").exception("failed", api_key=PLACEHOLDER, nested={"token": PLACEHOLDER})
    assert PLACEHOLDER not in stream.getvalue()
    assert stream.getvalue().count(REDACTED) == 2


def test_free_text_in_the_event_message_is_not_scanned() -> None:
    """The documented limit, asserted so it cannot be quietly overstated.

    Key-based redaction makes no promise about arbitrary text a caller passes as
    the event itself. This test pins that boundary rather than implying the
    logger sanitises everything.
    """
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    get_logger("test").info(f"starting with {PLACEHOLDER}")
    assert PLACEHOLDER in stream.getvalue()


def test_successive_configurations_keep_separate_run_contexts() -> None:
    first = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=first, version="0.0.0")
    clear_run_context()
    second = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=second, mode="RESEARCH")
    get_logger("test").info("event")
    record = _json_line(second)
    assert record["mode"] == "RESEARCH"
    assert "version" not in record


@pytest.mark.parametrize("supplied", ["instance", "tuple", "true", "none"])
def test_every_exc_info_form_is_handled(supplied: str) -> None:
    """structlog accepts several shapes; all must reach the safe contract."""
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    logger = get_logger("test")
    error = ValueError(f"token {PLACEHOLDER}")
    if supplied == "instance":
        logger.error("failed", exc_info=error)
    elif supplied == "tuple":
        logger.error("failed", exc_info=(type(error), error, None))
    elif supplied == "true":
        try:
            raise error
        except ValueError:
            logger.error("failed", exc_info=True)
    else:
        logger.error("failed", exc_info=None)
    rendered = stream.getvalue()
    assert PLACEHOLDER not in rendered
    if supplied != "none":
        assert "ValueError" in rendered


def test_an_empty_exc_info_tuple_is_tolerated() -> None:
    stream = io.StringIO()
    configure_logging(level="INFO", fmt="json", stream=stream)
    get_logger("test").error("failed", exc_info=())
    assert "error_type" not in _json_line(stream)
