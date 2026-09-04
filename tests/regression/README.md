# Regression tests

**Empty by design.**

A regression test is added when a real defect or incident has occurred, and it
encodes that specific failure so it cannot recur unnoticed. Writing one before
there is a defect tests an imagined failure: it passes from the moment it is
written, and its passing tells you nothing.

## Adding one

1. Reproduce the defect deterministically. If it cannot be reproduced, it cannot
   be regression-tested, and that fact is itself a finding worth recording.
2. Add the minimal fixture that fails on the current code.
3. Name the file after the incident or defect, not after the module.
4. Reference the incident report or issue in the test's docstring, including
   what was observed and why it mattered.
5. Fix the defect. The test now passes for a reason.

## Rules

- One test per real failure. Not per module, and not per hypothetical.
- Never delete a regression test because it has "been fixed". That is precisely
  when it starts earning its keep.
- Never fabricate market data for a fixture. If reproduction needs data that
  does not exist, say so instead of inventing it.
