"""Typed, immutable application configuration.

Stage 00 configures the *application*, not the trading system. There are no
fees, prices, balances, account limits, risk limits, endpoints, credentials, or
strategy parameters here, and there will not be until the stages that own those
concepts define them with the versioning and provenance they require.

Three properties are load-bearing:

Immutability
    The model is frozen. A run's configuration cannot drift while the run is in
    progress, which is what makes the recorded configuration fingerprint a true
    description of what produced a result.

Explicit unknowns
    A value that has not been established stays :data:`~qcf.core.unknown.UNKNOWN`
    rather than defaulting. See :mod:`qcf.core.unknown`.

Refusal of unknown keys
    ``extra="forbid"``. A misspelled key is a configuration error, not a
    silently ignored line -- the failure mode where a limit was set in a file
    and never read is exactly what this prevents.

Precedence, highest first: explicit keyword arguments, then ``QCF_``-prefixed
environment variables, then the YAML file. Dotenv files and secret directories
are deliberately *not* consulted: QCF configuration carries no secrets, so
reading credential sources would only create somewhere for one to hide.
"""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
from typing import Annotated, Any, Final, Literal

import yaml
from pydantic import BeforeValidator, ValidationError
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from qcf.core.enums import OperatingMode
from qcf.core.exceptions import ConfigurationError
from qcf.core.fingerprint import fingerprint
from qcf.core.logging import redact
from qcf.core.unknown import UNKNOWN, UnknownType

__all__ = ["ENV_PREFIX", "AppConfig", "PolicyVersion"]

#: Prefix for environment overrides, for example ``QCF_MODE=RESEARCH``.
ENV_PREFIX: Final = "QCF_"

_yaml_path_var: ContextVar[Path | None] = ContextVar("_qcf_yaml_path", default=None)


def _coerce_unknown(value: object) -> object:
    """Map the literal string ``"UNKNOWN"`` onto the UNKNOWN sentinel."""
    if isinstance(value, str) and value.strip().upper() == "UNKNOWN":
        return UNKNOWN
    return value


#: A policy version label, or UNKNOWN when none has been established.
PolicyVersion = Annotated[UnknownType | str, BeforeValidator(_coerce_unknown)]


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    """Read a YAML file that must contain a mapping at the top level."""
    if not path.is_file():
        raise ConfigurationError(
            f"configuration file {path} does not exist. A named configuration file "
            f"that is missing is an error, not an empty configuration."
        )
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"configuration file {path} is not valid YAML: {exc}") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigurationError(
            f"configuration file {path} must contain a mapping at the top level, "
            f"got {type(loaded).__name__}."
        )
    return loaded


class _YamlSettingsSource(PydanticBaseSettingsSource):
    """Settings source reading one YAML file, resolved when the source is built.

    Written rather than reused so that a *named* file which does not exist is an
    error. A source that silently treats a missing file as an empty mapping
    turns a mistyped path into defaults that look deliberate.
    """

    def __init__(self, settings_cls: type[BaseSettings], path: Path | None) -> None:
        super().__init__(settings_cls)
        self._data: dict[str, Any] = {} if path is None else _read_yaml_mapping(path)

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """Return the raw value for one field, as required by the source protocol."""
        del field
        return self._data.get(field_name), field_name, False

    def __call__(self) -> dict[str, Any]:
        """Return every value this source supplies."""
        return dict(self._data)


class AppConfig(BaseSettings):
    """Immutable, validated application settings.

    Attributes:
        app_name: Identifier used in logs and run records.
        environment: Free-form label for the machine or context, such as
            ``"local"`` or ``"ci"``. It carries no behaviour.
        mode: Operating mode. Defaults to :attr:`~qcf.core.enums.OperatingMode.DISABLED`.
        log_level: Minimum log level name.
        log_format: ``"console"`` for humans, ``"json"`` for machines.
        base_path: Root that relative paths resolve against. When set, path
            resolution does not depend on the working directory.
        data_root: Data directory, absolute or relative to ``base_path``.
        report_root: Report directory, absolute or relative to ``base_path``.
        timezone: Fixed to ``"UTC"``. QCF holds every internal timestamp in UTC;
            this field exists so that the constraint is visible in the recorded
            configuration rather than implied by code.
        random_seed: Seed for deterministic runs.
        policy_version: Label of the external policy set in force, or UNKNOWN.
    """

    model_config = SettingsConfigDict(
        frozen=True,
        extra="forbid",
        env_prefix=ENV_PREFIX,
        case_sensitive=False,
        validate_default=True,
    )

    app_name: str = "qcf"
    environment: str = "local"
    mode: OperatingMode = OperatingMode.DISABLED
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["console", "json"] = "console"
    base_path: Path | None = None
    data_root: Path = Path("data")
    report_root: Path = Path("reports")
    timezone: Literal["UTC"] = "UTC"
    random_seed: int = 0
    policy_version: PolicyVersion = UNKNOWN

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Order the sources: explicit arguments, then environment, then YAML."""
        del dotenv_settings, file_secret_settings
        return (
            init_settings,
            env_settings,
            _YamlSettingsSource(settings_cls, _yaml_path_var.get()),
        )

    @classmethod
    def load(
        cls,
        yaml_path: Path | str | None = None,
        # ANN401: overrides genuinely are arbitrary until pydantic validates
        # them against the field types. Narrowing to `object` would only move
        # the imprecision to the call site as a cast.
        **overrides: Any,  # noqa: ANN401
    ) -> AppConfig:
        """Load configuration from YAML, environment, and explicit overrides.

        Args:
            yaml_path: Optional path to a YAML file. If given, the file must
                exist.
            **overrides: Values that take precedence over every other source.

        Returns:
            A frozen, validated configuration.

        Raises:
            ConfigurationError: If the file is missing or malformed, or if the
                merged values fail validation.
        """
        token = _yaml_path_var.set(Path(yaml_path) if yaml_path is not None else None)
        try:
            return cls(**overrides)
        except ValidationError as exc:
            source = f" from {yaml_path}" if yaml_path is not None else ""
            raise ConfigurationError(f"invalid QCF configuration{source}:\n{exc}") from exc
        finally:
            _yaml_path_var.reset(token)

    def _resolve(self, path: Path) -> Path:
        """Resolve one configured path against ``base_path`` when it is relative."""
        if path.is_absolute():
            return path
        if self.base_path is not None:
            return self.base_path / path
        return Path.cwd() / path

    @property
    def resolved_data_root(self) -> Path:
        """Data root as an absolute path.

        Relative values resolve against :attr:`base_path` when it is set, and
        only otherwise against the working directory. Configuring
        :attr:`base_path` therefore makes a run independent of where it was
        started from.
        """
        return self._resolve(self.data_root)

    @property
    def resolved_report_root(self) -> Path:
        """Report root as an absolute path, resolved like :attr:`resolved_data_root`."""
        return self._resolve(self.report_root)

    def canonical(self) -> dict[str, Any]:
        """Return the canonical mapping used for fingerprinting.

        Dumped in Python mode so that UNKNOWN stays distinguishable from the
        string ``"UNKNOWN"``.
        """
        return self.model_dump(mode="python")

    def fingerprint(self) -> str:
        """Return the SHA-256 fingerprint of this configuration.

        Insignificant presentation in the source YAML -- key order, quoting,
        indentation -- cannot change the result, because the fingerprint is
        taken over validated values rather than over file text.
        """
        return fingerprint(self.canonical())

    def redacted(self) -> dict[str, Any]:
        """Return a JSON-safe mapping with any sensitive value replaced.

        Stage 00 configuration holds no secrets by construction. This method
        exists so that logging a configuration is safe by default even after
        later stages add fields.
        """
        dumped = redact(self.model_dump(mode="json"))
        assert isinstance(dumped, dict)  # noqa: S101 - redact preserves mapping kind
        return dumped
