# Git and stage workflow

## Branches

| Branch | Purpose |
| --- | --- |
| `main` | Accepted history. Protected by review; never force-pushed. |
| `stage/<number>-<description>` | One stage of work |

Stage 00 is the documented exception: it was developed on
`claude/new-session-19lczd` under an environment constraint, and `main` was
created by a minimal bootstrap commit so that a pull request had a base. Both
are recorded in
[ADR-0007](../architecture/decisions/0007-branching-and-bootstrap.md).

## Per-stage sequence

1. Verify repository, branch, and `HEAD`.
2. Inspect accepted prior-stage artefacts.
3. Inspect the working tree; preserve unrelated work.
4. Restate the stage scope and its exclusions.
5. Write the traceability plan **before** implementing.
6. Implement only the current stage.
7. Add unit, integration, property, contract, and regression tests as applicable.
8. Run the full validation sequence in [`testing.md`](testing.md).
9. Fix failures without weakening requirements; rerun.
10. Review for unnecessary complexity, optimistic assumptions, and boundary
    bypasses.
11. Update documentation, `docs/project-state.md`, and the stage report.
12. Record the exact observed commands and results.
13. Commit logically, only after validation passes.
14. Open a draft pull request and **stop for review**.

Never continue automatically to the next stage. The gate is the point.

## Commits

Conventional prefixes: `feat`, `fix`, `chore`, `docs`, `test`, `ci`, `refactor`,
with an optional scope such as `feat(core):`.

- Each commit is internally valid on its own.
- No empty commits, and never an empty commit to re-trigger CI.
- Never commit secrets or market data.
- Never force-push accepted history.

## Pull requests

Draft until the stage is complete and validated. The body follows
[the template](../../.github/pull_request_template.md) and reports what was
verified, with observed output rather than assertions. CI status is reported
separately from local results, and is never claimed before a workflow has
actually completed.

## Reviewing a stage

An independent adversarial pass, whose job is to find what the implementation
missed rather than to confirm it:

- missing requirements against the stage's own traceability table;
- look-ahead, survivorship, revision, and selection bias;
- timestamp and daylight-saving handling;
- fill and cost assumptions;
- roll logic;
- cash and profit-and-loss reconciliation;
- risk and compliance independence;
- **any** real-order capability;
- claims stronger than the evidence supports;
- tests that restate the implementation instead of challenging it.

Findings are classified BLOCKER, HIGH, MEDIUM, or LOW, each with evidence,
impact, reproduction, the required correction, and the regression test it needs.
The review ends with PASS-WITH-NO-BLOCKERS or FAIL.
