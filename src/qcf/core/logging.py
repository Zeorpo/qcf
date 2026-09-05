"""Structured logging and centralised redaction.

QCF's logs are evidence. Later stages assemble incident bundles from them, and a
bundle that contains a credential is a security incident of its own, so
redaction belongs in the logging pipeline rather than at each call site. A
processor cannot be forgotten; a convention can.

Design notes
    Logs are emitted through structlog's own print factory rather than through
    the standard library's handler chain. Reconfiguration is therefore
    idempotent -- calling :func:`configure_logging` twice replaces the
    configuration instead of attaching a second handler that duplicates every
    line -- and tests can capture output deterministically by passing a stream.

    Timestamps are ISO-8601 in UTC. QCF holds every internal timestamp in UTC;
    conversion to ``America/New_York`` or ``America/Chicago`` is a presentation
    and policy concern for later stages, not a storage format.
"""

from __future__ import annotations

import logging as stdlib_logging
import re
import sys
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any, Final, Literal, TextIO

import structlog

__all__ = [
    "REDACTED",
    "SENSITIVE_KEY_TERMS",
    "ExceptionOutput",
    "bind_run_context",
    "clear_run_context",
    "configure_logging",
    "get_logger",
    "is_sensitive_key",
    "redact",
]

#: Replacement text substituted for the value of a sensitive key.
REDACTED: Final = "***REDACTED***"

#: Normalised terms that mark a key as sensitive.
#:
#: Matching is substring-based against a normalised key, so ``API-KEY``,
#: ``api_key``, and ``apiKey`` are all recognised. The list errs towards
#: over-redaction: a redacted value that was harmless costs a debugging round,
#: while a leaked value cannot be un-leaked.
SENSITIVE_KEY_TERMS: Final[frozenset[str]] = frozenset(
    {
        "password",
        "secret",
        "token",
        "apikey",
        "credential",
        "authorization",
        "cookie",
        "accountid",
    }
)

_NON_ALNUM: Final = re.compile(r"[^a-z0-9]+")

LogFormat = Literal["console", "json"]

#: How much of an exception reaches the log.
#:
#: ``"safe"`` (the default) emits the exception's type and, for a
#: :class:`~qcf.core.exceptions.QCFError`, its stable ``code`` -- and nothing
#: else. ``"full"`` emits the formatted traceback, which is useful in local
#: development and is **not** safe for text that may contain a secret.
ExceptionOutput = Literal["safe", "full"]


def _normalise_key(key: str) -> str:
    """Lower-case a key and drop separators so spellings collapse to one form."""
    return _NON_ALNUM.sub("", key.lower())


def is_sensitive_key(key: str) -> bool:
    """Return ``True`` if ``key`` names a value that must not be logged.

    Args:
        key: A mapping key, in any casing or separator style.

    Returns:
        ``True`` if the normalised key contains any term in
        :data:`SENSITIVE_KEY_TERMS`.
    """
    normalised = _normalise_key(key)
    return any(term in normalised for term in SENSITIVE_KEY_TERMS)


def redact(value: object) -> object:
    """Return a copy of ``value`` with sensitive entries replaced.

    Mappings are traversed recursively and a sensitive key's whole value is
    replaced, however deeply nested it is. Sequences are traversed; lists and
    tuples keep their kind. Sets are returned unchanged, because redaction is
    driven by keys and a set has none.

    The input is never mutated. Callers may safely redact a live configuration
    or context mapping.

    Args:
        value: Any object, typically a mapping destined for a log line.

    Returns:
        A new structure with sensitive values replaced by :data:`REDACTED`.
    """
    if isinstance(value, Mapping):
        return {
            key: (REDACTED if isinstance(key, str) and is_sensitive_key(key) else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, (str, bytes, bytearray)):
        return value
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, Sequence):
        return [redact(item) for item in value]
    return value


def _redaction_processor(
    logger: object,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> Mapping[str, Any]:
    """Redact every event before it reaches a renderer."""
    del logger, method_name
    redacted = redact(dict(event_dict))
    assert isinstance(redacted, dict)  # noqa: S101 - redact preserves mapping kind
    return redacted


def _extract_exception(event_dict: MutableMapping[str, Any]) -> BaseException | None:
    """Pull the exception out of an event, whichever way it was supplied."""
    exc_info = event_dict.pop("exc_info", None)
    if exc_info is None or exc_info is False:
        return None
    if isinstance(exc_info, BaseException):
        return exc_info
    if isinstance(exc_info, tuple):
        return exc_info[1] if len(exc_info) > 1 else None
    return sys.exc_info()[1]


def _safe_exception_processor(
    logger: object,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> Mapping[str, Any]:
    """Replace exception text with controlled metadata.

    ``logger`` and ``method_name`` are unused; the signature is fixed by
    structlog's processor protocol.

    Key-based redaction cannot help here: a traceback is a single string under a
    key that is not sensitive by name, so no key rule would ever inspect it, at
    any position in the processor chain. The only reliable fix is not to emit
    the text.

    Emits ``error_type`` always, and ``error_code`` when the exception is a
    :class:`~qcf.core.exceptions.QCFError`. Chained causes contribute nothing:
    only the outermost type and code are recorded, so a suppressed message
    cannot reappear as an underlying exception.
    """
    del logger, method_name
    exception = _extract_exception(event_dict)
    # Drop any traceback another processor may already have rendered.
    event_dict.pop("exception", None)
    event_dict.pop("exc_info_", None)
    if exception is not None:
        event_dict["error_type"] = type(exception).__name__
        code = getattr(type(exception), "code", None)
        if isinstance(code, str):
            event_dict["error_code"] = code
    return event_dict


def configure_logging(  # noqa: PLR0913 - keyword-only knobs, each independent
    *,
    level: str = "INFO",
    fmt: LogFormat = "console",
    stream: TextIO | None = None,
    version: str | None = None,
    mode: str | None = None,
    exception_output: ExceptionOutput = "safe",
) -> None:
    """Configure structlog for this process.

    Safe to call more than once: each call replaces the configuration rather
    than adding to it, so no line is ever emitted twice.

    Args:
        level: Minimum level name, for example ``"INFO"``.
        fmt: ``"console"`` for human-readable output, ``"json"`` for machine
            output.
        stream: Destination stream. Defaults to standard output.
        version: Application version to bind into the run context.
        mode: Operating mode to bind into the run context.
        exception_output: ``"safe"`` (default) emits only an exception's type
            and code; ``"full"`` emits the formatted traceback and must not be
            used where messages may carry sensitive text.

    Raises:
        ValueError: If ``level`` is not a known level name.
    """
    level_map = stdlib_logging.getLevelNamesMapping()
    key = level.upper()
    if key not in level_map:
        raise ValueError(f"unknown log level {level!r}; expected one of {sorted(level_map)}")

    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer(sort_keys=True)
        if fmt == "json"
        # Colour is disabled deliberately: log output is routinely captured to
        # files and pasted into reports, where ANSI escapes are noise.
        else structlog.dev.ConsoleRenderer(colors=False)
    )

    exception_processors: list[structlog.typing.Processor] = (
        [_safe_exception_processor]
        if exception_output == "safe"
        else [structlog.processors.StackInfoRenderer(), structlog.processors.format_exc_info]
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            *exception_processors,
            # Redaction runs last so it also covers anything the exception
            # processors added. Note that it is key-based: see the module
            # docstring for what that does and does not guarantee.
            _redaction_processor,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level_map[key]),
        logger_factory=structlog.PrintLoggerFactory(stream),
        cache_logger_on_first_use=False,
    )

    context: dict[str, object] = {}
    if version is not None:
        context["version"] = version
    if mode is not None:
        context["mode"] = mode
    if context:
        bind_run_context(**context)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound logger, optionally named after the calling module."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]


def bind_run_context(**values: object) -> None:
    """Bind values into the context attached to every subsequent log line."""
    structlog.contextvars.bind_contextvars(**values)


def clear_run_context() -> None:
    """Clear the bound run context. Tests call this to stay independent."""
    structlog.contextvars.clear_contextvars()
