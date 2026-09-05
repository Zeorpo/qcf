# ADR-0007: Branch workflow and the initial-`main` bootstrap exception

- **Status:** Accepted
- **Date:** 2026-09-03
- **Stage:** 00

## Context

The repository was created empty: no commits, no refs. GitHub's configured
default branch was `main`, but no `main` ref existed, so there was nothing for a
pull request to target — a pull request needs a base branch, and the base branch
needs a commit.

Two conventions also had to be reconciled. The project workflow calls for stage
branches named `stage/<number>-<description>`. The execution environment for this
work mandates development on a specific branch, `claude/new-session-19lczd`, and
forbids pushing elsewhere without explicit permission.

Inventing a starting commit silently, or quietly renaming a branch to satisfy one
convention at the expense of the other, would both hide a decision that a
reviewer of the repository's history has a right to see.

## Decision

**Bootstrap.** A single minimal commit, `chore: bootstrap QCF repository`, was
created on the environment-mandated branch and pushed to `refs/heads/main`
without force. It contains only four files: `README.md` stating the project
identity, its private research status, and the no-live-order boundary;
`.gitignore` covering Python, environment, secret, data, and artefact rules so
that no market data or credential could be tracked from the first commit;
`LICENSE_POLICY.md`; and `docs/architecture/decisions/0000-adr-process.md`.

It contains no package, configuration, strategy, data, or execution code. It is a
base branch, not a stage.

**Branch naming.** Stage 00 work continues on `claude/new-session-19lczd`, which
deviates from the `stage/00-...` convention. The environment constraint was
explicitly approved by the repository owner in preference to renaming. Later
stages use `stage/<number>-<description>` where no such constraint applies.

**Pull request.** Stage 00 is proposed as a draft pull request into `main` and
waits for review. The bootstrap commit is not squashed away before that review,
so the exception stays visible in the history it applies to.

## Alternatives considered

**Push Stage 00 directly to `main`.** Rejected: no reviewable pull request, and
the boundary between "bootstrap" and "stage work" would disappear.

**Create an empty commit as the base.** Rejected. An empty root commit carries no
information, and `.gitignore` in particular needs to exist from the first commit —
its job is to prevent data and secrets from being tracked, which is a job it can
only do if it precedes everything else.

**Rename the local branch to `stage/00-repository-foundation`.** Rejected: it
would violate the environment constraint, which was the explicit subject of the
owner's approval.

**Make the bootstrap commit the whole of Stage 00.** Rejected: Stage 00 must be
reviewable as a diff, and a repository whose entire foundation arrives in one
unreviewed commit has skipped the gate it exists to pass.

## Consequences

`main` carries one commit that is not itself a completed stage. This is recorded
here and in the Stage 00 report so it is not mistaken for an accepted stage
artefact.

The Stage 00 branch name does not match the convention that later stages follow.
The deviation is documented rather than silently normalised.

Once Stage 00 merges, `main` holds the accepted foundation and the normal
workflow applies: branch from an accepted commit, one stage per branch, no
force-pushing accepted history, merge only after review and passing checks.

## Verification

- Remote `main` points at the bootstrap commit recorded in
  `reports/stages/stage-00-report.md`.
- The bootstrap commit contains exactly the four files named above.
- The Stage 00 branch contains Stage 00 work only.
- No force-push occurred; the bootstrap commit is an ancestor of the Stage 00
  branch.
