# Runbooks

**Status: not implemented.**

**Owning stage: Stage 17.**

## Intended responsibility

Hold operational procedures for paper operation: incident response, halt investigation, evidence collection, the versioned restart process, and the controlled improvement loop.

Each runbook states its trigger, the immediate containment steps, what evidence to preserve before touching anything, and who must approve a resumption.

## Premature implementation is forbidden

There is no automatic resumption after a risk, compliance, data, or software incident. A halt is latched: restarting the process does not clear it, and only an explicit human decision does.

A model is never retrained on an incident and immediately resumed. A parameter is never changed because one trade lost. A loss is not evidence of a bug, and a bug is not excused by a profit.

Every correction is developed offline, gains a regression fixture, reruns every affected validation gate, and becomes a new immutable version before any paper operation resumes.

Nothing in this area may be built before its stage begins, and its stage may not begin before the stages it depends on have been reviewed and accepted. Building ahead of the gate produces work that was never validated against the evidence the earlier stages were meant to produce.
