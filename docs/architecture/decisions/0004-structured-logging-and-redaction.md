# ADR-0004: structlog, UTC timestamps, and centralised redaction

- **Status:** Accepted
- **Date:** 2026-09-03
- **Stage:** 00

## Context

QCF's logs are not diagnostics; they are evidence. Later stages assemble
incident bundles from them, and those bundles are the record used to decide
whether a loss was expected market behaviour or a defect. That imposes two
requirements ordinary application logging does not have.

They must be machine-readable, because a bundle is queried and compared, not
read line by line.

They must not contain secrets. An incident bundle carrying a credential is a
security incident in its own right, and bundles are precisely the artefacts most
likely to be copied into a report or attached to a message.

A redaction convention applied at each call site fails the moment someone
forgets, and the failure is silent.

## Decision

Use structlog with a fixed processor chain: context merging, level, ISO-8601 UTC
timestamp, **redaction**, stack and exception rendering, then a renderer
(`ConsoleRenderer` for humans, `JSONRenderer` for machines).

Redaction is a processor, so every event passes through it regardless of how it
was logged. A key is sensitive if its normalised form — lower-cased with
separators removed — contains any of `password`, `secret`, `token`, `apikey`,
`credential`, `authorization`, `cookie`, or `accountid`. Normalisation means
`API-KEY`, `api_key`, and `apiKey` are all caught. A sensitive key's entire
value is replaced, however deeply nested, and the input is never mutated.

Logs are emitted through structlog's print factory rather than the standard
library's handler chain, which makes reconfiguration idempotent and lets tests
capture output deterministically by passing a stream.

Timestamps are UTC without exception.

## Alternatives considered

**Standard-library logging with a JSON formatter.** Rejected for Stage 00.
Handler management is global and additive, so a second `basicConfig` silently
duplicates every line — a real hazard for a system that will run under a
supervisor and be restarted. A stdlib bridge can be added later if an operator
needs one.

**Redaction at call sites.** Rejected: it depends on being remembered, and its
failure mode is silent.

**Redaction by value pattern rather than key.** Rejected as the primary
mechanism. Detecting secrets by shape produces both misses and false positives
on ordinary numeric data, whereas key names are declared by the code that logs
them. `detect-secrets` covers the value-shaped case at commit and in CI.

**Local timestamps.** Rejected. Local time is ambiguous across a daylight-saving
transition, and a system whose correctness depends on session boundaries cannot
afford an hour that occurs twice.

## Consequences

Over-redaction is possible: a key such as `token_count` would be redacted. That
direction is chosen deliberately — a redacted value that was harmless costs a
debugging round, while a leaked value cannot be un-leaked.

Console output carries no colour, because logs are routinely captured to files
and pasted into reports where ANSI escapes are noise.

The `qcf.core.logging` module shadows the standard library's `logging` by name.
Python 3's absolute imports make this unambiguous, and the name is fixed by the
approved layout; the Ruff rule is disabled for that file alone, with the
justification recorded in `pyproject.toml`.

## Verification

- `tests/unit/core/test_logging.py` asserts a placeholder credential never
  appears in rendered output, in either renderer, whether passed as an event
  field or bound into the run context.
- The same suite asserts nested and sequence traversal, non-mutation, and that
  reconfiguring does not duplicate output.
- `tests/property/test_fingerprint_properties.py` asserts non-mutation for
  arbitrary generated structures.
