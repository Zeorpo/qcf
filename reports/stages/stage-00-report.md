# Stage 00 implementation report

**Recommendation: PASS**, subject to independent adversarial review and to the
remote CI observation recorded below.

| Field | Value |
| --- | --- |
| Repository | `Zeorpo/qcf` (private) |
| Stage | 00 — Professional Repository Foundation |
| Starting commit | none — empty repository |
| Bootstrap commit | `bd2586223b7542ee46924a0c224168777fbccb6e` (`main`) |
| Working branch | `claude/new-session-19lczd` |
| Final commit | `PLACEHOLDER_FINAL_SHA` |
| Pull request | [Zeorpo/qcf#1](https://github.com/Zeorpo/qcf/pull/1) (draft) |

## Observed starting state

Re-verified immediately before any file was written:

```text
$ git remote get-url origin
https://github.com/Zeorpo/qcf
$ git symbolic-ref --short HEAD
claude/new-session-19lczd
$ git show-ref                    # local refs
(no output)
$ git ls-remote origin            # remote refs
(no output)
$ ls -A
.git
$ git status --porcelain --ignored
(no output)
$ python3.12 --version
Python 3.12.3
$ uv --version
uv 0.8.17
```

Private, zero commits, zero refs, no files, nothing to preserve. No stop
condition was triggered.

## Empty-repository bootstrap

`main` did not exist, so no pull request had a base branch to target. The
documented bootstrap exception was applied, and is recorded in
[ADR-0007](../../docs/architecture/decisions/0007-branching-and-bootstrap.md).

One commit, `chore: bootstrap QCF repository`, containing exactly four files:
`README.md`, `.gitignore`, `LICENSE_POLICY.md`, and
`docs/architecture/decisions/0000-adr-process.md`. It contains no package,
configuration, strategy, data, or execution code.

```text
$ git push origin HEAD:refs/heads/main
 * [new branch]      HEAD -> main
$ git ls-remote origin
bd2586223b7542ee46924a0c224168777fbccb6e	HEAD
bd2586223b7542ee46924a0c224168777fbccb6e	refs/heads/main
$ git symbolic-ref --short HEAD
claude/new-session-19lczd
```

No force-push occurred. The local branch was not renamed or left. `.gitignore`
is in the first commit deliberately: preventing data and credentials from being
tracked is a job it can only do if it precedes everything else.

A note on one observed message: the push emitted
`fatal: expected 'acknowledgments', received 'packfile'` followed by
`warning: push negotiation failed; proceeding anyway with push`. This is a
push-negotiation quirk of the environment's git proxy, not a failure — the ref
was created, as the `ls-remote` above confirms. It is recorded rather than
omitted because a reader reproducing this will see it too.

## Environment

| Item | Value |
| --- | --- |
| Interpreter | `/home/user/qcf/.venv/bin/python3` |
| Version | `3.12.3 (main, Mar  3 2026, 12:15:18) [GCC 13.3.0]` |
| Created from | `/usr/bin/python3.12` |
| uv | 0.8.17 |
| `uv.lock` SHA-256 | `1b1e3437e9d73b9b62222ea3d6b47f7d864bd2dcad2ac438f82be61424591714` |
| Packages locked | 42 |

The machine's default `python3` is 3.11.15 and was **not** used for any
validation. Globally installed Ruff 0.15.8, mypy 1.19.1, and pytest 9.0.2 exist
on this machine, are **not** the project toolchain, and are not cited anywhere in
this report. Every command below ran through `uv run`.

## Dependencies

Runtime, exactly as approved:

```text
pydantic==2.13.5   pydantic-settings==2.15.0   PyYAML==6.0.3   structlog==26.1.0
```

Development, exactly as approved:

```text
pytest==9.1.1        pytest-cov==7.1.0   hypothesis==6.167.1
ruff==0.16.6         mypy==2.3.1         pre-commit==4.6.2
types-PyYAML==6.0.12.20260815            detect-secrets==1.5.0
```

Nothing was added beyond the approved set and nothing was removed from it. No
numeric, dataframe, plotting, dashboard, broker, exchange, market-data, or
database dependency is declared.
`tests/contract/test_project_boundary.py::test_the_declared_dependency_set_matches_the_approved_list`
asserts this, so a future addition cannot pass silently.

## Decisions and deviations

| Item | Resolution |
| --- | --- |
| Branch name | `claude/new-session-19lczd` rather than `stage/00-...`, under the environment constraint approved by the owner. Recorded in ADR-0007. |
| Package scaffolding | `src/qcf/core` only. Later packages documented in `target-layout.md`, not stubbed. |
| `_envelope` dead branch | An unreachable `value is None` branch in `fingerprint.py` was removed rather than left uncovered or excluded from measurement. |
| `detect-secrets` verification form | `detect-secrets-hook --baseline ...` rather than `scan --baseline ...`. The scan form **rewrites** the baseline in place, so it cannot fail a build; the hook form verifies against the reviewed baseline and exits non-zero on a new finding. Documented in `testing.md` and used identically in CI. |
| Two secret-scan findings | A published NIST SHA-256 test vector and a fabricated git object id, both in test files. Inspected, confirmed not credentials, and marked with inline `pragma: allowlist secret` comments so the reason is visible at the site. The committed baseline therefore contains **zero** findings and no secret values. |
| Ruff `A005` on `qcf/core/logging.py` | Disabled for that file alone. The module name is fixed by the approved tree, and Python 3's absolute imports make the shadowing nominal. Justified inline in `pyproject.toml`. |
| Two deferred imports in the boundary checker | `# noqa: PLC0415` with reasons. The checker must still run and report a failure when the package is not installed, rather than failing to start. |
| `Any` in `AppConfig.load(**overrides)` | `# noqa: ANN401` with a reason: the values genuinely are arbitrary until pydantic validates them. |

## Changed files

75 files added since the bootstrap commit. Full list in the pull request diff.
By area: 9 package modules (`src/qcf`), 1 script, 9 test modules plus
`conftest.py`, 24 documentation files including 9 ADRs, 8 root configuration and
policy files, 5 `.github` files, 2 `config/` files, and the data, report, and
notebook skeletons.

## Requirements traceability

Every requirement in
[`../../docs/stages/stage-00-repository-foundation.md`](../../docs/stages/stage-00-repository-foundation.md)
(QCF-S00-001 through QCF-S00-026) is implemented and verified. That document was
written **before** implementation and was not revised to match what was built.

Two entries are worth flagging for the reviewer:

- **QCF-S00-015** (boundary checker) is verified by tests that build deliberate
  violations in temporary directories and assert the relevant check **fails**.
  A check only ever observed to pass has not been shown to be capable of
  failing.
- **QCF-S00-026** (no later-stage behaviour) is an absence. It is evidenced by
  the boundary checker, the contract tests, and the changed-file list — none of
  which can prove a negative on its own.

## Commands and observed results

All run from the locked environment.

```text
$ uv sync --all-groups --frozen
Audited 41 packages in 0.37ms

$ uv run ruff format --check .
60 files already formatted

$ uv run ruff check .
All checks passed!

$ uv run mypy src tests scripts
Success: no issues found in 22 source files

$ uv run python scripts/check_project_boundary.py
  [PASS] no live operating mode
  [PASS] no broker or network client imports
  [PASS] no real-order transmission path
  [PASS] no tracked .env file
  [PASS] no tracked market data
  [PASS] required files present
  [PASS] package imports
  [PASS] example configuration validates
  [PASS] internal timezone is UTC
  [PASS] product code terminology
  [PASS] documentation links resolve
11 passed, 0 failed, 0 skipped
Boundary check passed.

$ uv run detect-secrets-hook --baseline .secrets.baseline $(git ls-files)
(no output; exit 0)

$ git diff --check
(no output)
```

### Tests and coverage

```text
$ uv run pytest
305 passed

Name                                Stmts   Miss Branch BrPart  Cover
---------------------------------------------------------------------
scripts/check_project_boundary.py     232     10    110      4    96%
src/qcf/__init__.py                     2      0      0      0   100%
src/qcf/core/__init__.py                0      0      0      0   100%
src/qcf/core/config.py                 88      0     12      0   100%
src/qcf/core/enums.py                  29      0      0      0   100%
src/qcf/core/exceptions.py              8      0      0      0   100%
src/qcf/core/fingerprint.py            91      0     52      0   100%
src/qcf/core/logging.py                51      0     16      0   100%
src/qcf/core/unknown.py                83      0      8      0   100%
src/qcf/core/version.py                63      0     28      0   100%
---------------------------------------------------------------------
TOTAL                                 647     10    226      4    98%
Required test coverage of 90.0% reached. Total coverage: 98.40%
```

Branch coverage of `src/qcf` is 100% on every module. The 10 uncovered
statements are all in the boundary checker: subprocess failure handlers, two
`ImportError` fallbacks, and the `__main__` guard. Nothing was excluded from
measurement to reach the gate.

### Failed attempts, recorded

Included because a report that shows only the final green run conceals how it
was reached.

1. **Ruff, first run.** 44 findings, dominated by `PLC0415` (function-level
   imports in tests) and `ANN401`. Fixed by hoisting the imports and by
   replacing `Any` with `object` or `Callable[[], object]` where those are the
   true types — not by relaxing the rules.
2. **mypy, five errors.** Each was mypy correctly proving a property the test
   asserted at runtime: `UNKNOWN is not False` and
   `UNKNOWN_CANONICAL != "UNKNOWN"` were flagged as non-overlapping comparisons,
   and ordering operators on `object` were rejected outright. Each test was
   restructured to keep the runtime assertion meaningful, with the static
   rejection noted in a comment rather than silenced.
3. **Boundary checker, several runs.** Correctly failed on 12 missing required
   files and 3 dangling documentation links, which is the evidence that it does
   something. It then caught **this report**, whose limitations section names
   the reversed product code; the documented exemption marker was applied to
   that line.
4. **Secret scan, run twice.** Exit 1 the first time on two findings (a NIST
   test vector and a fabricated object id), and exit 1 again later after a
   refactor moved one `pragma` off the line carrying its token and introduced
   an inline `api_key` placeholder. Both rounds were inspected and resolved by
   placing the marker on the correct line; nothing was added to the baseline,
   which still contains zero findings.
5. **Remote CI, first run.** Failed on both matrix legs, before any gate ran,
   because of a self-inflicted environment guard in the workflow this pull
   request added. Diagnosed from the job log, fixed at the root, and both legs
   reproduced locally before re-pushing. Detailed above.
6. **Coverage, first full run.** 97.26%, with four uncovered spots. One was
   genuinely dead code and was deleted; three were untested public API
   (`get_field_value`, `clear_run_context`, and the `PackageNotFoundError`
   fallback) and received tests. Result 98.40%.

## Remote CI status

GitHub Actions **is** enabled on this private repository, which the Stage 00
inspection had listed as unverified.

**Run 1 — FAILURE**, and the fault was this pull request's own.
[Run 33837051171](https://github.com/Zeorpo/qcf/actions/runs/33837051171). Both
matrix legs failed at the same step, `Set up Python`, before any gate ran:

```text
Run uv python install 3.12
env:
  UV_PYTHON_DOWNLOADS: never
Python downloads are not allowed (`python-downloads = "never"`).
Change to `python-downloads = "manual"` to allow explicit installs.
##[error]Process completed with exit code 1.
```

Root cause: the workflow set `UV_PYTHON_DOWNLOADS: never` at job level, intending
to stop a silent download of an unintended interpreter, and then asked `uv` to
install the matrix interpreter. GitHub's `ubuntu-24.04` runner does not carry a
uv-managed 3.12 or 3.13 build, so the guard blocked exactly the install it was
meant to protect. The reasoning behind the guard was wrong as well as its
placement: what makes the interpreter trustworthy is that the matrix pins it
explicitly, not that it was already present on the runner.

Fix: drop the environment guard, and let `astral-sh/setup-uv` provision the
interpreter through its `python-version` input, which exports `UV_PYTHON` for
the whole job. The input was confirmed against the action's `action.yml` **at
the pinned SHA** rather than assumed. This also removes a step and keeps the
version declared in one place.

Before pushing the fix, both matrix legs were reproduced locally against the
real interpreters rather than only the 3.12 development environment:

```text
$ uv lock --check
Resolved 42 packages in 2ms

$ uv sync --all-groups --frozen --python /usr/bin/python3.13
$ uv run --python /usr/bin/python3.13 python -c "import sys; print(sys.version.split()[0])"
3.13.12
$ uv run --python /usr/bin/python3.13 ruff check .
All checks passed!
$ uv run --python /usr/bin/python3.13 mypy src tests scripts
Success: no issues found in 22 source files
$ uv run --python /usr/bin/python3.13 pytest
305 passed
Required test coverage of 90.0% reached. Total coverage: 98.40%
$ uv run --python /usr/bin/python3.13 python scripts/check_project_boundary.py
11 passed, 0 failed, 0 skipped
```

**Run 2** was triggered by the fix commit. Its result is recorded in the final
reporting update below; until it is green, this stage is not complete.

Actions are pinned to immutable commit SHAs resolved from the upstream
repositories with `git ls-remote`, not from memory:

| Action | Tag | SHA |
| --- | --- | --- |
| `actions/checkout` | v6.0.3 | `df4cb1c069e1874edd31b4311f1884172cec0e10` |
| `astral-sh/setup-uv` | v9.0.0 | `c771a70e6277c0a99b617c7a806ffedaca235ff9` |

## Security review

| Control | State |
| --- | --- |
| Live operating mode | Absent. No `LIVE` member; checker and contract tests enforce it. |
| Broker / prop-firm / exchange client | Absent as import and as dependency. |
| Network client inside `src/qcf` | Absent. AST import inspection enforces it. |
| Real-order path | Absent. AST function-name inspection enforces it. |
| Credentials, API keys, account identifiers | None present. `.env` is ignored and untracked; `.env.example` holds non-financial settings only. |
| Market data | None tracked. Verified by creating real files and asking git, not by reading ignore patterns. |
| Log redaction | A structlog processor, so it cannot be forgotten at a call site. Tested against a placeholder in both renderers, as an event field and as bound context. |
| Secret scanning | `detect-secrets` 1.5.0 pinned, reviewed baseline with zero findings, in pre-commit and CI. |
| CI privilege | `permissions: contents: read`; `persist-credentials: false`; no secrets referenced; no artefacts uploaded. |
| Advanced Security | Not assumed available. |

No security findings.

## Known limitations

1. **No trading system exists**, and no result has been produced or claimed. The
   vocabulary for later concepts exists as enum values; vocabulary is not
   behaviour.
2. **Stage 03 is blocked** pending authorised historical `6E` data. Fabricating
   sample history is prohibited.
3. **`Decimal(UNKNOWN)` raises `TypeError`, not `UnknownValueError`**, because
   `Decimal` inspects concrete types rather than calling a coercion protocol.
   The conversion remains impossible; only the exception type differs. Asserted
   by a test so it cannot change unnoticed.
4. **Layer-direction enforcement is by review, not by tooling.** The module
   graph is one package; an import-graph linter is deferred until there is a
   graph to check.
5. **The product-code terminology check is line-based.** It flags the reversed
   spelling `E6` <!-- qcf:allow-E6 --> and exempts the checker itself and test
   files, per the requirement not to flag prose that describes a prohibited
   concept. The same spelling inside a test file would not be caught. The
   exemption marker is required on the same line as the token, which this
   report demonstrates: the check caught this very paragraph on first run.
6. **The boundary checker's git-dependent checks report SKIP outside a
   checkout** rather than failing. They pass in CI, where a checkout always
   exists.
7. **Coverage is not correctness.** 98% branch coverage means the lines ran, not
   that the assertions were the right ones. That is what the adversarial review
   is for.

## Unresolved decisions

Recorded in [the ADR index](../../docs/architecture/decisions/README.md), none
decided implicitly: authoritative monetary representation (Stage 02B), dataframe
engine (Stage 03), continuous-futures adjustment (Stage 02B), external policy
encoding (Stage 01), strategy and model families (Stage 08+).

The security reporting contact remains `UNKNOWN` and no license is selected.
Both are the owner's to supply.

## Recommendation

**PASS** for Stage 00, conditional on the independent adversarial review
recording no unresolved blockers, and on the remote CI run completing green.

Next permitted stage: **Stage 01 — Governance and Versioned Policy Contracts**.
Do not begin it before that review.
