# ADR-0009: Configuration records the effective path context

- **Status:** Accepted
- **Date:** 2026-09-04
- **Stage:** 00 (correction pass 00-C)

## Context

`resolved_data_root` documented itself as returning an absolute path, and did
not. With a relative `base_path` it returned the base joined to the child —
still relative, still interpreted against whatever the working directory
happened to be:

```text
AppConfig.load(base_path=Path("relative-root")).resolved_data_root
  -> relative-root/data        is_absolute() = False
```

Worse than the broken docstring: the configuration **fingerprint was identical**
regardless of where the process ran. One recorded identity could denote two
different directories on the same machine. For a system whose reproducibility
argument rests on fingerprints describing what produced a result, that is the
fingerprint failing at its one job.

The cause was resolving lazily. Each property call re-read `Path.cwd()`, so a
configuration's meaning drifted with the process while its identity stayed
still.

## Decision

Resolve the base **once**, when the configuration is validated, into a new
field `effective_base_path`:

| `base_path` | `effective_base_path` |
| --- | --- |
| omitted | the working directory at construction |
| relative | that same working directory, joined with it |
| absolute | itself |

Normalisation is lexical (`os.path.normpath`): dot segments collapse, no
filesystem access, **symlinks are not resolved**. Resolving them would record
a link's target rather than the location the operator configured, and would
differ across machines that lay out links differently.

Child paths resolve against `effective_base_path` and never consult the working
directory, so they are absolute and do not change if the process chdir's later.
Directories are not required to exist.

`effective_base_path` is a model field, so it appears in the dump and in the
fingerprint, and an explicitly supplied value is honoured on reload.

## Alternatives considered

**Reject a relative `base_path`.** Consistent with the project's fail-loudly
posture, and tempting. Rejected because a relative base is a reasonable thing to
write in a config file, and anchoring it at construction gives an unambiguous
meaning without refusing useful input.

**`Path.resolve()`.** Rejected: it follows symlinks (see above) and, in strict
mode, would require output directories to exist before a run could be
configured.

**Keep resolution lazy and only fix the docstring.** Rejected outright. It
documents the drift instead of removing it and leaves the fingerprint ambiguous.

## Consequences

**Configuration fingerprints are now machine-specific whenever paths differ
between machines.** This is intended: the fingerprint answers "what produced
this result", and the answer includes where the data was read from. It follows
that two machines producing the same fingerprint is evidence about one machine's
runs, not a cross-machine equivalence claim. **No such cross-machine claim is
made here.** A semantic, path-independent identity — if a later stage wants one
for comparing runs across machines — is a separate contract that would need its
own decision record.

A configuration dumped and reloaded on the same machine resolves identically.
Reloaded elsewhere, `effective_base_path` carries the original machine's path;
callers wanting re-anchoring should omit it and let it re-derive.

## Verification

- `tests/unit/core/test_config.py` asserts absoluteness for omitted, relative
  and absolute bases; stability across `chdir`; dot-segment collapsing;
  non-existent targets; and dump/reload retention.
- The same suite asserts the fingerprint changes when the effective base
  changes, and is stable when only the working directory does.
