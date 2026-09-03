# ADR-0000: Architecture decision record process

- **Status:** Accepted
- **Date:** 2026-09-03
- **Stage:** 00 — Professional Repository Foundation

## Context

QCF is a staged research system in which decisions made early — how money is
represented, what a timestamp means, which layer may create exposure — constrain
every later stage. Those decisions need to survive the conversation that
produced them.

Two failure modes matter here specifically. The first is a decision that is made
implicitly by the first line of code that assumes it, so that no one can later
tell whether it was considered. The second is a decision that is quietly
reversed under deadline pressure, which for this project could mean reversing a
safety boundary rather than a stylistic preference.

An architecture decision record is a short, immutable, numbered document that
states what was decided, what was rejected, and how the decision can be checked.
It is the cheapest mechanism that addresses both failure modes.

## Decision

Every architecturally significant decision is recorded as an ADR in
`docs/architecture/decisions/`, numbered sequentially from `0000`, using the
template in `docs/architecture/decisions/template.md`.

A decision is architecturally significant if it constrains later stages, affects
a project boundary, changes the meaning of recorded data, or would be expensive
to reverse. Formatting preferences and local implementation choices are not
ADRs.

Every ADR carries these sections:

| Section | Purpose |
| --- | --- |
| Title | `ADR-NNNN: <decision>` |
| Status | Proposed, Accepted, Superseded by ADR-NNNN, or Rejected |
| Date | ISO-8601 date of the status shown |
| Stage | The stage that owns the decision |
| Context | The forces that made a decision necessary |
| Decision | What was decided, stated so it can be checked |
| Alternatives considered | What was rejected and why |
| Consequences | What this makes easy, hard, or impossible later |
| Verification | How a reviewer confirms the code matches the decision |

The **Verification** section is required, and is what separates an ADR from a
note. A decision no reviewer can check is not recorded, it is only asserted.

ADRs are immutable once accepted. A changed decision is a new ADR that
supersedes the old one; the superseded record stays in place with its status
updated, so the history of the reasoning survives.

An ADR may also record a decision that is deliberately **deferred**, naming the
stage that owns it. Deferred decisions are listed in
`docs/architecture/decisions/README.md` so an open question cannot be lost by
being merely unwritten.

## Alternatives considered

**Decisions recorded in commit messages.** Rejected. Commit messages are not
indexed by topic, cannot be superseded, and are read in the order changes
happened rather than in the order a new reader needs them.

**A single running design document.** Rejected. A mutable document loses the
reasoning behind reversed decisions, which is precisely the history that
matters when a boundary is about to be reversed a second time.

**Issue-tracker discussions.** Rejected as the primary record because it binds
the project's design history to a hosting platform and to network access. ADRs
are plain files in the repository and remain readable from a clone.

## Consequences

Decisions carry a small, fixed documentation cost, paid at the moment of
deciding rather than during a later review. Reviewers gain a fixed place to look
before asking why something is the way it is.

Because ADRs are immutable and numbered, an ADR that is wrong stays visible.
That is intended: a superseded decision plus its replacement is more informative
than a document that only ever shows the current answer.

The **Verification** requirement means some decisions will surface as executable
checks — `scripts/check_project_boundary.py` and the contract tests exist partly
to verify ADR-0001 and ADR-0005.

## Verification

- `docs/architecture/decisions/` contains `README.md`, `template.md`, and
  sequentially numbered records with no gaps.
- Every record contains all nine sections named above.
- `scripts/check_project_boundary.py` verifies that documentation relative links
  resolve, which includes links between ADRs.
