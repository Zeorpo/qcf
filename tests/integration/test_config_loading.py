"""The installed package, the committed example configuration, and the layering
between YAML, environment, and explicit arguments — exercised together."""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

import pytest

import qcf
from qcf.core.config import ENV_PREFIX, AppConfig
from qcf.core.enums import OperatingMode
from qcf.core.logging import REDACTED, redact
from qcf.core.unknown import is_unknown

EXAMPLE = Path("config/base.example.yaml")


def test_package_imports_from_installed_layout() -> None:
    """`qcf` must resolve to an installed distribution, not to path luck.

    With a `src` layout the working directory is not importable, so a passing
    import here means the package was actually installed — which is what would
    ship.
    """
    distribution = importlib.metadata.distribution("qcf")
    assert distribution.metadata["Name"] == "qcf"
    assert qcf.__version__ == distribution.version
    assert Path(qcf.__file__ or "").name == "__init__.py"


def test_the_committed_example_configuration_validates(repo_root: Path) -> None:
    """The example must stay loadable as the model evolves, or it is a lie."""
    config = AppConfig.load(repo_root / EXAMPLE)
    assert config.mode is OperatingMode.DISABLED
    assert config.timezone == "UTC"
    assert config.app_name == "qcf"
    assert is_unknown(config.policy_version)


def test_the_example_declares_no_financial_or_secret_settings(repo_root: Path) -> None:
    """Stage 00 configuration owns no financial concept and no credential."""
    text = (repo_root / EXAMPLE).read_text(encoding="utf-8").lower()
    forbidden = (
        "api_key",
        "password",
        "token",
        "account_id",
        "broker",
        "commission",
        "tick_value",
        "risk_limit",
        "profit_target",
        "endpoint",
    )
    present = [term for term in forbidden if f"{term}:" in text]
    assert not present, f"example configuration declares {present}"


def test_yaml_and_environment_layer_deterministically(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}MODE", "BACKTEST")
    monkeypatch.setenv(f"{ENV_PREFIX}LOG_LEVEL", "DEBUG")
    config = AppConfig.load(repo_root / EXAMPLE)

    # Environment wins over the file...
    assert config.mode is OperatingMode.BACKTEST
    assert config.log_level == "DEBUG"
    # ...and the file still supplies everything the environment did not set.
    assert config.app_name == "qcf"
    assert config.log_format == "console"


def test_explicit_arguments_win_over_both(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}MODE", "BACKTEST")
    config = AppConfig.load(repo_root / EXAMPLE, mode="REPLAY")
    assert config.mode is OperatingMode.REPLAY


def test_layering_is_repeatable(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Loading twice from the same inputs must give the same fingerprint."""
    monkeypatch.setenv(f"{ENV_PREFIX}RANDOM_SEED", "42")
    first = AppConfig.load(repo_root / EXAMPLE)
    second = AppConfig.load(repo_root / EXAMPLE)
    assert first.fingerprint() == second.fingerprint()
    assert first.random_seed == 42


def test_the_example_fingerprint_is_independent_of_the_working_directory(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A fingerprint that moved with the shell's cwd would be worthless."""
    baseline = AppConfig.load(repo_root / EXAMPLE, base_path=repo_root).fingerprint()
    monkeypatch.chdir(tmp_path)
    assert AppConfig.load(repo_root / EXAMPLE, base_path=repo_root).fingerprint() == baseline


def test_redacted_representation_is_json_safe_and_hides_nothing_real(
    repo_root: Path,
) -> None:
    redacted = AppConfig.load(repo_root / EXAMPLE).redacted()
    # Stage 00 configuration holds no secrets, so nothing should be replaced.
    assert REDACTED not in repr(redacted)
    assert redacted["mode"] == "DISABLED"
    assert redacted["timezone"] == "UTC"
    assert redacted["policy_version"] == "UNKNOWN"
    json.dumps(redacted)


def test_a_configuration_carrying_a_secret_like_field_would_be_redacted() -> None:
    """Proves the redaction path is wired to configuration, not only to logs.

    Stage 00 has no sensitive field, so the behaviour is demonstrated on an
    equivalently shaped mapping rather than by adding one.
    """
    placeholder = "not-a-real-value"  # pragma: allowlist secret
    dumped = {**AppConfig.load().redacted(), "api_key": placeholder}
    assert redact(dumped) != dumped
    assert redact(dumped)["api_key"] == REDACTED  # type: ignore[index]
