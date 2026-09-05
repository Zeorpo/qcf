# Stages

QCF is built in numbered stages. Each is scoped, implemented, validated,
reported, and reviewed before the next begins.

## Why stages

The ordering is the method. Data quality, accounting, execution realism, risk,
and validation must exist *before* strategy research, because a promising result
obtained without them cannot be distinguished from a lucky one. Building a
strategy first and adding costs later reliably produces an edge that disappears
when the costs arrive — after months of work have been invested in believing it.

## Documents

| Document | Contents |
| --- | --- |
| `roadmap.md` | All twenty stages at a high level |
| `stage-NN-<name>.md` | One stage's scope, exclusions, requirement IDs, traceability, and acceptance gates |
| `../project-state.md` | Where the project currently is |
| `../../reports/stages/stage-NN-report.md` | What was actually done and observed |

The distinction between the last two matters. The stage document is written
**before** implementation and states what is required. The report is written
after and states what was observed, including failures. Traceability
reconstructed afterwards documents what was built, not what was required.

## Gates

A stage is recommended PASS only when every acceptance gate in its own document
is met, each supported by observed command output rather than assertion. A gate
is never lowered to make an implementation pass; a stage that cannot meet one is
reported INCOMPLETE or FAIL, with the evidence.

After each stage, an independent adversarial review looks for what the
implementation missed. The next stage is justified only if that review records
no unresolved blockers.
