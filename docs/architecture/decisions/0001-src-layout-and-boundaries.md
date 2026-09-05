# ADR-0001: `src` layout and boundary enforcement

- **Status:** Accepted
- **Date:** 2026-09-03
- **Stage:** 00

## Context

Two problems needed solving at once.

The first is ordinary packaging hygiene. With a flat layout, the working
directory is on `sys.path`, so `import qcf` succeeds whether or not the package
is installed correctly. Tests then pass against the source tree while the
distribution is broken, and the failure surfaces at the worst moment.

The second is specific to this project. QCF's most important properties are
things it must *not* be able to do: no live mode, no broker connectivity, no
real-order path, no tracked market data. Properties stated only in prose decay,
because prose is not run by anything. A reviewer who is tired, or new, or
confident will not catch a broker import in a large diff.

## Decision

Use a `src` layout: the package lives at `src/qcf` and is imported from the
installed distribution.

Enforce the project boundaries with an executable check,
`scripts/check_project_boundary.py`, which runs in CI and in pre-commit. It
verifies:

- `OperatingMode` declares exactly the permitted members and no live member;
- no module imports a broker, exchange, or market-data client, and `src/qcf`
  additionally imports no network module;
- no function in `src/qcf` is named as an order transmitter without a simulation
  marker;
- no `.env` file and no market data is tracked;
- the required Stage 00 files exist;
- the package imports and the example configuration validates;
- the internal timezone is UTC;
- the CME Euro FX product code is written `6E`;
- relative documentation links resolve.

Import inspection is performed over the syntax tree, not by text search, so
prose and test fixtures that mention a prohibited concept are not flagged for
describing it. The checker and the test suite are exempt from content scans, for
the same reason.

## Alternatives considered

**Flat layout.** Rejected: it hides installation defects and makes the "is this
what ships?" question unanswerable from a test run.

**Review-only boundary enforcement.** Rejected. The boundaries are exactly the
properties a reviewer is least likely to notice being violated, because the
violation looks like ordinary code.

**Text search for forbidden names.** Rejected: it cannot distinguish an import
from a sentence about an import, so it would fire on the documentation that
explains the rule, and the resulting noise would get it disabled.

**`import-linter` for layer direction.** Deferred, not rejected. The module
graph is currently one package; a dependency to enforce a rule about a graph
that does not exist yet would be premature. It becomes worthwhile when the
domain packages in [`../target-layout.md`](../target-layout.md) exist.

## Consequences

The package must be installed to be importable, so every command runs through
`uv run`. That is a small, constant cost and it is the point: what the tests
import is what would ship.

The checker needs maintenance as the project grows — new packages, new required
files. That maintenance is visible and reviewable, which is better than a rule
that silently stops covering new code.

The deny-lists are narrow by design. A broad allowlist would quietly re-open the
boundary it defends, so entries are added deliberately and documented in the
module.

## Verification

- `uv run python scripts/check_project_boundary.py` exits zero.
- `tests/contract/test_project_boundary.py` asserts each check catches a
  deliberate violation constructed in a temporary directory, so the checks are
  proven to fail when they should rather than merely observed to pass.
- `tests/integration/test_config_loading.py` asserts `qcf` resolves to an
  installed distribution.
