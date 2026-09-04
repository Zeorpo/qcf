"""Configuration must be immutable, validated, and free of silent defaults."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from qcf.core.config import ENV_PREFIX, AppConfig, _YamlSettingsSource
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
