# ADR-0006: Committed lockfile and reproducibility

- **Status:** Accepted
- **Date:** 2026-09-03
- **Stage:** 00 (build-isolation boundary corrected in 00-F, finding R-10)

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
`uv sync --all-groups --frozen` everywhere, including CI, so that **the project,
optional and development dependencies represented in that lock** are not
re-resolved and a stale lock fails the build rather than silently resolving
something newer.

`--frozen` means uv does not update the project lock during the sync. It does
**not** mean the installation is offline, and it does not mean every input is an
entry in the lock. QCF's first-party package is built in an isolated PEP 517
environment from `[build-system].requires`, and those requirements — together
with their transitive dependencies — are selected outside `uv.lock` each time.
See the boundary table below.

Runtime and development dependencies are separated: `project.dependencies` for
what the package imports, and a `dev` dependency group for tooling. Only what
the current stage actually imports is added — a rule that keeps the runtime
surface small and makes each addition a visible, justified decision.

Every completed run records the code commit, the environment fingerprint, the
configuration fingerprint, and the data fingerprints. Stage 00 provides the
primitives: `qcf.core.fingerprint` and `qcf.core.version`.

## What is controlled, and what is not

Adapted from what was actually observed with the CI sync command
(`uv sync --all-groups --frozen`) against an empty cache, using the locked uv
version. Nothing here claims a control that was not verified.

| Input or process | Controlled now | Not guaranteed now |
| --- | --- | --- |
| Project, optional and dev dependencies | Resolved versions and hashes recorded in `uv.lock`; `--frozen` refuses to update it, and a stale lock fails | Permanent artifact or index availability; the lock names what to fetch, not that it will still be fetchable |
| PEP 517 build requirements | A declared lower bound, `hatchling>=1.27` | Complete locking, exact or transitive versions, and offline availability — seven packages were selected outside `uv.lock` on a clean sync |
| CI actions and interpreters | Actions pinned to immutable commit SHAs; Python 3.12 and 3.13 named explicitly | The runner image, its preinstalled toolchain, and the surrounding infrastructure |
| Source and configuration identity | Canonical inputs defined and fingerprinted (`qcf.core.fingerprint`, ADR-0008, ADR-0009) | A universal environment or artifact identity; fingerprints are machine-specific where paths differ |
| Built distributions | Contents inspected; the wheel carries `qcf/` and dist-info only | Byte-identical rebuilds across environments; no such claim is made |

**Residual limitation (finding R-10).** Build-time resolution is outside the
lock. Closing it properly requires all of: complete build dependency and version
control including transitive requirements; artifact and hash availability for
them; controlled runner and toolchain inputs; evidence of a clean offline
install; and an explicit definition of what "reproducible artifact" would mean
here. Pinning `hatchling` to one version would satisfy none of those on its own,
and disabling build isolation would move the trust boundary rather than describe
it — both are separate design decisions, not documentation fixes.

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
- The build-isolation boundary above is reproducible with
  `UV_CACHE_DIR=<empty dir> uv sync --all-groups --frozen -v`, which reports
  `Resolving build requirements` and the selected build packages.
- `scripts/check_project_boundary.py` rejects the specific absolute phrasings
  that were previously false here and in `SECURITY.md`.
- `tests/contract/test_project_boundary.py` asserts the declared dependency set
  matches the approved list, so a dependency cannot be added without the test
  being changed deliberately.
