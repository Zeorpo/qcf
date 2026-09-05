# Stage 00 — Professional Repository Foundation

- **Stage:** 00
- **Status:** In progress
- **Branch:** `claude/new-session-19lczd`
- **Starting commit:** none — empty repository
- **Bootstrap commit:** `bd2586223b7542ee46924a0c224168777fbccb6e`

This document is written **before** the Stage 00 implementation and is the
predeclared traceability plan for it. It is not a summary produced after the
fact.

## Objective

Establish a typed, testable, documented, reproducible, and security-conscious
Python foundation for QCF, with the research-only boundary enforced by
executable checks rather than by assertion.

## Scope

Stage 00 creates repository scaffolding, Python packaging, a locked Python 3.12
environment, core enums and exceptions, typed non-financial configuration,
explicit UNKNOWN-value behaviour, deterministic fingerprints, structured logging
with redaction, package version metadata, a project-boundary checker, the test
hierarchy, development documentation, architecture decisions, project state and
roadmap, CI and pre-commit gates, and the Stage 00 report.

## Explicit exclusions

Stage 00 implements **no part of a trading system**. The following are out of
scope and their absence is verified by `QCF-S00-026`:

market data of any kind (real or fabricated) · data ingestion, schemas, or
adapters · instrument, calendar, expiry, or roll logic · tick or P&L arithmetic
· features · strategies or signals · position sizing · backtesting · execution
simulation · paper-account behaviour · risk-engine behaviour · compliance-engine
behaviour · model training · broker, prop-firm, or account connectivity · order
submission, modification, or cancellation · any live operating mode.

Later domain packages under `src/qcf` are **documented, not created**. See
[`../architecture/target-layout.md`](../architecture/target-layout.md).

## Assumptions

1. The repository was empty at the start of this stage; nothing could be
   overwritten. Re-verified immediately before the bootstrap commit.
2. Python 3.12 is the development interpreter. The environment's default
   `python3` is 3.11 and is not used for any validation.
3. Globally installed Ruff, mypy, and pytest are not the project toolchain and
   are not cited as evidence.
4. No historical market data has been supplied or authorised. Stage 03 remains
   blocked until it is.
5. GitHub Advanced Security is not assumed to be available; secret scanning uses
   a pinned `detect-secrets`.
6. The security reporting contact is `UNKNOWN` until the owner supplies one.

## Requirements and traceability

| ID | Requirement | Implementation | Verification |
| --- | --- | --- | --- |
| QCF-S00-001 | Empty-repository bootstrap: remote `main` created from a documented minimal commit; work continues on the environment-mandated branch | `README.md`, `.gitignore`, `LICENSE_POLICY.md`, `docs/architecture/decisions/0000-adr-process.md` | ADR-0007; `reports/stages/stage-00-report.md`; remote `main` SHA recorded |
| QCF-S00-002 | One authoritative `pyproject.toml`: name, non-hype description, `requires-python >=3.12`, `src` discovery, `py.typed`, pre-1.0 version | `pyproject.toml`, `src/qcf/py.typed` | `tests/integration/test_config_loading.py::test_package_imports_from_installed_layout`; build/install validation |
| QCF-S00-003 | Approved dependency set exactly; resolved versions locked and committed | `pyproject.toml`, `uv.lock` | `uv sync --frozen`; `tests/contract/test_project_boundary.py::test_dependency_set_matches_approved_list` |
| QCF-S00-004 | Core enums with exact permitted values | `src/qcf/core/enums.py` | `tests/unit/core/test_enums.py` |
| QCF-S00-005 | No `LIVE` operating mode; default mode `DISABLED` | `src/qcf/core/enums.py`, `src/qcf/core/config.py` | `tests/unit/core/test_enums.py::test_operating_mode_has_no_live_member`; `tests/contract/test_project_boundary.py`; `scripts/check_project_boundary.py` |
| QCF-S00-006 | Justified core exception hierarchy carrying useful, secret-free messages | `src/qcf/core/exceptions.py` | `tests/unit/core/test_exceptions.py` |
| QCF-S00-007 | Explicit immutable UNKNOWN: stable representation, no silent coercion to int/float/Decimal/bool, no arithmetic, prohibited coercions raise `UnknownValueError` | `src/qcf/core/unknown.py` | `tests/unit/core/test_unknown.py`; `tests/property/test_fingerprint_properties.py::test_unknown_coercions_always_fail` |
| QCF-S00-008 | Frozen non-financial configuration: YAML loading, `QCF_` env overrides, unknown-key rejection, UTC fixed, default mode `DISABLED` | `src/qcf/core/config.py`, `config/base.example.yaml` | `tests/unit/core/test_config.py`; `tests/integration/test_config_loading.py` |
| QCF-S00-009 | Path resolution independent of the working directory when a base path is configured | `src/qcf/core/config.py` | `tests/unit/core/test_config.py::test_paths_resolve_against_base_path_not_cwd` |
| QCF-S00-010 | Canonical JSON + SHA-256 fingerprints with documented determinism properties | `src/qcf/core/fingerprint.py` | `tests/unit/core/test_fingerprint.py`; `tests/property/test_fingerprint_properties.py` |
| QCF-S00-011 | File fingerprinting that refuses directories rather than recursing by surprise | `src/qcf/core/fingerprint.py` | `tests/unit/core/test_fingerprint.py::test_fingerprint_file_rejects_directory` |
| QCF-S00-012 | structlog configuration: UTC timestamps, level, console and JSON renderers, run-context binding, idempotent reconfiguration | `src/qcf/core/logging.py` | `tests/unit/core/test_logging.py` |
| QCF-S00-013 | Centralised redaction: nested structures, non-mutating, case-insensitive and separator-tolerant | `src/qcf/core/logging.py` | `tests/unit/core/test_logging.py`; `tests/property/test_fingerprint_properties.py::test_redaction_never_mutates_input` |
| QCF-S00-014 | Version metadata: package version, best-effort git commit, explicit UNKNOWN outside a checkout, no shell or network, import never fails | `src/qcf/core/version.py` | `tests/unit/core/test_version.py` |
| QCF-S00-015 | Read-only project-boundary checker covering modes, broker SDKs, order paths, tracked data, `.env`, required files, imports, example config, UTC, `6E` terminology, and documentation links | `scripts/check_project_boundary.py` | `tests/contract/test_project_boundary.py` (including deliberate temporary violations) |
| QCF-S00-016 | Data-directory skeleton committed; every actual data file ignored | `.gitignore`, `data/**` | `tests/contract/test_data_directory_protection.py` |
| QCF-S00-017 | Documentation set: README, architecture, layering rules, target layout, development guides, area READMEs | `README.md`, `docs/**` | `scripts/check_project_boundary.py` documentation-link check |
| QCF-S00-018 | ADRs 0000–0007 accepted and internally consistent; deferred decisions recorded with owning stages | `docs/architecture/decisions/**` | `scripts/check_project_boundary.py`; manual review |
| QCF-S00-019 | Security foundation: `SECURITY.md` with UNKNOWN contact, `.env.example`, pinned `detect-secrets` with reviewed baseline in pre-commit and CI | `SECURITY.md`, `.env.example`, `.secrets.baseline`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml` | `detect-secrets` verification; `tests/contract/test_project_boundary.py::test_no_env_file_is_tracked` |
| QCF-S00-020 | Deterministic, offline unit, integration, property, and contract tests; regression directory documented but empty of fictional cases | `tests/**` | Full `pytest` run |
| QCF-S00-021 | Ruff formatting and linting, strict mypy for `src/qcf`, pytest with branch coverage at a 90% gate | `pyproject.toml` | `ruff format --check`, `ruff check`, `mypy`, `pytest --cov` |
| QCF-S00-022 | Pre-commit configuration with pinned hook revisions | `.pre-commit-config.yaml` | `pre-commit run --all-files` |
| QCF-S00-023 | CI on pull requests and pushes to `main`: least privilege, no secrets, 3.12 and 3.13 matrix, locked install, all quality and security gates, actions pinned to immutable SHAs | `.github/workflows/ci.yml` | Remote CI run, reported separately from local results |
| QCF-S00-024 | Stage scope and traceability, project state, and roadmap | `docs/stages/**`, `docs/project-state.md` | This document; manual review |
| QCF-S00-025 | Stage 00 report containing observed commands and exact results | `reports/stages/stage-00-report.md` | Manual review against command output |
| QCF-S00-026 | No later-stage financial behaviour exists anywhere in the repository | (absence) | `scripts/check_project_boundary.py`; `tests/contract/test_project_boundary.py`; review of the complete changed-file list |

## Acceptance gates

Stage 00 may be recommended **PASS** only if all of the following hold, each
supported by observed command output rather than assertion:

1. Remote `main` exists at the documented bootstrap commit.
2. The branch contains Stage 00 work only.
3. The package installs and imports under Python 3.12 from the installed `src`
   layout.
4. Runtime and development dependencies are locked in `uv.lock`.
5. Configuration is frozen and validated; default mode is `DISABLED`; no `LIVE`
   mode exists.
6. UNKNOWN values cannot silently coerce or enter arithmetic.
7. Fingerprint properties hold.
8. Redaction tests pass and no representative secret appears in rendered output.
9. `ruff format --check`, `ruff check`, strict `mypy`, and the full test suite
   pass, with branch coverage at or above 90%.
10. The project-boundary checker and `detect-secrets` verification pass.
11. No market data is tracked; no `.env` is tracked.
12. Documentation links resolve and ADRs are complete.
13. No later-stage financial behaviour exists.

Failure to reach a gate is reported as **INCOMPLETE** or **FAIL** with the
observed evidence. A gate is never lowered to make an implementation pass.

## Current status

Filled in by `reports/stages/stage-00-report.md` at the end of the stage.

## Reviewer decision

> **Decision:** _pending independent adversarial review_
> **Reviewer:**
> **Date:**
> **Findings:** _to be completed by the reviewer_
> **Next permitted stage:** Stage 01 — Governance and Versioned Policy Contracts,
> only if this review records no unresolved blockers.
