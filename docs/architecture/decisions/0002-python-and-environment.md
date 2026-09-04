# ADR-0002: Python 3.12 or newer, uv, and the CI matrix

- **Status:** Accepted
- **Date:** 2026-09-03
- **Stage:** 00

## Context

The development machine's default `python3` is 3.11, while 3.12 and 3.13 are
also installed. Ruff, mypy, and pytest were present globally as unpinned tools
bound to the 3.11 interpreter.

That arrangement produces a specific and dangerous failure: validation runs
green against an interpreter and tool versions that are not the project's, and
the report says "tests pass" without saying what they passed under. Reproducing
a result later then requires guessing what was actually installed.

Python 3.12 is also a floor with real content here: `StrEnum`, PEP 695 type
parameters, and `logging.getLevelNamesMapping()` are all used by Stage 00 code.

## Decision

Require Python `>=3.12`. Create the project environment explicitly from a 3.12
interpreter using `uv`, and pin every tool as a development dependency inside it.

Run **every** validation command through `uv run`, so that formatting, linting,
type checking, and tests all execute against the locked environment.

Global installations of Ruff, mypy, or pytest are never cited as evidence in a
stage report. CI runs a matrix of 3.12 and 3.13: 3.12 is the floor and 3.13 is
the newest available, so a regression at either end surfaces immediately.

## Alternatives considered

**Poetry.** Available and capable. Rejected because uv resolves and installs
substantially faster in CI and manages the interpreter itself, and because only
one lock mechanism should exist.

**Plain `pip` with `requirements.txt`.** Rejected: no cross-platform lock, and
no clean separation between runtime and development dependency sets.

**Accepting the 3.11 default.** Rejected: it contradicts the stated floor and
would forbid `StrEnum` and PEP 695 syntax for no gain.

**Single-version CI on 3.12.** Rejected: it would let a 3.13 incompatibility
land unnoticed and surface later as an unexplained environment problem.

## Consequences

Contributors need `uv`. In exchange, `uv sync --all-groups --frozen` produces a
byte-identical environment on any machine, which is what makes a run record
meaningful.

`uv.lock` is committed and must be regenerated when dependencies change; CI
fails on a stale lock rather than silently resolving something newer.

The 3.13 matrix entry occasionally surfaces upstream incompatibilities before
they are convenient to fix. That is the intended service, not a cost.

## Verification

- `uv run python -c "import sys; print(sys.version)"` reports 3.12 or newer.
- `uv sync --all-groups --frozen` succeeds, proving the lock is current.
- `.github/workflows/ci.yml` declares the 3.12 and 3.13 matrix.
- The Stage 00 report records the exact interpreter path and version observed.
