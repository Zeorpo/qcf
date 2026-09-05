# Stage 00-C — bounded software foundation corrections

## 1. Outcome

**LOCAL CORRECTIONS VERIFIED.**

Six corrections applied, covering nine of the thirteen findings from the Stage
00-R review. Every corrected defect has before/after evidence: the smallest
relevant test fails against the original implementation and passes against the
correction. Four findings are **deferred** as outside this pass's authorisation
and remain open.

This is a **local patch only**. Nothing was committed, pushed, or published; no
pull request, monitoring job, or repository setting was touched. Remote CI for
these changes is **NOT RUN**.

## 2. Starting revision and changed files

| Item | Value |
| --- | --- |
| Starting commit | `3941e61301481b93eadcbd4a13fbc3ea57f1aaa9` |
| Base | `bd2586223b7542ee46924a0c224168777fbccb6e` |
| Branch | `claude/new-session-19lczd` (unchanged, no new commit) |
| Final commit | **none — the work is uncommitted by instruction** |
| Patch digest | recorded in the external handoff manifest — see below |

**The patch digest is deliberately not printed here (finding CR-01).** The
earlier version of this table carried a digest defined as SHA-256 over
`git diff HEAD` concatenated with the contents of each untracked file in sorted
order. This document is one of those untracked files, so its own bytes were part
of the digest's input while the digest sat inside it. That is circular: no value
written here can ever be recomputed from the definition given here, and the
recorded value could not be reproduced by any reading of it.

The authoritative digest of a patch is recorded in the external handoff manifest,
which is generated *after* the patch is exported and is not itself included in
the patch it describes. A manifest is likewise never required to contain its own
digest. Four kinds of hash are kept distinct throughout: source-tree manifest
digests, patch-file digests, artifact-manifest digests, and Git object IDs.

**Modified (21):** `.github/pull_request_template.md` · `.github/workflows/ci.yml` ·
`.pre-commit-config.yaml` · `README.md` · `SECURITY.md` ·
`docs/architecture/decisions/0004-structured-logging-and-redaction.md` ·
`docs/architecture/decisions/README.md` · `docs/architecture/target-layout.md` ·
`docs/development/environment.md` · `docs/development/testing.md` ·
`docs/project-state.md` · `scripts/check_project_boundary.py` ·
`src/qcf/core/config.py` · `src/qcf/core/exceptions.py` ·
`src/qcf/core/fingerprint.py` · `src/qcf/core/logging.py` ·
`tests/contract/test_project_boundary.py` ·
`tests/property/test_fingerprint_properties.py` · `tests/unit/core/test_config.py` ·
`tests/unit/core/test_fingerprint.py` · `tests/unit/core/test_logging.py`

**Added (8):** `docs/architecture/decisions/0008-canonical-input-contract.md` ·
`docs/architecture/decisions/0009-effective-path-context.md` ·
`scripts/__init__.py` · `scripts/repo_files.py` · `scripts/run_secret_scan.py` ·
`tests/contract/test_repo_files.py` · `tests/contract/test_secret_scan.py` ·
this report

## 3. Self-review disclosure and independent-review status

> **The Stage 00-R review was a SELF-REVIEW.** It was performed by the same
> agent session that implemented Stage 00, and it says so. It does **not**
> satisfy the independent-review gate.
>
> These corrections were made by that same session. A self-review followed by a
> self-correction establishes that specific reproduced defects are fixed. It
> establishes nothing about defects neither pass was capable of seeing.

**Independent review status: NOT PERFORMED.** A fresh review is required, and
should examine both these corrections and the four deferred findings.

## 4. Findings register

Reconstructed from the complete Stage 00-R report, which this session retained.
All thirteen findings are enumerated below with their original identifiers; none
is invented and none is silently marked closed.

| ID | Reported defect | Status | Correction |
| --- | --- | --- | --- |
| **R-01** | Ordinary mappings could impersonate canonical envelopes; a source comment claimed they could not | **CORRECTED** | E — structural key escaping (ADR-0008) |
| **R-02** | `resolved_*_root` returned a relative path against a docstring promising absolute | **CORRECTED** | D — base anchored at construction (ADR-0009) |
| **R-03** | `ConfigurationError` echoed rejected input values | **CORRECTED** | B — sanitised diagnostics, detached context |
| **R-04** | Exception text never redacted; reordering processors does not fix it | **CORRECTED** | C — `exception_output="safe"` contract |
| **R-05** | CI secret scan silently missed paths containing spaces | **CORRECTED** | A — `scripts/run_secret_scan.py` |
| **R-06** | Boundary checker traversed non-standard virtualenv directories | **CORRECTED** | F — git-aware enumeration |
| **R-07** | A SKIPPED boundary check did not fail the run | **CORRECTED** | F — `--strict`, used in CI and pre-commit |
| **R-08** | Coverage not reproducible from a clean checkout; mislabelled as branch-only | **CORRECTED** | F — cause removed; metrics now reported separately |
| **R-11** | Non-UTF-8 YAML escaped as `UnicodeDecodeError`, outside the documented contract | **CORRECTED** | B — wrapped as `ConfigurationError` |
| **R-09** | sdist `include` patterns unanchored; ship more than declared | **DEFERRED** | Not authorised by this pass |
| **R-10** | Build backend outside the lock; reproducibility boundary undocumented | **DEFERRED** | Not authorised by this pass |
| **R-12** | Misspelled `QCF_*` environment variable silently ignored | **DEFERRED** | Not authorised by this pass |
| **R-13** | Duplicate YAML keys silently last-wins (hardening, not a requirement violation) | **DEFERRED** | Not authorised by this pass |

The four deferred items are outside corrections A–F, which the task authorised
by name. Widening the patch to cover them would have been the scope creep this
pass was told to avoid; each remains open and is listed in
`docs/project-state.md` so it cannot be lost.

**Register status: COMPLETE.** The full 00-R report was available, so no finding
is unknown.

## 5. Corrections, with before/after evidence

### Correction A — filename-safe secret scanning (R-05)

**Before**, the shipped CI command, reproduced against the real scanner in a
temporary repository containing a fabricated key in `my config file.py`:

```text
detect-secrets-hook --baseline .secrets.baseline $(git ls-files)
  exit=0   findings=0        <- the secret was not scanned at all
```

**After**, via `scripts/run_secret_scan.py`:

```text
SECRET SCAN FAILED: 1 file(s) carry new findings.
  - my config file.py
  exit=1
```

The runner enumerates NUL-delimited (`git ls-files -z`), passes paths as an
argument array after `--`, and batches by encoded size. `--` is required, not
decorative: without it argparse rejects a leading-dash filename as an unknown
option, which is a tool error and must not be reported as "no secrets".

Failure modes are distinguished by exit status: `0` clean, `1` findings, `2` the
scan could not run (missing baseline, enumeration failure, scanner startup
failure, timeout). Findings are attributed per file — an earlier draft blamed
every file in a failing batch, including clean ones, which is its own false
alarm. Detected values are never printed. The baseline is only read.

`test_the_old_shell_form_missed_what_the_runner_finds` reconstructs the old
command and asserts it returns 0, then asserts the runner finds the same secret,
so the regression is demonstrated rather than described.

### Correction B — safe configuration diagnostics (R-03, R-11)

**Before:** the rejected value appeared in the error through all three input
channels.

```text
explicit kwarg / QCF_ env var / YAML file  ->  marker echoed: True
  "... input_value='INERT-MARKER-9Q7', input_type=str]"
```

**After:** absent from `str()`, `repr()`, the structured details, and a
formatted traceback, through all three channels.

Errors are built from
`exc.errors(include_input=False, include_url=False, include_context=False)`,
verified against the locked pydantic 2.13.5 rather than assumed. That is not
sufficient on its own: for `extra_forbidden`, the error's `loc` **is the
caller's key name**, so an unrecognised field whose name is itself sensitive is
redacted, while an ordinary typo is still reported by name.

Two further channels were closed. YAML parse errors report position only — a
parser message quotes the offending source line, which is file content. And the
`ValidationError` is **detached**, not merely suppressed: `raise ... from None`
sets `__suppress_context__` but leaves `__context__` populated, so the raw
values stayed reachable by introspection and by any formatter that ignores the
flag. The sanitised error is raised outside the handler with `__context__`
cleared. A test asserts this, and it is what caught the distinction.

**Boundary, stated rather than glossed:** this is not memory erasure. Copies may
exist elsewhere, and a traceback formatter that dumps frame locals can still see
the value in the frame that produced it. The guarantee is about the exception
object.

### Correction C — end-to-end logging disclosure (R-04)

The review's hypothesis was that redaction preceding `format_exc_info` caused
the leak. **That hypothesis was tested and is insufficient**: moving redaction
last still leaked. Key-based redaction never inspects values, and `exception` is
not a sensitive key name, so processor order is irrelevant.

`configure_logging` now defaults to `exception_output="safe"`, emitting the
exception's type and, for a `QCFError`, its stable `code` — never the message or
traceback. Verified in both renderers:

| Case | Marker leaked |
| --- | --- |
| Plain exception | No |
| Chained exception (`raise ... from ...`) | No |
| `ConfigurationError` end-to-end | No |
| Nested sensitive keys and bound context | No |
| `exception_output="full"` (opt-in) | **Yes**, by design and documented |
| Free text in the event message | **Yes**, documented limit |

The last row is asserted by a test on purpose. Key-based redaction promises
nothing about arbitrary prose a caller interpolates, and ADR-0004 deliberately
rejected pattern-matching secrets as the primary mechanism. Pinning the limit
stops it being quietly overstated later.

### Correction D — stable absolute configuration paths (R-02)

**Before:** `AppConfig.load(base_path=Path("relative-root")).resolved_data_root`
returned `relative-root/data` — not absolute, and re-interpreted against the
working directory on every access while the fingerprint stayed constant.

**After:** the base is anchored once at validation into `effective_base_path`.
Omitted → construction-time cwd; relative → anchored to it; absolute →
unchanged. Normalisation is lexical, so dot segments collapse, targets need not
exist, and **symlinks are not resolved** (recording a link's target rather than
the configured path would surprise, and would differ across machines).

The fingerprint now includes the effective base, so two directories can no
longer share one recorded identity. **Consequence stated plainly:** fingerprints
become machine-specific where paths differ. That is intended — a fingerprint
answers "what produced this result" — and **no cross-machine equivalence is
claimed**. ADR-0009 records this.

### Correction E — unambiguous fingerprint input contract (R-01)

**Before:** `canonicalize(Decimal("1.25"))` and
`canonicalize({"__qcf_type__": "decimal", "value": "1.25"})` produced identical
bytes, for every recognised tag including UNKNOWN.

**After:** raw mapping keys using the reserved `__qcf_` prefix are escaped, so no
mapping can produce a bare `__qcf_type__` and an envelope is only ever produced
by a typed value. The transform is injective and tested as such.

**Distinguished from a hash collision:** the defect was identical *serialized
bytes*, so equal digests followed arithmetically. Encoding tests compare
`canonical_json` output, never manufacturing a digest collision as a stand-in.

**A retired assertion, explained.** The blanket idempotence property is
withdrawn by ADR-0008: it was what forced envelope pass-through, and
pass-through was what destroyed injectivity. Four unit tests asserting the old
pass-through contract were replaced, each removal documented in the test file
alongside its replacement. Idempotence was never the property that mattered.

**Compatibility.** Fingerprints change only for mappings with reserved-prefix
keys. None has ever been persisted — Stage 00 stores no run records, and
`AppConfig` has no such field — so configuration fingerprints are unchanged and
there is nothing to migrate. No compatibility shim was added; one would be a
second, weaker path for a value nothing has stored.

### Correction F — scan scope and hermetic coverage (R-06, R-07, R-08)

Scope is now git's view of the working tree — tracked plus untracked-not-ignored
— via `scripts/repo_files.py`. Untracked files are included deliberately: a
newly written module is first-party code, and skipping it would go green on
exactly the code most likely to be wrong. Outside a checkout, a pruned
filesystem walk is used; pruning applies to untracked trees only, so it can
never hide committed source.

```text
before:  1580 .py files scanned, 1558 of them third-party (98.6%)
after:     24 .py files scanned, 0 third-party
```

R-07: `--strict` makes a SKIPPED check fail, and CI and pre-commit both pass it.
Verified on a hermetic copy of the tree with no `.git`: exit 0 without the flag,
exit 1 with it.

R-08: the cold/warm difference is fixed **at its cause**, not papered over. The
old skip branch executed only when a cache directory already existed; that code
no longer exists. Cold and warm runs now produce identical coverage — see §7.

## 6. Contract changes and compatibility

| Contract | Change | Compatibility |
| --- | --- | --- |
| `canonicalize` | Raw input only; reserved keys escaped; format version 2 | Affects only mappings with `__qcf_`-prefixed keys. None persisted. |
| `AppConfig` | New `effective_base_path` field; resolved paths absolute and stable | Fingerprints now reflect path context and are machine-specific |
| `ConfigurationError` | Carries sanitised `details`; message never echoes input; context detached | Additive; existing construction still works |
| `QCFError` | New `code` class attribute | Additive |
| `configure_logging` | New `exception_output`, default `"safe"` | Default changes what is emitted for exceptions — intentionally |
| Boundary checker | `--strict`; git-aware scope | Additive flag; scope narrowed to first-party |

## 7. Commands, versions, and results

All through the locked environment; no global tool is cited.

### Python 3.12.3

```text
uv lock --check                                    exit=0   Resolved 42 packages
uv run ruff format --check .                       exit=0   69 files already formatted
uv run ruff check .                                exit=0   All checks passed!
uv run mypy src tests scripts                      exit=0   no issues in 27 source files
uv run pytest                                      exit=0   426 passed
uv run python scripts/check_project_boundary.py --strict
                                                   exit=0   11 passed, 0 failed, 0 skipped
uv run python scripts/run_secret_scan.py           exit=0   87 files, no new findings
git diff --check                                   exit=0
```

### Python 3.13.12

```text
uv sync --all-groups --frozen --python 3.13         exit=0   lock unchanged
uv run ruff format --check .                        exit=0   69 files already formatted
uv run ruff check .                                 exit=0   All checks passed!
uv run mypy src tests scripts                       exit=0   no issues in 27 source files
uv run pytest                                       exit=0   426 passed; 97.43%
uv run python scripts/check_project_boundary.py --strict
                                                    exit=0   11 passed, 0 failed, 0 skipped
uv run python scripts/run_secret_scan.py            exit=0   87 files, no new findings
```

Both supported interpreters were available; neither leg is INCOMPLETE, and both
report identical coverage.

### Coverage — statements and branches reported separately

With `branch = true`, coverage.py's headline figure is **combined**, not
branch-only. The Stage 00 report described it as branch coverage; that was
wrong, and is corrected here.

| Metric | Covered / total | Percent |
| --- | --- | --- |
| Statements | 890 / 912 | 97.59% |
| Branches | 287 / 296 | 96.96% (9 partial) |
| **Combined** | — | **97.43%** |

`src/qcf` is **100% statements and 100% branches on every module**, with zero
partial branches. All uncovered lines are in `scripts/`: tool-failure branches
and `__main__` guards. Nothing was excluded from measurement, and the 90%
threshold was not lowered. 426 tests, **0 skips, 0 xfails**.

### Cold vs warm

Run in a fresh isolated copy of the corrected tree, then again in the same
checkout:

```text
cache directories at start: 0
run 1 (cold: no cache directories)   426 passed   Total coverage: 97.43%
cache directories now: 1
run 2 (warm: caches present)         426 passed   Total coverage: 97.43%
```

**Identical**, and equal to the figure measured in the working checkout. Before
this pass the same comparison produced 98.17% cold and 98.40% warm.

A correction to the Stage 00-R review is owed here. It stated that "CI, which
always starts clean, measures 98.17%". **That was an unverified extrapolation
and it was wrong.** The actual CI log for `3941e61` reports 98.40%, because the
workflow runs `ruff` and `mypy` before `pytest` and those steps create the cache
directories that the skip branch depended on. The underlying non-determinism was
real; the inference about CI was not. The 00-R report is left as written, with
this dated correction recorded rather than edited into it.

### Packaging, rebuilt and installed clean

```text
uv build                                  -> qcf-0.0.0.tar.gz, qcf-0.0.0-py3-none-any.whl
wheel contents                            -> qcf/** + py.typed + dist-info only
pip install <wheel> in a fresh venv outside any checkout:
  qcf.__version__          0.0.0
  module path              .../site-packages/qcf
  leaks the source tree?   False
  resolve_git_commit()     UNKNOWN          (correct: a wheel has no git metadata)
  AppConfig().mode         DISABLED
  resolved path absolute   True             (Correction D holds in the installed package)
  CANONICAL_FORMAT_VERSION 2                (Correction E ships)
```

## 8. Local validation versus remote CI

**Remote CI: NOT RUN for these corrections.** No push was authorised. The green
run recorded against `3941e61` predates every change in this patch and is **not
evidence for it**; citing it would be exactly the reuse the task forbids.

The distinction that matters: local gates pass, and remote CI has not been
asked. Neither is a substitute for the other — CI runs on a clean runner with
different caching, and the workflow itself was modified by this patch.

## 9. Baseline, lock, and security limitations

| Item | State |
| --- | --- |
| `uv.lock` SHA-256 | `1b1e3437e9d73b9b62222ea3d6b47f7d864bd2dcad2ac438f82be61424591714` — **unchanged**, recomputed from actual bytes |
| `.secrets.baseline` | `0f5e1cc51914ff1ce78e0efc3f8575f11b1343b8d94b5563a87d7417183b3daa` — **unchanged**; no finding was added or widened |
| Runtime dependencies | Unchanged. No dependency added, removed, or upgraded. |
| Toolchain | Unchanged. |

Limitations that remain, stated rather than implied:

- Redaction is key-based and does not sanitise free text in an event message.
- Exception sanitisation covers the exception object; it is not memory erasure,
  and a formatter dumping frame locals can still reach the value.
- Static deny-lists in the boundary checker are not a sandbox. They prove
  specific absences, not the absence of all capability.
- Configuration fingerprints are machine-specific where paths differ.
- Four review findings remain open (R-09, R-10, R-12, R-13).

## 10. Remaining blockers and the next review request

**Blocking Stage 01:** no independent review has been performed. The 00-R review
and these corrections come from the same session.

The bounded request for a fresh reviewer:

1. Verify each correction against its finding, from the patch rather than this
   report.
2. Attack the new contracts specifically: the escape transform's injectivity;
   whether any other channel echoes a rejected configuration value; whether the
   safe exception path can be bypassed; whether the enumeration can be made to
   miss first-party code.
3. Assess the four deferred findings and decide whether any blocks Stage 01.
4. Re-derive the coverage figures independently, cold and warm.

## 11. Changes by category

Reported separately, because "no files were created" in an earlier report was
ambiguous about temporary artefacts and automation.

**Source and repository changes (local, uncommitted):** 21 files modified, 8
added, as listed in §2. Nothing committed, pushed, tagged, or branched.

**Temporary files (outside the repository, in the session scratch directory):**
regression fixtures in throwaway git repositories; a copied tree for the
cold/warm comparison; a hermetic no-git tree built by a test; built
distributions. None is inside the repository and none is staged.

**Remote state:** unchanged. No commit, push, merge, PR edit, comment, review,
approval, label, or setting change. The PR remains open and draft at `3941e61`.

**Automation state:** unchanged **by this pass**. A pre-existing hourly
self-check-in from the earlier PR subscription remains active and was neither
created, modified, nor cancelled here. For completeness, and because an earlier
report folded this into a blanket no-change claim: that check-in *was* re-armed
and its interval lengthened during earlier turns, before this pass began.

**Fixtures:** every secret-shaped fixture is a fabricated value written only to
temporary directories. No real credential was created, used, or recorded, and no
fixture was added to the repository.
