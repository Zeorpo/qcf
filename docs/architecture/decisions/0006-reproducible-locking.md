# ADR-0006: Committed lockfile and reproducibility

- **Status:** Accepted
- **Date:** 2026-09-03
- **Stage:** 00

## Context

A research result is only evidence if it can be reproduced, and reproduction
requires knowing what produced it: the code, the configuration, the data, and
the environment. The environment is the component most often omitted, and the
one most likely to change without anyone noticing.

An unpinned dependency set means a run six months from now resolves different
versions. If the result differs, there is no way to tell whether the finding was
fragile or the environment moved.

## Decision

Commit `uv.lock` with every resolved version and hash. Install with
`uv sync --all-groups --frozen` everywhere, including CI, so that nothing is
resolved at install time and a stale lock fails the build rather than silently
resolving something newer.

Runtime and development dependencies are separated: `project.dependencies` for
what the package imports, and a `dev` dependency group for tooling. Only what
the current stage actually imports is added — a rule that keeps the runtime
surface small and makes each addition a visible, justified decision.

Every completed run records the code commit, the environment fingerprint, the
configuration fingerprint, and the data fingerprints. Stage 00 provides the
primitives: `qcf.core.fingerprint` and `qcf.core.version`.

## Alternatives considered

**Unpinned dependencies with a version floor.** Rejected: convenient until a
result changes and nobody can say why.

**Pinning only direct dependencies.** Rejected. Transitive versions affect
numerical behaviour, and a floating transitive dependency is exactly as capable
of changing a result as a direct one.

**A container image as the unit of reproducibility.** Not rejected, but not
sufficient alone. An image pins more than the lock does, but it is opaque:
`uv.lock` is diffable and reviewable, so a dependency change is visible in a pull
request. The two compose well and the lock is the prerequisite.

## Consequences

Dependency updates become explicit commits with a reviewable diff, which is the
intended behaviour rather than a cost.

`uv.lock` conflicts on merge are resolved by regenerating, never by hand-editing;
`.gitattributes` marks it generated so reviewers know not to read it as source.

Contributors must have `uv`. See [ADR-0002](0002-python-and-environment.md).

## Verification

- `uv.lock` is tracked.
- `uv sync --all-groups --frozen` succeeds locally and in CI; a stale lock fails.
- `tests/contract/test_project_boundary.py` asserts the declared dependency set
  matches the approved list, so a dependency cannot be added without the test
  being changed deliberately.
