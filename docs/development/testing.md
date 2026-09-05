# Testing and validation

## Categories

| Directory | Purpose |
| --- | --- |
| `tests/unit/` | One module's behaviour, including its failure modes |
| `tests/integration/` | Components together, and the installed package rather than the source tree |
| `tests/property/` | Invariants over generated inputs, via Hypothesis |
| `tests/contract/` | Project boundaries: no live mode, no broker client, no tracked data |
| `tests/regression/` | One test per real defect or incident. Empty until there is one. |

`tests/regression/` is deliberately empty. A regression test invented before a
defect exists tests an imagined failure, and its passing means nothing.

## Standards

Every test must be:

- **deterministic** — no wall-clock dependence, no unseeded randomness, no
  dependence on execution order. Hypothesis runs derandomised.
- **offline** — no network, ever.
- **independent of market data** — no dataset, and no fabricated price rows.
- **free of real credentials** — placeholders only, obviously marked.
- **meaningful** — asserting a real property, not that a function returned
  without raising.

A failing test is fixed by fixing the code, or by correcting an assertion that
is demonstrably wrong. Never by loosening it.

## The full validation sequence

Run all of it before committing. This is the sequence a stage report must record
with its exact observed output.

```bash
uv sync --all-groups --frozen            # locked environment; fails if the lock is stale
uv run ruff format --check .             # formatting
uv run ruff check .                      # linting
uv run mypy src tests scripts            # strict typing for src/qcf
uv run pytest                            # tests, branch coverage, 90% gate
uv run python scripts/check_project_boundary.py --strict
uv run detect-secrets scan --baseline .secrets.baseline
git status --short                       # nothing unexpected staged or left behind
git diff --check                         # no whitespace damage
```

## Coverage

Branch coverage, with a 90% floor configured in `pyproject.toml`. The floor is a
minimum, not a target, and code is never excluded from measurement to reach it.
Exclusions are limited to `TYPE_CHECKING` blocks, `@overload` stubs, and
explicitly marked unreachable branches.

Report **statements and branches separately**. With `branch = true`,
coverage.py's headline percentage is a *combined* figure, not branch-only;
describing it as branch coverage overstates it.

Coverage must not depend on filesystem history. A first run in a clean checkout
and a second run in the same checkout must produce the same number — an earlier
version measured differently because a code path executed only once a cache
directory happened to exist. Tests build the trees they need.

## Writing a property test

Property tests state invariants rather than examples. Hypothesis then searches
for a counterexample, which is the part a hand-written example cannot do.

The invariants asserted today: canonicalisation is idempotent; mapping key order
does not change a fingerprint; sequence order does; changing a value changes the
fingerprint; redaction never mutates its input; and prohibited `UNKNOWN`
coercions always fail regardless of the operand.
