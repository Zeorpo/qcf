---
name: Stage review
about: Independent adversarial review of a completed stage
labels: stage-review
---

## Stage under review

- Stage:
- Branch / pull request:
- Commit range reviewed:

## Mandate

Find what the implementation missed. Do not implement fixes during this pass —
a reviewer who starts fixing stops looking.

## Areas examined

- [ ] Missing requirements, checked against the stage's own traceability table
- [ ] Look-ahead, survivorship, revision, and selection bias
- [ ] Timestamp and daylight-saving behaviour
- [ ] Fill and cost assumptions
- [ ] Futures roll logic
- [ ] Cash and profit-and-loss reconciliation
- [ ] Risk and compliance independence
- [ ] Any real-order capability
- [ ] Claims stronger than the evidence supports
- [ ] Tests that restate the implementation rather than challenging it

## Findings

For each: severity (BLOCKER / HIGH / MEDIUM / LOW), evidence, impact,
reproduction, required correction, and the regression test it needs.

### Finding 1

- **Severity:**
- **Evidence:**
- **Impact:**
- **Reproduction:**
- **Required correction:**
- **Required regression test:**

## Verdict

- [ ] PASS-WITH-NO-BLOCKERS
- [ ] FAIL

## Next permitted stage

<!-- Only if the verdict is PASS-WITH-NO-BLOCKERS. -->
