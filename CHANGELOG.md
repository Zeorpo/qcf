# Changelog

Notable changes to QCF. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Versions are pre-1.0 and carry no stability promise. QCF is research software;
there is no released stable version and none is implied by a version number.

## [Unreleased]

### Added

- **Stage 00 — Professional Repository Foundation.**
  - `src/qcf` package layout with `py.typed`, built and locked against Python 3.12.
  - `qcf.core.enums`: `OperatingMode` (no `LIVE` member), `HaltState`, `Severity`,
    `DataQualityDisposition`.
  - `qcf.core.exceptions`: the `QCFError` hierarchy.
  - `qcf.core.unknown`: an explicit `UNKNOWN` sentinel that cannot be coerced or
    used in arithmetic.
  - `qcf.core.fingerprint`: canonical JSON and SHA-256 fingerprints with
    documented determinism properties.
  - `qcf.core.config`: frozen, validated, non-financial application settings with
    YAML and `QCF_` environment layering.
  - `qcf.core.logging`: structlog configuration with centralised redaction.
  - `qcf.core.version`: package version and best-effort revision resolution.
  - `scripts/check_project_boundary.py`: executable verification of the
    research-only boundary.
  - Unit, integration, property, and contract test suites.
  - Architecture decision records ADR-0000 through ADR-0007.
  - CI, pre-commit, and `detect-secrets` quality and security gates.

### Notes

- No market data, strategy, model, backtester, execution simulator, paper
  broker, risk engine, or compliance engine exists in this release. None is
  implied by the presence of the vocabulary that will later describe them.
