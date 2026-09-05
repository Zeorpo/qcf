# Contributing to QCF

QCF is built in numbered stages. Each stage is scoped, implemented, validated,
reported, and reviewed before the next begins. This is not ceremony: the value
of a research system is entirely in whether its results can be trusted, and
trust comes from evidence accumulated in order.

## Non-negotiable boundaries

These are not preferences and are not open to trade-off against convenience:

- **No live mode.** `OperatingMode` has no `LIVE` member and never may.
- **No broker, prop-firm, or exchange connectivity.** No client library, no
  endpoint, no credential.
- **No real-order capability.** No function that submits, modifies, or cancels
  an order outside the process.
- **No market data in git.** Real or fabricated, no price row is ever committed.
- **No fabricated data.** If a test needs market data that does not exist, the
  test is wrong or the work is blocked. Inventing rows is not an option.
- **No weakened tests.** A failing test is fixed by fixing the code or by
  correcting a demonstrably wrong assertion — never by loosening it to pass.

`scripts/check_project_boundary.py` enforces the mechanical parts of this list.
It runs in CI and in pre-commit.

## Stage workflow

1. Start from an accepted commit.
2. Write the stage scope and traceability document **before** implementing:
   requirement IDs, the file that satisfies each, and the test that verifies it.
   Traceability reconstructed afterwards documents what was built, not what was
   required.
3. Implement only the current stage. Later stages' packages are documented in
   [`docs/architecture/target-layout.md`](docs/architecture/target-layout.md),
   not stubbed.
4. Write tests alongside each component.
5. Run the full validation sequence in
   [`docs/development/testing.md`](docs/development/testing.md).
6. Fix failures without weakening requirements.
7. Write the stage report with the **exact observed** command output, including
   failed attempts where they are informative.
8. Open a draft pull request and stop for review.

Never continue automatically to the next stage.

## Development setup

See [`docs/development/environment.md`](docs/development/environment.md). In
short: Python 3.12 or newer, `uv sync --all-groups`, and every command run
through `uv run` so that it uses the locked environment rather than whatever is
on `PATH`.

## Commits and pull requests

- Logical commits; each one internally valid on its own.
- Never force-push accepted history.
- Never commit secrets or market data.
- Conventional prefixes: `feat`, `fix`, `chore`, `docs`, `test`, `ci`, `refactor`.
- Pull requests use [the template](.github/pull_request_template.md) and state
  what was verified, with observed results rather than assertions.

## Adding an architecture decision

Copy [`docs/architecture/decisions/template.md`](docs/architecture/decisions/template.md)
to the next number and fill in every section. The **Verification** section is
required: a decision no reviewer can check has not been recorded, only asserted.
Accepted ADRs are immutable — supersede, never edit.

## Language

Reports and documentation describe what was observed. They do not claim that a
strategy will make money, that a system is safe, that a result is proven, or
that any external party has approved anything. Where evidence is weak, say so.
An honest negative result is a result; an overstated positive one is a defect.
