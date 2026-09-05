# ADR-0010: Configuration fails closed on every channel, and diagnostics name only what we declared

- **Status:** Accepted
- **Date:** 2026-09-04
- **Stage:** 00-D (alias prohibition and diagnostic boundary added in 00-E)

## Context

Three findings from the Stage 00 review cycle turned out to be one decision that
had never actually been made, only assumed.

ADR-0003 recorded that configuration "rejects unknown keys (`extra="forbid"`) so
that a misspelled setting fails loudly instead of being ignored". That statement
was true of the YAML mapping and of keyword arguments, and **false of the
environment** (finding R-12). pydantic-settings collects only prefixed names that
match a declared field and discards the rest before the model is constructed, so
`extra="forbid"` never saw them: `QCF_MOED=PAPER` loaded successfully with
`mode=DISABLED`, while the identical typo through either other channel was a hard
error. The project's own prose names this failure — a setting that was configured
and never read — as the thing it exists to prevent.

The same silence existed inside a single file (finding R-13): PyYAML's default is
last-value-wins, so a file setting `mode` twice loaded without complaint, and a
file that said two contradictory things quietly became one of them.

Separately, the diagnostic that reports these failures was itself unsafe (finding
H-01). An unknown key is text the operator supplied and QCF never validated, and
it can be a credential pasted into the wrong place. The guard was a *shape*
heuristic — redact if the name contains a sensitive-looking word, exceeds 64
characters, or is not a Python identifier. A pasted credential is normally
identifier-shaped and short, so it passed all three tests and was echoed verbatim
into the message, `repr`, structured details and the traceback. Safe logging was
already the default and did not leak, but an exception that a caller prints,
interpolates, or hands to `logging.exception` is outside the logger's reach.

## Decision

**One principle, three channels.** An unrecognised or repeated configuration key
is an error through keyword arguments, through the `QCF_` environment namespace,
and through the YAML file alike. Three mechanisms are required because no single
one reaches all three:

- `extra="forbid"` covers keyword arguments and the YAML mapping.
- `qcf.core.config.check_environment` validates the `QCF_` namespace against the
  schema before construction, from a `model_validator(mode="before")` so that
  direct construction is covered as well as `AppConfig.load()`. Namespace
  membership is decided case-insensitively even for a case-sensitive model, so a
  wrongly-cased name is reported as ours-and-misspelled rather than filed as
  somebody else's variable. Names without the prefix are ignored entirely.
- `_UniqueKeySafeLoader`, a `SafeLoader` subclass scoped to this module, rejects
  duplicate keys at every mapping depth, YAML merge keys (`<<`), and non-string
  keys. PyYAML's global `SafeLoader` is not modified, so no other module's
  parsing changes.

**Aliases are prohibited.** Environment names are the `QCF_` prefix plus the
canonical field name, and nothing else. `AppConfig` fields MUST NOT declare
`alias`, `validation_alias`, `serialization_alias`, `AliasChoices`, `AliasPath`,
or a `model_config` `alias_generator`. `assert_no_field_aliases` enforces this
from `__pydantic_init_subclass__`, so an aliased field is a class-definition
error rather than a runtime surprise, and `AppConfig` itself is checked at import.

The reason is finding DR-02. An earlier version of this ADR claimed the
environment guard was alias-aware. It was not: pydantic-settings reads a field
carrying a `validation_alias` from the **unprefixed** alias, so both
`QCF_<ALIAS>` and `QCF_<FIELD>` are silently ignored — R-12's "configured and
never read" returning by a side door. Rather than build alias support nothing
needs, Stage 00 forbids aliases and enforces the prohibition.

Before alias support could be introduced, four things must exist: one explicit
precedence and naming design; environment behaviour verified against the locked
pydantic-settings rather than assumed; an error-safety review, because an alias
spelling reaches error locations as caller-controlled text; and contract tests
covering all of it.

**Diagnostics name only what we declared.** A location segment is printed only if
it matches a name in `schema_field_names()`, which is exactly the model's
canonical field names — aliases being prohibited, no other spelling can reach an
error location. Everything else becomes one constant placeholder. The rule is
positive — an allowlist — rather than a search for suspicious input, because
deciding from length, entropy, prefixes, identifier syntax or keywords is exactly
what H-01 defeated. Integer sequence indices are preserved: pydantic generates
them, and they can carry nothing. pydantic's own `msg` is not copied through
either; message text is chosen from a code-owned table keyed on the error type.

Keyword-based redaction in `qcf.core.logging` remains, as defence in depth. It
does not decide whether untrusted text may be printed.

**The boundary, stated exactly (finding DR-01).** The guarantee covers values and
unknown key names received *as data* — explicit mappings, YAML, environment — and
their appearance in public exception text, `repr`, details, and the supported
logger. It does not and cannot cover source code the caller wrote: a traceback
prints the caller's own source line, so a literal written directly into a call
shows up there whatever this package does. Nor frame locals under a debugger, nor
text a caller independently prints. Never hard-code a sensitive value as a
literal; supply it as data, where the guarantee applies.

## Alternatives considered

**Keep the shape heuristic and widen it.** Adding entropy scoring or more
keywords would raise the bar without changing the shape of the argument: the
guard would still be guessing about text it does not understand, and any
threshold has a value just below it. Rejected — an allowlist is decidable.

**Print the unknown key but only in a "debug" mode.** This is the second unsafe
default output path the correction brief warns against. A flag that makes
diagnostics unsafe will be enabled on the day someone is debugging, which is the
day the output gets pasted somewhere. Rejected.

**Report unknown environment names to help the operator find the typo.** This is
the obvious usability choice and it reintroduces H-01 through the environment
channel: an environment variable *name* is untrusted input too. A count and a
stable reason code are reported instead. Rejected on the same grounds.

**Let duplicate YAML keys win last, as PyYAML does.** First-wins is no better;
both silently pick a side in a contradiction the file did not resolve. Rejected.

**Patch `yaml.SafeLoader` globally.** Simpler, and it would change YAML parsing
for every dependency in the process. Rejected as out of proportion.

**Implement alias support properly instead of forbidding aliases.** It is the
more general answer, and it would mean designing a precedence and naming scheme,
verifying it against the settings library's own alias behaviour, and reviewing
the error-safety consequences — all for a feature no field uses. Building
unused machinery is how a foundation acquires paths nobody tests. Rejected for
Stage 00; the preconditions for revisiting it are recorded above.

## Consequences

Makes easy: a misspelled setting now fails the same way wherever it is written,
so an operator can trust that a value they set is a value that was read.

Makes hard: diagnosing a typo is less direct. The error gives a position, a
stable reason code and a count, not the offending name. This is a deliberate
trade — the alternative is a diagnostic that will one day print a credential.

Makes impossible: YAML merge keys and non-string keys can no longer be used in
QCF configuration, and no field may carry an alias. None is used today; all are
rejected rather than left half-supported. A future field wanting a different
external name is a design conversation, not a one-line `Field(alias=...)`.

Costs: a second validation path exists alongside `extra="forbid"`, and it can
drift from the schema if someone hardcodes a name into it. That is why it derives
its allowlist from `model_fields` and why a synchronisation test exists. The
alias prohibition is a real restriction on future schema design, accepted
deliberately: a foundation that fails closed is worth more here than one that
accommodates a naming preference.

## Verification

- `tests/unit/core/test_config_fail_closed.py` — 81 tests covering all three
  findings. In particular:
  - `test_an_unknown_keyword_argument_is_never_echoed` and
    `test_an_unknown_yaml_key_is_never_echoed` assert an inert marker is absent
    from `str`, `repr`, `args`, `details`, `reason`, the traceback, `__cause__`,
    `__context__` and every public attribute;
  - `test_the_reported_typo_is_now_rejected` is R-12's exact reproduction;
  - `test_a_duplicate_top_level_key_is_rejected` is R-13's;
  - `test_the_check_accepts_every_declared_field_name` and
    `test_the_check_is_driven_by_the_model_not_a_hardcoded_list` are the
    synchronisation guards;
  - `test_the_global_safe_loader_is_not_mutated` asserts the scoping claim;
  - `test_a_case_sensitive_model_compares_exactly` pins the casing contract
    against what the library actually does.
  - `test_the_real_schema_declares_no_alias_of_any_form` and
    `test_every_alias_form_fails_at_class_definition` enforce the no-alias
    contract across all five field forms plus `alias_generator`;
  - `test_adding_an_alias_cannot_widen_the_environment_namespace` is the second
    line of defence, on an isolated fixture outside the guarded hierarchy.
- `uv run pytest tests/unit/core/test_config_fail_closed.py` — expect 89 passed.
- `src/qcf/core/config.py` holds 100% statement and branch coverage.
