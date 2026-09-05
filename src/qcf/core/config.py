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
    A misspelled key is a configuration error on **every** input channel, not a
    silently ignored line -- the failure mode where a limit was set and never
    read is exactly what this prevents. ``extra="forbid"`` covers keyword
    arguments and the YAML file; :func:`check_environment` covers the ``QCF_``
    environment namespace, which ``extra="forbid"`` never sees because
    pydantic-settings discards unmatched names before the model is built. A
    YAML file may not repeat a key at any depth either, for the same reason.

Precedence, highest first: explicit keyword arguments, then ``QCF_``-prefixed
environment variables, then the YAML file. Dotenv files and secret directories
are deliberately *not* consulted: QCF configuration carries no secrets, so
reading credential sources would only create somewhere for one to hide.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from pathlib import Path
from typing import Annotated, Any, Final, Literal, NoReturn

import yaml
from pydantic import BeforeValidator, ValidationError, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from qcf.core.enums import OperatingMode
from qcf.core.exceptions import ConfigurationError, InvariantViolationError
from qcf.core.fingerprint import fingerprint
from qcf.core.logging import redact
from qcf.core.unknown import UNKNOWN, UnknownType

__all__ = [
    "ALIAS_ATTRIBUTES",
    "ENV_PREFIX",
    "REASON_AMBIGUOUS_ENV_KEY",
    "REASON_DUPLICATE_YAML_KEY",
    "REASON_UNKNOWN_ENV_KEY",
    "REASON_UNSUPPORTED_YAML_KEY",
    "REASON_YAML_MERGE_KEY",
    "AppConfig",
    "PolicyVersion",
    "alias_violations",
    "assert_no_field_aliases",
    "check_environment",
    "safe_validation_details",
    "schema_field_names",
]

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


def _raise_detached(error: ConfigurationError) -> NoReturn:
    """Raise ``error`` with no reference to the exception being handled.

    ``raise ... from None`` sets ``__suppress_context__``, which stops the
    *default* traceback formatter printing the original -- but ``__context__``
    still holds it, so the rejected value stays reachable by introspection and
    by third-party formatters. Clearing both detaches it instead of hiding it.

    This is not memory erasure. Copies may survive elsewhere, and a formatter
    that dumps frame locals can still see the value in the frame that produced
    it. The guarantee is about the exception object, and no more.
    """
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error


def _normalise(path: Path) -> Path:
    """Collapse dot segments lexically, without touching the filesystem.

    Deliberately not :meth:`Path.resolve`: resolving would follow symlinks, so
    the recorded path would describe the link's target rather than the location
    the operator configured, and it would differ between machines that lay out
    links differently. Normalisation here is purely textual, needs no directory
    to exist, and leaves symlinks intact.
    """
    return Path(os.path.normpath(path))


#: Replacement for a location segment that is not a known schema field name.
#:
#: Constant by design. A placeholder derived from the input -- a length, a first
#: character, a hash -- would leak a little of the thing it exists to hide.
_REDACTED_FIELD: Final = "<unknown-field>"


#: The alias-bearing metadata this project inspects, verified against the locked
#: pydantic rather than assumed.
#:
#: All four matter. Setting ``alias`` populates ``validation_alias`` and
#: ``serialization_alias`` too; ``AliasChoices`` and ``AliasPath`` appear only
#: under ``validation_alias``; and a ``model_config`` ``alias_generator``
#: populates all three at ``alias_priority`` 1. Checking one attribute would
#: therefore miss most of the ways an alias can arrive.
ALIAS_ATTRIBUTES: Final = ("alias", "validation_alias", "serialization_alias", "alias_priority")


def alias_violations(model: type[BaseSettings]) -> tuple[str, ...]:
    """Return a description of every alias declared on ``model``, if any.

    Stage 00 **prohibits aliases** on configuration models. See
    :func:`assert_no_field_aliases` for why.

    Returns:
        One ``"field.attribute"`` string per violation, empty when the model
        obeys the contract. Field and attribute names are code-owned, so they
        are safe to place in an error message -- unlike the caller-supplied text
        that :func:`_safe_loc` handles.
    """
    found: list[str] = []
    if model.model_config.get("alias_generator") is not None:
        found.append("model_config.alias_generator")
    for field_name, field in model.model_fields.items():
        found.extend(
            f"{field_name}.{attribute}"
            for attribute in ALIAS_ATTRIBUTES
            if getattr(field, attribute, None) is not None
        )
    return tuple(found)


def assert_no_field_aliases(model: type[BaseSettings]) -> None:
    """Enforce the Stage 00 no-alias contract on ``model``.

    QCF derives environment variable names as the ``QCF_`` prefix plus the
    canonical field name, and nothing else. An alias breaks that in a way that
    fails *open*: pydantic-settings reads a field carrying a ``validation_alias``
    from the **unprefixed** alias, so ``QCF_<ALIAS>`` and ``QCF_<FIELD>`` are
    both silently ignored while looking exactly like valid settings. That is
    finding R-12 -- a setting configured and never read -- returning by a side
    door, and finding DR-02 recorded that the environment guard had been
    described as alias-aware when it was not.

    Rather than implement alias support that nothing needs, Stage 00 forbids
    aliases and enforces the prohibition here, at class-definition time, so the
    contract cannot quietly lapse when a future field is added.

    Raises:
        InvariantViolationError: If any alias form is declared. This is a defect
            in QCF's own schema, not bad input, which is why it is an invariant
            violation rather than a :class:`ConfigurationError`.
    """
    violations = alias_violations(model)
    if violations:
        raise InvariantViolationError(
            f"{model.__name__} declares field aliases, which Stage 00 configuration "
            f"forbids: {', '.join(violations)}. Environment names are derived from "
            f"the QCF_ prefix plus the canonical field name only. See ADR-0010 for "
            f"what must be designed before alias support can be introduced."
        )


def schema_field_names(model: type[BaseSettings]) -> frozenset[str]:
    """Return every name this model will accept in an error location.

    This is the **allowlist** that decides whether a location segment may be
    printed. It is derived from the validated schema, so a field added to the
    model is covered automatically and cannot drift out of sync -- there is no
    second hand-maintained copy to forget.

    Canonical field names only. Aliases are prohibited by
    :func:`assert_no_field_aliases`, so no other spelling can reach an error
    location; collecting alias forms here would be unreachable code that implies
    a support this project does not offer.
    """
    return frozenset(model.model_fields)


def _safe_loc(loc: Sequence[object], allowed: frozenset[str]) -> tuple[str | int, ...]:
    """Return a location tuple safe to put in a message, a log, or a traceback.

    Every segment is checked, at every depth, for every error type. The previous
    version checked only ``extra_forbidden`` locations and decided by *shape* --
    sensitive-sounding word, over-long, not an identifier. That reasoning was
    backwards: an unknown key is untrusted precisely because we do not know what
    it is, and a credential pasted into a key position is normally identifier-
    shaped and short, so it passed every test (finding H-01).

    The rule now is positive rather than suspicious: a segment is printed only if
    it is a name *we* declared. Anything else is replaced, whatever it looks
    like. Integer segments are sequence indices generated by pydantic, not input
    text, so they are preserved -- they help locate the error and can carry
    nothing.
    """

    def printable(part: object) -> bool:
        # bool is a subclass of int; a boolean is not a sequence index.
        is_index = isinstance(part, int) and not isinstance(part, bool)
        is_declared_name = isinstance(part, str) and part in allowed
        return is_index or is_declared_name

    return tuple(part if printable(part) else _REDACTED_FIELD for part in loc)  # type: ignore[misc]


#: Code-owned replacements for pydantic's own error text.
#:
#: pydantic's ``msg`` is not copied. Most of its messages are schema-derived and
#: harmless, but ``value_error`` carries whatever a validator put in a
#: ``ValueError`` -- which may be the value itself -- and the boundary should not
#: depend on knowing which types are safe this release.
_MESSAGE_FOR_TYPE: Final[Mapping[str, str]] = {
    "extra_forbidden": "unknown configuration key",
    "missing": "required value is absent",
    "int_parsing": "value is not a valid integer",
    "int_type": "value is not an integer",
    "string_type": "value is not a string",
    "bool_parsing": "value is not a valid boolean",
    "float_parsing": "value is not a valid number",
    "literal_error": "value is not one of the permitted literals",
    "enum": "value is not a member of the permitted set",
    "path_type": "value is not a valid path",
    "frozen_instance": "configuration is frozen and cannot be mutated",
}
_GENERIC_MESSAGE: Final = "value failed validation"


def safe_validation_details(
    exc: ValidationError, *, model: type[BaseSettings] | None = None
) -> tuple[dict[str, object], ...]:
    """Convert a pydantic error into details that carry no input text at all.

    Three separate channels had to be closed:

    ``input``
        ``include_input=False`` drops the rejected value.
    ``ctx`` and ``url``
        ``include_context=False`` and ``include_url=False`` drop constraint
        context and documentation links, both of which can embed the value.
    ``loc`` and ``msg``
        Neither is touched by those flags. ``loc`` goes through
        :func:`_safe_loc`; ``msg`` is discarded and replaced with our own text
        keyed on the error *type*, which is a pydantic constant rather than
        anything derived from input.

    Args:
        exc: The validation error to sanitise.
        model: Schema whose field names may be named in the output. Defaults to
            :class:`AppConfig`.

    Returns:
        Entries carrying a pydantic error ``type``, a sanitised ``loc``, and a
        code-owned ``msg``. Verified by tests that assert an inert marker is
        absent from every representation, rather than assumed from the flags.
    """
    allowed = schema_field_names(AppConfig if model is None else model)
    details: list[dict[str, object]] = []
    for error in exc.errors(include_input=False, include_url=False, include_context=False):
        error_type = str(error.get("type", "unknown"))
        details.append(
            {
                "type": error_type,
                "loc": _safe_loc(error.get("loc", ()), allowed),
                "msg": _MESSAGE_FOR_TYPE.get(error_type, _GENERIC_MESSAGE),
            }
        )
    return tuple(details)


def _format_details(details: Sequence[Mapping[str, object]]) -> str:
    """Render sanitised details as a short human-readable block."""
    lines = []
    for detail in details:
        raw_loc = detail.get("loc", ())
        parts = raw_loc if isinstance(raw_loc, (tuple, list)) else ()
        loc = ".".join(str(part) for part in parts) or "<root>"
        lines.append(f"  {loc}: {detail.get('msg', '')} [{detail.get('type', '')}]")
    return "\n".join(lines)


#: Stable reason codes. Chosen from this fixed set, never derived from input.
REASON_UNKNOWN_ENV_KEY: Final = "QCF_CONFIG_UNKNOWN_ENV_KEY"
REASON_AMBIGUOUS_ENV_KEY: Final = "QCF_CONFIG_AMBIGUOUS_ENV_KEY"
REASON_DUPLICATE_YAML_KEY: Final = "QCF_CONFIG_DUPLICATE_YAML_KEY"
REASON_UNSUPPORTED_YAML_KEY: Final = "QCF_CONFIG_UNSUPPORTED_YAML_KEY"
REASON_YAML_MERGE_KEY: Final = "QCF_CONFIG_YAML_MERGE_KEY"
REASON_INVALID_VALUES: Final = "QCF_CONFIG_INVALID_VALUES"

#: YAML's merge key. Deliberately rejected -- see :class:`_UniqueKeySafeLoader`.
_MERGE_KEY: Final = "tag:yaml.org,2002:merge"


class _DuplicateYamlKeyError(Exception):
    """Internal signal from the loader. Never escapes this module.

    Carries only a line and column. The key itself is *not* carried: it is file
    content, and this object crosses into an error path that formats text.
    """

    def __init__(self, reason: str, line: int, column: int) -> None:
        super().__init__(reason)
        self.reason = reason
        self.line = line
        self.column = column


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """A ``SafeLoader`` that refuses duplicate, merged and non-string keys.

    Subclassed rather than patched: ``yaml.SafeLoader`` is global, and altering
    it would silently change how every other module in the process — including
    dependencies — parses YAML. This class governs QCF's configuration files and
    nothing else.

    Three rejections, all for the same reason: each one lets a file say two
    contradictory things and quietly resolve the contradiction on the reader's
    behalf.

    Duplicate keys
        PyYAML's default is last-wins. First-wins would be no better. A file
        setting ``mode`` twice does not have an obvious intended meaning, and
        guessing one is how a setting that was configured ends up never read.

    Merge keys (``<<``)
        A merge silently supplies values from elsewhere in the document, so the
        effective configuration is not what the reader sees at the key. Rejected
        as unsupported rather than half-supported.

    Non-string keys
        ``1: x`` and ``true: x`` are legal YAML. No QCF field is named by a
        number or a boolean, so such a key can only be a mistake. Rejecting is
        honest; coercing to ``"1"`` invents an intent.

    Safe-load semantics are preserved throughout: no arbitrary object
    construction is enabled by any of this.
    """

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        """Build a mapping, rejecting anything ambiguous at *this* depth.

        PyYAML calls this for every mapping in the document, so nested mappings
        are checked by the same code that checks the top level rather than by a
        separate recursive walk that could drift out of step.
        """
        seen: set[str] = set()
        for key_node, _ in node.value:
            mark = key_node.start_mark
            if key_node.tag == _MERGE_KEY:
                raise _DuplicateYamlKeyError(REASON_YAML_MERGE_KEY, mark.line + 1, mark.column + 1)
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise _DuplicateYamlKeyError(
                    REASON_UNSUPPORTED_YAML_KEY, mark.line + 1, mark.column + 1
                )
            if key in seen:
                raise _DuplicateYamlKeyError(
                    REASON_DUPLICATE_YAML_KEY, mark.line + 1, mark.column + 1
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    """Read a YAML file that must contain a mapping at the top level."""
    if not path.is_file():
        raise ConfigurationError(
            f"configuration file {path} does not exist. A named configuration file "
            f"that is missing is an error, not an empty configuration."
        )
    # Each failure below builds its error and raises it *outside* the handler.
    # Raising inside would set __context__ to the original exception, whose
    # str() carries file content -- `from None` only suppresses that from the
    # default traceback, it does not detach the object. See _raise_detached.
    read_failure: str | None = None
    text = ""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        read_failure = f"configuration file {path} is not valid UTF-8 (byte offset {exc.start})."
    except OSError as exc:
        read_failure = f"configuration file {path} could not be read: {exc.strerror}"
    if read_failure is not None:
        _raise_detached(ConfigurationError(read_failure))

    parse_failure: str | None = None
    parse_reason: str | None = None
    loaded: object = None
    try:
        loaded = yaml.load(text, Loader=_UniqueKeySafeLoader)  # noqa: S506 - unique-key SafeLoader
    except _DuplicateYamlKeyError as exc:
        # Position only. The key is deliberately not quoted: an unknown key is
        # untrusted input and may itself be a credential -- the same reasoning
        # as H-01, applied to the file channel.
        parse_reason = exc.reason
        parse_failure = (
            f"configuration file {path} was rejected at line {exc.line}, column {exc.column} "
            f"[{exc.reason}]. The key is withheld because it is untrusted input."
        )
    except yaml.YAMLError as exc:
        # Only the position is reported. A YAML parser's message quotes the
        # offending source line, which is file content and may be a secret.
        mark = getattr(exc, "problem_mark", None)
        where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        parse_failure = (
            f"configuration file {path} is not valid YAML{where}. "
            f"The parser message is withheld because it quotes file content."
        )
    if parse_failure is not None:
        _raise_detached(ConfigurationError(parse_failure, reason=parse_reason))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigurationError(
            f"configuration file {path} must contain a mapping at the top level, "
            f"got {type(loaded).__name__}."
        )
    return loaded


def check_environment(
    environ: Mapping[str, str], model: type[BaseSettings]
) -> ConfigurationError | None:
    """Return an error if the ``QCF_`` environment namespace holds a bad name.

    ``extra="forbid"`` does not reach here. pydantic-settings collects only
    prefixed names that *match a declared field* and discards the rest before
    the model ever sees them, so a misspelled ``QCF_MOED`` was silently dropped
    while the identical typo through YAML or a keyword argument was a hard error
    (finding R-12). Two documented guarantees were false for this one channel.

    Case handling follows the model rather than guessing: with
    ``case_sensitive=False`` -- QCF's setting -- pydantic-settings matches
    ``QCF_MODE``, ``qcf_mode`` and ``Qcf_Mode`` alike, so this check folds case
    the same way. Under ``case_sensitive=True`` it compares exactly. Two
    spellings that differ only by case can coexist in one environment on POSIX
    while folding to one name; that is reported rather than resolved, because
    picking one silently is the behaviour this function exists to remove.

    Names without the prefix are ignored entirely: the environment belongs to
    the whole machine, and QCF has no business policing the rest of it.

    Returns:
        ``None`` when the namespace is clean, otherwise a ready-to-raise
        :class:`ConfigurationError`. It is returned rather than raised so the
        caller can raise it detached from any exception being handled.
    """
    config = model.model_config
    prefix = str(config.get("env_prefix", ""))
    case_sensitive = bool(config.get("case_sensitive", False))
    declared = schema_field_names(model)

    unknown = 0
    ambiguous: set[str] = set()
    seen_spellings: dict[str, set[str]] = {}
    for raw in environ:
        # Namespace membership is always decided case-insensitively, even for a
        # case-sensitive model. Otherwise `qcf_mode` under a strict model would
        # be filed as somebody else's variable and dropped in silence -- which is
        # R-12 again, one layer down. It is ours; it is simply spelled wrong.
        if not raw.lower().startswith(prefix.lower()):
            continue
        suffix = raw[len(prefix) :]
        if case_sensitive:
            # The library requires the prefix and the name exactly as declared.
            recognised = raw.startswith(prefix) and suffix in declared
            identity = suffix
        else:
            identity = suffix.lower()
            recognised = identity in {name.lower() for name in declared}
        if not recognised:
            # Covers misspellings, wrong casing under a case-sensitive model,
            # and -- because no nested delimiter is configured -- delimited
            # names such as QCF_A__B.
            unknown += 1
            continue
        seen_spellings.setdefault(identity, set()).add(raw)
    if not case_sensitive:
        ambiguous = {name for name, spellings in seen_spellings.items() if len(spellings) > 1}

    if not unknown and not ambiguous:
        return None

    problems: list[str] = []
    if unknown:
        plural = "" if unknown == 1 else "s"
        problems.append(
            f"{unknown} unrecognised {prefix}* environment variable{plural} "
            f"[{REASON_UNKNOWN_ENV_KEY}]"
        )
    if ambiguous:
        problems.append(
            f"{len(ambiguous)} recognised setting(s) supplied under more than one casing "
            f"[{REASON_AMBIGUOUS_ENV_KEY}]"
        )
    return ConfigurationError(
        "invalid QCF environment configuration: "
        + "; ".join(problems)
        + ". Names are withheld because an environment variable name is untrusted "
        "input and may itself carry a secret. Compare the environment against the "
        "documented settings.",
        reason=REASON_AMBIGUOUS_ENV_KEY if ambiguous else REASON_UNKNOWN_ENV_KEY,
    )


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
        base_path: Root that relative paths resolve against, exactly as the
            operator wrote it. May be relative; it is anchored at construction.
        effective_base_path: The absolute base actually in force, derived once
            when the configuration is validated. It is part of the model, so it
            appears in the dump and in the fingerprint: a configuration's
            identity includes the path context it denotes. That makes
            fingerprints machine-specific whenever paths differ between
            machines, which is intended -- see ADR-0009.
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
    effective_base_path: Path = Path()
    data_root: Path = Path("data")
    report_root: Path = Path("reports")
    timezone: Literal["UTC"] = "UTC"
    random_seed: int = 0
    policy_version: PolicyVersion = UNKNOWN

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401 - passthrough
        """Enforce the no-alias contract on every subclass, as it is defined.

        Checked here rather than at validation time so that an aliased field is
        a class-definition error -- it cannot reach a running system, and it
        cannot pass unnoticed because no test happened to construct that model.

        ``__pydantic_init_subclass__`` rather than ``__init_subclass__``: the
        latter runs *before* the metaclass has collected ``model_fields``, so a
        newly declared aliased field is not yet visible and the check silently
        passes. Verified against the locked pydantic, not assumed -- the first
        implementation used ``__init_subclass__`` and caught only
        ``alias_generator``, which lives in ``model_config`` and is available
        earlier.
        """
        super().__pydantic_init_subclass__(**kwargs)
        assert_no_field_aliases(cls)

    @model_validator(mode="before")
    @classmethod
    def _derive_effective_base(cls, data: Any) -> Any:  # noqa: ANN401 - pydantic hook
        """Anchor the base path once, at construction time.

        The working directory is read here and nowhere else. Resolving lazily in
        the properties meant a configuration's meaning changed when the process
        chdir'd, while its fingerprint stayed the same -- two different
        directories behind one identity.

        An explicitly supplied ``effective_base_path`` is honoured, so a dumped
        configuration reloads to the same paths on the same machine rather than
        re-anchoring to wherever the reload happens to run.
        """
        # Checked here so that it applies to direct construction as well as to
        # AppConfig.load(). A check that only load() performed would be one
        # `AppConfig()` call away from being bypassed.
        environment_error = check_environment(os.environ, cls)
        if environment_error is not None:
            _raise_detached(environment_error)
        if not isinstance(data, dict):
            return data
        if data.get("effective_base_path"):
            return data
        anchor = Path.cwd()
        base = data.get("base_path")
        effective = anchor if base is None else Path(base)
        if not effective.is_absolute():
            effective = anchor / effective
        merged = dict(data)
        merged["effective_base_path"] = _normalise(effective)
        return merged

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
        failure: ConfigurationError
        try:
            return cls(**overrides)
        except ValidationError as exc:
            source = f" from {yaml_path}" if yaml_path is not None else ""
            details = safe_validation_details(exc, model=cls)
            failure = ConfigurationError(
                f"invalid QCF configuration{source}:\n{_format_details(details)}",
                details=details,
                reason=REASON_INVALID_VALUES,
            )
        finally:
            _yaml_path_var.reset(token)
        # Raised outside the handler so the ValidationError -- which carries
        # every rejected input value in its str() -- is not attached as context.
        _raise_detached(failure)

    def _resolve(self, path: Path) -> Path:
        """Resolve one configured path against the effective base.

        Always absolute, because :attr:`effective_base_path` is absolute by
        construction. Never consults the working directory, so the result does
        not change if the process chdir's later.
        """
        if path.is_absolute():
            return _normalise(path)
        return _normalise(self.effective_base_path / path)

    @property
    def resolved_data_root(self) -> Path:
        """Data root as an absolute path.

        Absolute in every case: a relative :attr:`base_path` was anchored to the
        working directory at construction, and an omitted one defaults to it.
        The value does not change if the process chdir's afterwards.
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


# AppConfig itself is not covered by __init_subclass__, which only runs for
# subclasses. Checking here means the contract is verified at import time: a
# module that cannot satisfy it does not load.
assert_no_field_aliases(AppConfig)
