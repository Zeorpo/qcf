"""Configuration must be immutable, validated, and free of silent defaults."""

from __future__ import annotations

import traceback
from pathlib import Path

import pytest
from pydantic import ValidationError

from qcf.core.config import (
    _REDACTED_FIELD,
    ENV_PREFIX,
    AppConfig,
    _YamlSettingsSource,
)
from qcf.core.enums import OperatingMode
from qcf.core.exceptions import ConfigurationError
from qcf.core.unknown import UNKNOWN, is_unknown


def test_default_mode_is_disabled() -> None:
    """A process that has not been told what it is for does nothing."""
    assert AppConfig().mode is OperatingMode.DISABLED


def test_defaults_are_non_financial_and_safe() -> None:
    config = AppConfig()
    assert config.app_name == "qcf"
    assert config.timezone == "UTC"
    assert config.log_level == "INFO"
    assert config.log_format == "console"
    assert config.base_path is None
    assert config.random_seed == 0


def test_policy_version_defaults_to_unknown_not_a_placeholder() -> None:
    """No policy set has been retrieved or reviewed, so none may be named."""
    assert is_unknown(AppConfig().policy_version)


def test_configuration_is_frozen() -> None:
    config = AppConfig()
    with pytest.raises(ValidationError):
        config.mode = OperatingMode.PAPER


def test_unknown_keys_are_rejected() -> None:
    """A setting that was configured and never read is worse than none at all."""
    with pytest.raises(ValidationError):
        AppConfig(maximum_contracts=5)  # type: ignore[call-arg]


def test_load_wraps_validation_failures_as_configuration_errors() -> None:
    with pytest.raises(ConfigurationError, match="invalid QCF configuration"):
        AppConfig.load(mode="LIVE")


@pytest.mark.parametrize("forbidden", ["LIVE", "live", "PRODUCTION", "REAL"])
def test_no_live_mode_can_be_configured(forbidden: str) -> None:
    with pytest.raises(ConfigurationError):
        AppConfig.load(mode=forbidden)


def test_timezone_cannot_be_changed_from_utc() -> None:
    with pytest.raises(ConfigurationError):
        AppConfig.load(timezone="America/New_York")


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ConfigurationError):
        AppConfig.load(log_level="VERBOSE")


def test_yaml_values_are_loaded(tmp_path: Path) -> None:
    path = tmp_path / "conf.yaml"
    path.write_text("mode: RESEARCH\nrandom_seed: 11\n", encoding="utf-8")
    config = AppConfig.load(path)
    assert config.mode is OperatingMode.RESEARCH
    assert config.random_seed == 11


def test_an_empty_yaml_file_yields_defaults(tmp_path: Path) -> None:
    path = tmp_path / "conf.yaml"
    path.write_text("", encoding="utf-8")
    assert AppConfig.load(path).mode is OperatingMode.DISABLED


def test_a_named_missing_file_is_an_error(tmp_path: Path) -> None:
    """A mistyped path must not quietly become "use the defaults"."""
    with pytest.raises(ConfigurationError, match="does not exist"):
        AppConfig.load(tmp_path / "absent.yaml")


def test_malformed_yaml_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "conf.yaml"
    path.write_text("mode: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not valid YAML"):
        AppConfig.load(path)


def test_yaml_that_is_not_a_mapping_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "conf.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="mapping at the top level"):
        AppConfig.load(path)


def test_yaml_with_an_unknown_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "conf.yaml"
    path.write_text("modee: RESEARCH\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        AppConfig.load(path)


def test_environment_overrides_are_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}MODE", "BACKTEST")
    assert AppConfig.load().mode is OperatingMode.BACKTEST


def test_environment_overrides_beat_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "conf.yaml"
    path.write_text("mode: RESEARCH\nrandom_seed: 1\n", encoding="utf-8")
    monkeypatch.setenv(f"{ENV_PREFIX}MODE", "REPLAY")
    config = AppConfig.load(path)
    assert config.mode is OperatingMode.REPLAY
    assert config.random_seed == 1


def test_explicit_arguments_beat_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}MODE", "REPLAY")
    assert AppConfig.load(mode="PAPER").mode is OperatingMode.PAPER


def test_unprefixed_environment_variables_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODE", "PAPER")
    assert AppConfig.load().mode is OperatingMode.DISABLED


def test_paths_resolve_against_base_path_not_cwd(tmp_path: Path) -> None:
    """Configuring base_path makes a run independent of where it was started."""
    base = tmp_path / "checkout"
    base.mkdir()
    config = AppConfig.load(base_path=base)
    assert config.resolved_data_root == base / "data"
    assert config.resolved_report_root == base / "reports"


def test_paths_fall_back_to_the_working_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    config = AppConfig.load()
    assert config.resolved_data_root == tmp_path / "data"


def test_absolute_configured_paths_are_left_alone(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    config = AppConfig.load(base_path=tmp_path, data_root=elsewhere)
    assert config.resolved_data_root == elsewhere


def test_fingerprint_ignores_yaml_presentation(tmp_path: Path) -> None:
    """Key order, quoting, and indentation are not part of the configuration."""
    first = tmp_path / "a.yaml"
    first.write_text("mode: RESEARCH\nrandom_seed: 3\n", encoding="utf-8")
    second = tmp_path / "b.yaml"
    second.write_text('random_seed:   3\n\nmode:  "RESEARCH"\n', encoding="utf-8")
    assert AppConfig.load(first).fingerprint() == AppConfig.load(second).fingerprint()


def test_fingerprint_changes_when_a_value_changes() -> None:
    assert AppConfig.load().fingerprint() != AppConfig.load(random_seed=1).fingerprint()


def test_fingerprint_distinguishes_unknown_policy_from_a_named_one() -> None:
    unknown = AppConfig.load()
    named = AppConfig.load(policy_version="lucid-2026-09")
    assert is_unknown(unknown.policy_version)
    assert unknown.fingerprint() != named.fingerprint()


def test_the_literal_unknown_string_becomes_the_sentinel() -> None:
    assert is_unknown(AppConfig.load(policy_version="UNKNOWN").policy_version)
    assert is_unknown(AppConfig.load(policy_version=" unknown ").policy_version)


def test_canonical_dump_keeps_the_unknown_sentinel() -> None:
    assert AppConfig.load().canonical()["policy_version"] is UNKNOWN


def test_redacted_output_is_json_safe() -> None:
    redacted = AppConfig.load(base_path=Path("/tmp/x")).redacted()  # noqa: S108
    assert redacted["policy_version"] == "UNKNOWN"
    assert redacted["mode"] == "DISABLED"
    assert isinstance(redacted["data_root"], str)


def test_the_yaml_source_exposes_single_field_lookup(tmp_path: Path) -> None:
    """`get_field_value` is part of the settings-source protocol.

    pydantic-settings reads this source through `__call__`, so the per-field
    accessor would otherwise go unexercised while still being part of the
    contract the base class requires.
    """
    path = tmp_path / "conf.yaml"
    path.write_text("mode: RESEARCH\n", encoding="utf-8")
    source = _YamlSettingsSource(AppConfig, path)

    value, key, is_complex = source.get_field_value(AppConfig.model_fields["mode"], "mode")
    assert (value, key, is_complex) == ("RESEARCH", "mode", False)

    missing, key, _ = source.get_field_value(AppConfig.model_fields["app_name"], "app_name")
    assert missing is None
    assert key == "app_name"


def test_a_source_with_no_path_supplies_nothing() -> None:
    assert _YamlSettingsSource(AppConfig, None)() == {}


# --------------------------------------------------------------------------
# Correction B (R-03): diagnostics must not echo input values.
# The marker below is inert: it is not a credential and stands in for one.
# --------------------------------------------------------------------------

MARKER = "INERT-MARKER-9Q7"


def test_an_invalid_explicit_value_is_not_echoed() -> None:
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(random_seed=MARKER)
    assert MARKER not in str(caught.value)
    assert MARKER not in repr(caught.value)
    assert MARKER not in repr(caught.value.details)


def test_an_invalid_environment_value_is_not_echoed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}RANDOM_SEED", MARKER)
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load()
    assert MARKER not in str(caught.value)


def test_an_invalid_yaml_value_is_not_echoed(tmp_path: Path) -> None:
    path = tmp_path / "conf.yaml"
    path.write_text(f"random_seed: {MARKER}\n", encoding="utf-8")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    assert MARKER not in str(caught.value)


def test_a_sensitive_extra_field_name_is_redacted() -> None:
    """The extra-field location is an unvalidated key and may itself be secret."""
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(**{f"api_key_{MARKER}": "x"})
    assert MARKER not in str(caught.value)
    # Asserted against the constant rather than a copied literal, so renaming
    # the placeholder cannot leave this test passing against stale text.
    assert _REDACTED_FIELD in str(caught.value)


def test_an_ordinary_extra_field_name_is_also_replaced() -> None:
    """An unknown key is untrusted whether or not it looks alarming.

    This assertion is **inverted** from its original form, which required
    ``maximum_contracts`` to appear in the message on the grounds that
    "redaction must not make every typo undiagnosable". That reasoning is what
    finding H-01 disproved: ``maximum_contracts`` is not a declared field, so it
    is caller-supplied text, and the old test was asserting the defect. A
    credential pasted into a key position is ordinary-looking too.

    The legitimate half of the original intent — diagnostics must stay useful —
    is kept, and covered by ``test_diagnostics_still_identify_the_field_and_reason``
    below: a *known* field with a bad value is still named in full.
    """
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(maximum_contracts=5)
    assert "maximum_contracts" not in str(caught.value)
    assert _REDACTED_FIELD in str(caught.value)


def test_diagnostics_still_identify_the_field_and_reason() -> None:
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(random_seed=MARKER)
    assert "random_seed" in str(caught.value)
    assert "int_parsing" in str(caught.value)
    assert caught.value.details[0]["type"] == "int_parsing"


def test_the_validation_error_is_not_chained() -> None:
    """Chaining would reprint the raw inputs under "the direct cause"."""
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(random_seed=MARKER)
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None or MARKER not in str(caught.value.__context__)


def test_a_formatted_traceback_does_not_leak_the_value() -> None:
    try:
        AppConfig.load(random_seed=MARKER)
    except ConfigurationError as exc:
        rendered = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    assert MARKER not in rendered


def test_malformed_yaml_reports_position_not_content(tmp_path: Path) -> None:
    """A parser message quotes the offending source line, which may be secret."""
    path = tmp_path / "conf.yaml"
    path.write_text(f"mode: [unclosed {MARKER}\n", encoding="utf-8")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    assert MARKER not in str(caught.value)
    assert "line" in str(caught.value)


def test_non_utf8_yaml_is_a_configuration_error(tmp_path: Path) -> None:
    """R-11: previously escaped as UnicodeDecodeError, outside the contract."""
    path = tmp_path / "conf.yaml"
    path.write_bytes("app_name: caf\xe9\n".encode("latin-1"))
    with pytest.raises(ConfigurationError, match="not valid UTF-8"):
        AppConfig.load(path)


def test_an_unreadable_file_is_a_configuration_error(tmp_path: Path) -> None:
    directory = tmp_path / "a_directory.yaml"
    directory.mkdir()
    with pytest.raises(ConfigurationError):
        AppConfig.load(directory)


# --------------------------------------------------------------------------
# Correction D (R-02): resolved paths are absolute and stable.
# --------------------------------------------------------------------------


def test_a_relative_base_still_yields_absolute_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = AppConfig.load(base_path=Path("relative-root"))
    assert config.resolved_data_root.is_absolute()
    assert config.resolved_report_root.is_absolute()
    assert config.resolved_data_root == tmp_path / "relative-root" / "data"


def test_an_omitted_base_anchors_to_the_construction_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    config = AppConfig.load()
    assert config.resolved_data_root == tmp_path / "data"


def test_an_absolute_base_is_left_absolute(tmp_path: Path) -> None:
    config = AppConfig.load(base_path=tmp_path)
    assert config.resolved_data_root == tmp_path / "data"


def test_resolved_paths_do_not_move_when_the_process_chdirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The defect: a configuration's meaning drifted while its identity did not."""
    start = tmp_path / "start"
    start.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(start)
    config = AppConfig.load(base_path=Path("rel"))
    before = config.resolved_data_root
    monkeypatch.chdir(elsewhere)
    assert config.resolved_data_root == before


def test_dot_segments_are_collapsed_lexically(tmp_path: Path) -> None:
    config = AppConfig.load(base_path=tmp_path / "a" / ".." / "b" / ".")
    assert config.resolved_data_root == tmp_path / "b" / "data"


def test_symlinks_are_not_resolved(tmp_path: Path) -> None:
    """Recording the link target rather than the configured path would surprise."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    config = AppConfig.load(base_path=link)
    assert config.resolved_data_root == link / "data"


def test_the_target_need_not_exist(tmp_path: Path) -> None:
    config = AppConfig.load(base_path=tmp_path / "not" / "created" / "yet")
    assert config.resolved_data_root.is_absolute()


def test_a_dumped_configuration_reloads_to_the_same_paths(tmp_path: Path) -> None:
    original = AppConfig.load(base_path=tmp_path / "root")
    reloaded = AppConfig(**original.model_dump(mode="json"))
    assert reloaded.effective_base_path == original.effective_base_path
    assert reloaded.resolved_data_root == original.resolved_data_root


def test_the_fingerprint_tracks_the_effective_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two different directories must not share one recorded identity."""
    first = tmp_path / "one"
    first.mkdir()
    second = tmp_path / "two"
    second.mkdir()
    monkeypatch.chdir(first)
    one = AppConfig.load(base_path=Path("rel"))
    monkeypatch.chdir(second)
    two = AppConfig.load(base_path=Path("rel"))
    assert one.resolved_data_root != two.resolved_data_root
    assert one.fingerprint() != two.fingerprint()


def test_the_fingerprint_is_stable_when_only_cwd_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = AppConfig.load(base_path=tmp_path)
    before = config.fingerprint()
    monkeypatch.chdir(tmp_path)
    assert config.fingerprint() == before


def test_an_os_error_while_reading_is_a_configuration_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A read that fails for any OS reason is still a malformed configuration."""
    path = tmp_path / "conf.yaml"
    path.write_text("mode: RESEARCH\n", encoding="utf-8")

    def _fail(*_args: object, **_kwargs: object) -> str:
        message = "simulated read failure"
        raise OSError(5, message)

    monkeypatch.setattr(Path, "read_text", _fail)
    with pytest.raises(ConfigurationError, match="could not be read"):
        AppConfig.load(path)


def test_non_mapping_input_passes_through_the_base_validator() -> None:
    """The validator must not assume it is always handed a dict."""
    with pytest.raises(ValidationError):
        AppConfig.model_validate("not a mapping")
