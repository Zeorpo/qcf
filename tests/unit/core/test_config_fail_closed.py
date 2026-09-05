"""Configuration fails closed, and says so without quoting the input.

Three findings share one root cause: somewhere a channel accepted, or repeated,
text that the operator supplied and QCF never validated.

H-01
    An unknown configuration key was echoed verbatim into the error message,
    ``repr``, structured details and the traceback whenever it happened to look
    like an ordinary identifier. The old guard decided by *shape* — sensitive
    word, over-long, not an identifier — and a credential pasted into a key
    position defeats all three.

R-12
    ``extra="forbid"`` never saw the ``QCF_`` environment namespace, because
    pydantic-settings discards unmatched names before the model is built. The
    identical typo was a hard error through YAML and a keyword argument, and
    silent through the environment.

R-13
    A YAML file could set the same key twice and PyYAML kept the last one, so a
    file that said two contradictory things loaded without complaint.

Every marker below is fabricated. None is a credential, none has ever been
valid anywhere, and none leaves a temporary directory or this process.
"""

from __future__ import annotations

import io
import logging
import traceback
from pathlib import Path

import pytest
import yaml
from pydantic import AliasChoices, AliasPath, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from qcf.core.config import (
    ENV_PREFIX,
    REASON_AMBIGUOUS_ENV_KEY,
    REASON_DUPLICATE_YAML_KEY,
    REASON_UNKNOWN_ENV_KEY,
    REASON_UNSUPPORTED_YAML_KEY,
    REASON_YAML_MERGE_KEY,
    AppConfig,
    alias_violations,
    assert_no_field_aliases,
    check_environment,
    safe_validation_details,
    schema_field_names,
)
from qcf.core.exceptions import ConfigurationError, InvariantViolationError
from qcf.core.logging import configure_logging, get_logger

# --------------------------------------------------------------------------
# Fabricated unknown keys. Each is identifier-shaped and free of any word the
# old heuristic looked for, which is exactly why it used to be echoed.
# --------------------------------------------------------------------------
ORDINARY_TYPO = "moed"
IDENTIFIER_SHAPED = "hunter2placeholder"
HIGH_ENTROPY = "wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY"  # pragma: allowlist secret
HEX_BLOB = "a3f9c21e88b74d05a1ff"  # pragma: allowlist secret
VERY_LONG = "z" * 200
WITH_SEPARATORS = "some-key.with:separators"
WITH_UNICODE = "clé_étrangère"
WITH_WHITESPACE = "key with spaces"

#: Keys usable through every channel, including ``**kwargs``.
IDENTIFIER_KEYS = [ORDINARY_TYPO, IDENTIFIER_SHAPED, HIGH_ENTROPY, HEX_BLOB, VERY_LONG]

#: Keys that only YAML can express.
EXOTIC_KEYS = [WITH_SEPARATORS, WITH_UNICODE, WITH_WHITESPACE]

ALL_KEYS = IDENTIFIER_KEYS + EXOTIC_KEYS


def _renderings(exc: ConfigurationError) -> dict[str, str]:
    """Every public rendering of an exception that the contract covers."""
    buffer = io.StringIO()
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=buffer)
    return {
        "str": str(exc),
        "f-string": f"{exc}",
        "repr": repr(exc),
        "args": repr(exc.args),
        "details": repr(exc.details),
        "reason": repr(exc.reason),
        "traceback": buffer.getvalue(),
        "cause": repr(exc.__cause__),
        "context": repr(exc.__context__),
        "attributes": repr(sorted(vars(exc).items())),
    }


def _assert_absent(exc: ConfigurationError, marker: str) -> None:
    """Fail naming the rendering that leaked, not merely that one did."""
    leaked = [name for name, text in _renderings(exc).items() if marker in text]
    assert not leaked, f"key echoed in {leaked}"


def _yaml_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "qcf.yaml"
    path.write_text(text, encoding="utf-8")
    return path


# ==========================================================================
# H-01 — an unknown key is never copied into output
# ==========================================================================


@pytest.mark.parametrize("key", IDENTIFIER_KEYS)
def test_an_unknown_keyword_argument_is_never_echoed(key: str) -> None:
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(**{key: 1})  # type: ignore[arg-type]
    _assert_absent(caught.value, key)


@pytest.mark.parametrize("key", ALL_KEYS)
def test_an_unknown_yaml_key_is_never_echoed(tmp_path: Path, key: str) -> None:
    path = _yaml_config(tmp_path, f'"{key}": 1\n')
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    _assert_absent(caught.value, key)


def test_the_placeholder_is_constant_and_reveals_no_shape() -> None:
    """Two unknown keys of very different shapes must be indistinguishable."""
    with pytest.raises(ConfigurationError) as short_key:
        AppConfig.load(ab=1)
    with pytest.raises(ConfigurationError) as long_key:
        AppConfig.load(**{VERY_LONG: 1})  # type: ignore[arg-type]
    assert str(short_key.value) == str(long_key.value)


def test_several_unknown_keys_at_once_are_all_replaced() -> None:
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(**{IDENTIFIER_SHAPED: 1, HEX_BLOB: 2, HIGH_ENTROPY: 3})  # type: ignore[arg-type]
    for key in (IDENTIFIER_SHAPED, HEX_BLOB, HIGH_ENTROPY):
        _assert_absent(caught.value, key)
    assert len(caught.value.details) == 3


def test_a_nested_unknown_key_is_replaced(tmp_path: Path) -> None:
    """A mapping value under a known field puts the key deeper in the location."""
    path = _yaml_config(tmp_path, f"data_root:\n  {IDENTIFIER_SHAPED}: 1\n")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    _assert_absent(caught.value, IDENTIFIER_SHAPED)


def test_a_known_field_is_still_named() -> None:
    """Redacting everything would make the diagnostic useless."""
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(random_seed="not-an-int")
    assert "random_seed" in str(caught.value)
    assert caught.value.details[0]["loc"] == ("random_seed",)


def test_an_invalid_value_for_a_known_field_is_not_echoed() -> None:
    marker = "INERT-VALUE-MARKER-Q7"
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(random_seed=marker)
    _assert_absent(caught.value, marker)
    assert caught.value.details[0]["type"] == "int_parsing"


def test_pydantic_error_text_is_not_copied_through() -> None:
    """``msg`` is ours. pydantic's own text may embed a validator's value."""
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(**{IDENTIFIER_SHAPED: 1})  # type: ignore[arg-type]
    assert caught.value.details[0]["msg"] == "unknown configuration key"
    assert "Extra inputs are not permitted" not in str(caught.value)


def test_no_third_party_error_object_is_retained() -> None:
    """A stored ValidationError would put every rejected value back in reach."""
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(**{IDENTIFIER_SHAPED: 1})  # type: ignore[arg-type]
    exc = caught.value
    assert exc.__cause__ is None
    assert exc.__context__ is None
    for value in vars(exc).values():
        assert not isinstance(value, Exception)


@pytest.mark.parametrize("key", IDENTIFIER_KEYS)
def test_the_supported_logger_does_not_emit_an_unknown_key(key: str) -> None:
    buffer = io.StringIO()
    configure_logging(fmt="json", stream=buffer)
    log = get_logger("test")
    try:
        AppConfig.load(**{key: 1})  # type: ignore[arg-type]
    except ConfigurationError:
        log.error("config_failed", exc_info=True)
    output = buffer.getvalue()
    assert key not in output
    assert "QCF_CONFIG_INVALID" in output


def test_the_stdlib_logger_does_not_emit_an_unknown_key() -> None:
    """The exception text itself must be safe; not every caller uses our logger."""
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    logger = logging.getLogger("qcf-test-plain")
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)
    try:
        try:
            AppConfig.load(**{HIGH_ENTROPY: 1})  # type: ignore[arg-type]
        except ConfigurationError:
            logger.exception("config failed")
    finally:
        logger.removeHandler(handler)
    assert HIGH_ENTROPY not in buffer.getvalue()


def test_schema_field_names_covers_every_declared_field() -> None:
    """The allowlist is derived, so a new field cannot be forgotten."""
    assert schema_field_names(AppConfig) >= set(AppConfig.model_fields)


def test_schema_field_names_admits_nothing_undeclared() -> None:
    assert IDENTIFIER_SHAPED not in schema_field_names(AppConfig)


# ==========================================================================
# DR-02 — aliases are prohibited, and the prohibition is enforced
#
# These assertions are INVERTED from their Stage 00-D form, which asserted that
# alias spellings were added to the allowlist. That was written to support an
# alias feature the project does not have, and finding DR-02 showed the support
# was illusory: pydantic-settings reads a field carrying a validation_alias from
# the *unprefixed* alias, so QCF_<ALIAS> and QCF_<FIELD> are both silently
# ignored — R-12's failure mode by a side door. Stage 00 now forbids aliases
# instead of half-supporting them.
# ==========================================================================


def test_the_real_schema_declares_no_alias_of_any_form() -> None:
    """The contract, asserted against the shipping model itself."""
    assert alias_violations(AppConfig) == ()
    assert_no_field_aliases(AppConfig)


def test_the_allowlist_is_exactly_the_canonical_field_names() -> None:
    assert schema_field_names(AppConfig) == set(AppConfig.model_fields)


@pytest.mark.parametrize(
    ("label", "aliased_field"),
    [
        ("alias", Field(default=0, alias="outside_name")),
        ("validation_alias", Field(default=0, validation_alias="outside_name")),
        ("serialization_alias", Field(default=0, serialization_alias="outside_name")),
        ("alias_choices", Field(default=0, validation_alias=AliasChoices("first", "second"))),
        ("alias_path", Field(default=0, validation_alias=AliasPath("outer", "inner"))),
    ],
)
def test_every_alias_form_fails_at_class_definition(label: str, aliased_field: object) -> None:
    """A temporary model, never the production one — the contract forbids that.

    The class is built with ``type()`` rather than a ``class`` statement so that
    the field definition can be parametrised; pydantic sees no difference.
    """
    with pytest.raises(InvariantViolationError, match="forbids"):
        type(
            f"Aliased_{label}",
            (AppConfig,),
            {"__annotations__": {"renamed": int}, "renamed": aliased_field},
        )


def test_an_alias_generator_also_fails() -> None:
    """It populates every alias attribute at priority 1, so it must be caught too."""
    with pytest.raises(InvariantViolationError, match="forbids"):

        class Generated(AppConfig):
            model_config = SettingsConfigDict(
                frozen=True,
                extra="forbid",
                env_prefix=ENV_PREFIX,
                case_sensitive=False,
                validate_default=True,
                alias_generator=str.upper,
            )


def test_a_subclass_without_aliases_is_still_permitted() -> None:
    """The guard must not make the model unextendable."""

    class Extended(AppConfig):
        extra_setting: int = 0

    assert Extended().extra_setting == 0
    assert "extra_setting" in schema_field_names(Extended)


def test_adding_an_alias_cannot_widen_the_environment_namespace() -> None:
    """An isolated fixture, outside the AppConfig hierarchy the guard protects.

    Even if a model somehow carried an alias, ``check_environment`` derives
    accepted names from canonical fields only, so the alias spelling never
    becomes an accepted ``QCF_`` name. The guard is the primary defence; this is
    the second one.
    """

    class Outside(BaseSettings):
        model_config = SettingsConfigDict(env_prefix=ENV_PREFIX, case_sensitive=False)
        # Every alias *shape*, not just one. An earlier version of this test used
        # AliasChoices alone, and a mutation that widened the allowlist with plain
        # string aliases slipped past it.
        by_choices: int = Field(default=0, validation_alias=AliasChoices("choice_name"))
        by_string: int = Field(default=0, alias="string_name")
        by_path: int = Field(default=0, validation_alias=AliasPath("path_outer", "inner"))

    assert schema_field_names(Outside) == {"by_choices", "by_string", "by_path"}
    for spelling in ("CHOICE_NAME", "STRING_NAME", "PATH_OUTER", "INNER"):
        assert check_environment({f"{ENV_PREFIX}{spelling}": "1"}, Outside) is not None
    assert alias_violations(Outside) != ()


def test_redaction_still_covers_alias_shaped_arbitrary_input() -> None:
    """H-01 must not have been weakened by narrowing the allowlist."""
    for key in ("outside_name", "first", "second", "outer", "inner"):
        with pytest.raises(ConfigurationError) as caught:
            AppConfig.load(**{key: 1})  # type: ignore[arg-type]
        _assert_absent(caught.value, key)


def test_a_sequence_index_is_preserved_but_its_neighbour_is_not() -> None:
    """Indices are pydantic's own integers; they locate the error and leak nothing."""

    class WithList(AppConfig):
        items: list[int] = Field(default_factory=list)

    with pytest.raises(ValidationError) as caught:
        WithList(items=["not-an-int"])  # type: ignore[list-item]
    details = safe_validation_details(caught.value, model=WithList)
    assert details[0]["loc"] == ("items", 0)


def test_an_unknown_key_beside_a_sequence_index_is_still_replaced() -> None:
    class WithList(AppConfig):
        items: list[int] = Field(default_factory=list)

    with pytest.raises(ValidationError) as caught:
        WithList(**{IDENTIFIER_SHAPED: 1})  # type: ignore[arg-type]
    details = safe_validation_details(caught.value, model=WithList)
    assert IDENTIFIER_SHAPED not in repr(details)


# ==========================================================================
# R-12 — the QCF_ environment namespace fails closed
# ==========================================================================


def test_a_clean_environment_loads() -> None:
    assert AppConfig.load().mode.value == "DISABLED"


def test_a_valid_environment_variable_still_applies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}MODE", "BACKTEST")
    assert AppConfig.load().mode.value == "BACKTEST"


@pytest.mark.parametrize("spelling", ["QCF_MODE", "qcf_mode", "Qcf_Mode", "QCF_mode"])
def test_every_casing_the_library_accepts_is_accepted_here(
    monkeypatch: pytest.MonkeyPatch, spelling: str
) -> None:
    """The check must not reject what pydantic-settings would have honoured."""
    monkeypatch.setenv(spelling, "REPLAY")
    assert AppConfig.load().mode.value == "REPLAY"


def test_the_reported_typo_is_now_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """R-12's exact reproduction: this used to load with mode=DISABLED."""
    monkeypatch.setenv(f"{ENV_PREFIX}MOED", "PAPER")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load()
    assert caught.value.reason == REASON_UNKNOWN_ENV_KEY


@pytest.mark.parametrize("suffix", ["MOED", "MODEE", "TOTALLY_MADE_UP", "MODE_"])
def test_unknown_prefixed_names_are_rejected(monkeypatch: pytest.MonkeyPatch, suffix: str) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}{suffix}", "1")
    with pytest.raises(ConfigurationError):
        AppConfig.load()


def test_a_delimited_nested_name_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """No nested delimiter is configured, so this is not a supported spelling."""
    monkeypatch.setenv(f"{ENV_PREFIX}MODE__NESTED", "1")
    with pytest.raises(ConfigurationError):
        AppConfig.load()


def test_multiple_unknown_names_are_counted_not_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for suffix in ("AAA", "BBB", "CCC"):
        monkeypatch.setenv(f"{ENV_PREFIX}{suffix}", "1")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load()
    message = str(caught.value)
    assert "3 unrecognised" in message
    for suffix in ("AAA", "BBB", "CCC"):
        assert suffix not in message


def test_an_unknown_environment_name_is_never_echoed(monkeypatch: pytest.MonkeyPatch) -> None:
    """H-01 applies to the environment channel too: the name is untrusted."""
    monkeypatch.setenv(f"{ENV_PREFIX}{HIGH_ENTROPY.upper()}", "1")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load()
    _assert_absent(caught.value, HIGH_ENTROPY.upper())
    _assert_absent(caught.value, HIGH_ENTROPY)


def test_a_mixture_of_valid_and_invalid_names_still_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}MODE", "RESEARCH")
    monkeypatch.setenv(f"{ENV_PREFIX}NONSENSE", "1")
    with pytest.raises(ConfigurationError):
        AppConfig.load()


def test_an_empty_value_under_a_valid_name_is_not_a_key_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty value is a value problem; the name itself is recognised."""
    monkeypatch.setenv(f"{ENV_PREFIX}MODE", "")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load()
    assert caught.value.reason != REASON_UNKNOWN_ENV_KEY


def test_an_empty_value_under_a_string_field_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(f"{ENV_PREFIX}ENVIRONMENT", "")
    assert AppConfig.load().environment == ""


def test_unprefixed_variables_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """The environment belongs to the machine, not to QCF."""
    monkeypatch.setenv("MODE", "PAPER")
    monkeypatch.setenv("PATH_TO_NOWHERE", "x")
    monkeypatch.setenv("NOTQCF_MODE", "x")
    assert AppConfig.load().mode.value == "DISABLED"


def test_conflicting_case_variants_are_reported_not_resolved() -> None:
    """Two spellings folding to one name have no determinate meaning."""
    error = check_environment({"QCF_MODE": "RESEARCH", "qcf_mode": "PAPER"}, AppConfig)
    assert error is not None
    assert error.reason == REASON_AMBIGUOUS_ENV_KEY


def test_one_casing_of_one_name_is_not_ambiguous() -> None:
    assert check_environment({"QCF_MODE": "RESEARCH"}, AppConfig) is None


def test_a_case_sensitive_model_compares_exactly() -> None:
    """The check follows the model's contract rather than assuming QCF's own.

    Under ``case_sensitive=True`` pydantic-settings matches only the exact
    spelling, so two casings are two different names — one recognised, one not —
    and there is nothing ambiguous about them.
    """

    class Strict(AppConfig):
        model_config = SettingsConfigDict(
            frozen=True,
            extra="forbid",
            env_prefix=ENV_PREFIX,
            case_sensitive=True,
            validate_default=True,
        )

    # Verified against the library rather than assumed: under case_sensitive=True
    # only `QCF_mode` is honoured, and `QCF_MODE` and `qcf_mode` are both ignored.
    assert check_environment({"QCF_mode": "RESEARCH"}, Strict) is None
    assert check_environment({"QCF_MODE": "RESEARCH"}, Strict) is not None
    assert check_environment({"qcf_mode": "RESEARCH"}, Strict) is not None

    # Under QCF's own case-insensitive model all three are honoured.
    for spelling in ("QCF_mode", "QCF_MODE", "qcf_mode"):
        assert check_environment({spelling: "RESEARCH"}, AppConfig) is None

    # Two casings are two distinct names when the model is case-sensitive, so
    # one is recognised and the other is simply unknown -- not ambiguous.
    both = check_environment({"QCF_mode": "A", "QCF_MODE": "B"}, Strict)
    assert both is not None
    assert both.reason == REASON_UNKNOWN_ENV_KEY


def test_the_check_accepts_every_declared_field_name() -> None:
    """Synchronisation guard: a field added to the model cannot drift out.

    If this fails, a new field is settable in YAML but rejected in the
    environment — the mirror image of R-12.
    """
    environ = {f"{ENV_PREFIX}{name.upper()}": "x" for name in AppConfig.model_fields}
    assert check_environment(environ, AppConfig) is None


def test_the_check_is_driven_by_the_model_not_a_hardcoded_list() -> None:
    """A different schema must produce a different verdict from the same input."""

    class Other(AppConfig):
        extra_setting: int = 0

    environ = {f"{ENV_PREFIX}EXTRA_SETTING": "1"}
    assert check_environment(environ, AppConfig) is not None
    assert check_environment(environ, Other) is None


def test_direct_construction_is_also_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    """A guard only ``load()`` applied would be one call away from bypassed."""
    monkeypatch.setenv(f"{ENV_PREFIX}NONSENSE", "1")
    with pytest.raises(ConfigurationError):
        AppConfig()


# ==========================================================================
# R-13 — a YAML file may not say two things
# ==========================================================================


def test_an_ordinary_file_still_loads(tmp_path: Path) -> None:
    path = _yaml_config(tmp_path, "mode: RESEARCH\nrandom_seed: 7\n")
    config = AppConfig.load(path)
    assert config.mode.value == "RESEARCH"
    assert config.random_seed == 7


def test_a_duplicate_top_level_key_is_rejected(tmp_path: Path) -> None:
    """R-13's exact reproduction: this used to load silently as PAPER."""
    path = _yaml_config(tmp_path, "mode: RESEARCH\nmode: PAPER\n")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    assert caught.value.reason == REASON_DUPLICATE_YAML_KEY


def test_a_duplicate_with_identical_values_is_also_rejected(tmp_path: Path) -> None:
    """Equal values today; a divergent edit tomorrow is the accident."""
    path = _yaml_config(tmp_path, "mode: RESEARCH\nmode: RESEARCH\n")
    with pytest.raises(ConfigurationError):
        AppConfig.load(path)


def test_a_nested_duplicate_is_rejected(tmp_path: Path) -> None:
    path = _yaml_config(tmp_path, "data_root:\n  inner: 1\n  inner: 2\n")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    assert caught.value.reason == REASON_DUPLICATE_YAML_KEY


def test_a_deeply_nested_duplicate_is_rejected(tmp_path: Path) -> None:
    path = _yaml_config(tmp_path, "a:\n  b:\n    c:\n      d: 1\n      d: 2\n")
    with pytest.raises(ConfigurationError):
        AppConfig.load(path)


def test_a_duplicate_inside_a_sequence_is_rejected(tmp_path: Path) -> None:
    path = _yaml_config(tmp_path, "items:\n  - k: 1\n    k: 2\n")
    with pytest.raises(ConfigurationError):
        AppConfig.load(path)


def test_a_unicode_duplicate_key_is_rejected(tmp_path: Path) -> None:
    path = _yaml_config(tmp_path, "clé: 1\nclé: 2\n")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    assert caught.value.reason == REASON_DUPLICATE_YAML_KEY


def test_the_duplicate_key_is_never_quoted(tmp_path: Path) -> None:
    """The key is untrusted input; H-01's reasoning applies to it too."""
    path = _yaml_config(tmp_path, f'"{HIGH_ENTROPY}": 1\n"{HIGH_ENTROPY}": 2\n')
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    _assert_absent(caught.value, HIGH_ENTROPY)


def test_the_offending_line_is_never_quoted(tmp_path: Path) -> None:
    marker = "INERT-LINE-MARKER-K2"
    path = _yaml_config(tmp_path, f"mode: {marker}\nmode: {marker}\n")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    _assert_absent(caught.value, marker)


def test_a_position_is_reported(tmp_path: Path) -> None:
    """Position is safe and is what makes the error actionable."""
    path = _yaml_config(tmp_path, "mode: RESEARCH\nmode: PAPER\n")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    assert "line 2" in str(caught.value)


def test_a_merge_key_is_rejected(tmp_path: Path) -> None:
    """Decided, not inherited: a merge hides where a value came from."""
    path = _yaml_config(
        tmp_path, "defaults: &d\n  mode: RESEARCH\nsettings:\n  <<: *d\n  random_seed: 1\n"
    )
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    assert caught.value.reason == REASON_YAML_MERGE_KEY


def test_a_plain_anchor_and_alias_still_works(tmp_path: Path) -> None:
    """Only merging is rejected; reusing a scalar is unambiguous."""
    path = _yaml_config(tmp_path, "environment: &e ci\napp_name: *e\n")
    config = AppConfig.load(path)
    assert config.environment == "ci"
    assert config.app_name == "ci"


@pytest.mark.parametrize("document", ["1: value\n", "true: value\n", "1.5: value\n"])
def test_a_non_string_key_is_rejected(tmp_path: Path, document: str) -> None:
    """No field is named by a number. Coercing to "1" would invent an intent."""
    path = _yaml_config(tmp_path, document)
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    assert caught.value.reason == REASON_UNSUPPORTED_YAML_KEY


def test_multiple_documents_are_rejected(tmp_path: Path) -> None:
    path = _yaml_config(tmp_path, "mode: RESEARCH\n---\nmode: PAPER\n")
    with pytest.raises(ConfigurationError):
        AppConfig.load(path)


def test_a_non_mapping_root_is_rejected(tmp_path: Path) -> None:
    path = _yaml_config(tmp_path, "- one\n- two\n")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    assert "mapping at the top level" in str(caught.value)


def test_malformed_yaml_is_still_rejected_without_quoting_content(tmp_path: Path) -> None:
    marker = "INERT-BROKEN-MARKER-M4"
    path = _yaml_config(tmp_path, f"mode: [unclosed\n{marker}: 1\n")
    with pytest.raises(ConfigurationError) as caught:
        AppConfig.load(path)
    _assert_absent(caught.value, marker)


def test_an_empty_file_is_an_empty_mapping(tmp_path: Path) -> None:
    path = _yaml_config(tmp_path, "")
    assert AppConfig.load(path).mode.value == "DISABLED"


def test_the_global_safe_loader_is_not_mutated(tmp_path: Path) -> None:
    """Patching PyYAML globally would change parsing for every dependency."""
    path = _yaml_config(tmp_path, "mode: RESEARCH\nmode: PAPER\n")
    with pytest.raises(ConfigurationError):
        AppConfig.load(path)
    assert yaml.safe_load("a: 1\na: 2\n") == {"a": 2}


def test_the_loader_does_not_construct_arbitrary_objects(tmp_path: Path) -> None:
    """Safe-load semantics must survive the subclass."""
    path = _yaml_config(tmp_path, "mode: !!python/object/apply:os.system ['true']\n")
    with pytest.raises(ConfigurationError):
        AppConfig.load(path)


# ==========================================================================
# The three channels now state one principle
# ==========================================================================


@pytest.mark.parametrize("channel", ["kwargs", "yaml", "env"])
def test_the_same_typo_fails_on_every_channel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, channel: str
) -> None:
    """The asymmetry R-12 described is gone: one typo, three refusals."""
    if channel == "kwargs":
        with pytest.raises(ConfigurationError):
            AppConfig.load(**{ORDINARY_TYPO: "RESEARCH"})
    elif channel == "yaml":
        path = _yaml_config(tmp_path, f"{ORDINARY_TYPO}: RESEARCH\n")
        with pytest.raises(ConfigurationError):
            AppConfig.load(path)
    else:
        monkeypatch.setenv(f"{ENV_PREFIX}{ORDINARY_TYPO.upper()}", "RESEARCH")
        with pytest.raises(ConfigurationError):
            AppConfig.load()
