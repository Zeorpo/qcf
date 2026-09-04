---
name: Bug report
about: Something behaves differently from what the code or documentation states
labels: bug
---

## What happened

<!-- Observed behaviour. Paste exact output, including the full traceback. -->

## What was expected

<!-- And where that expectation comes from: a docstring, an ADR, a test, a stage
     document. "I assumed" is a valid answer and worth saying explicitly. -->

## Reproduction

```bash
# Exact commands, run through `uv run`.
```

- Deterministic? yes / no / intermittent
- First observed on commit:

## Environment

- Python version:
- `uv --version`:
- Operating system:

## Boundary check

- [ ] This report contains no credentials, account identifiers, or market data
- [ ] `uv run python scripts/check_project_boundary.py` output is included if relevant

## Impact

<!-- Could this change a research result, or is it a usability problem? A defect
     that silently alters a number is far more serious than one that crashes. -->
