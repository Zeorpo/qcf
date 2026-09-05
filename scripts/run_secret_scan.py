"""Run detect-secrets over every project-owned file, safely.

This exists because the previous CI invocation was

    detect-secrets-hook --baseline .secrets.baseline $(git ls-files)

which word-splits on whitespace. A tracked path containing a space became two
arguments, neither of which existed, and the step exited zero having scanned
nothing. A secret-detection control that silently declines to run is worse than
none, because it reports green.

Guarantees
    Every path reaches the scanner as exactly one argument, whatever it
    contains: spaces, tabs, newlines, non-ASCII, or a leading dash. Paths are
    passed after ``--`` so a name beginning with a dash is a filename and not an
    option — without it argparse rejects the run outright.

    Enumeration failure, scanner startup failure, and timeouts are reported as
    *tool errors* with a distinct exit status, never as a clean scan. The
    baseline is only ever read.

Exit status
    ``0`` no findings · ``1`` findings · ``2`` the scan could not be performed.

Findings are reported as a count and the files involved. Detected values are
never printed: this output goes to CI logs, which are more widely readable than
the repository.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

# Runnable as `python scripts/run_secret_scan.py` and importable as
# `scripts.run_secret_scan`: putting the repository root on the path makes the
# package name resolve identically either way.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.repo_files import RepoFileError, enumerate_project_files  # noqa: E402

__all__ = ["ScanOutcome", "batch_paths", "main", "scan"]

#: Bytes of filename payload per scanner invocation.
#:
#: `getconf ARG_MAX` is 2 MiB on the CI runner; this leaves three orders of
#: magnitude of headroom for the environment block and the fixed arguments,
#: which is the part that is awkward to measure and easy to get wrong.
MAX_BATCH_BYTES: Final = 100_000

_SCAN_TIMEOUT: Final = 300

#: argparse exits 2 on a usage error. That is a tool failure, not a finding.
_ARGPARSE_USAGE_ERROR: Final = 2

EXIT_CLEAN: Final = 0
EXIT_FINDINGS: Final = 1
EXIT_ERROR: Final = 2


@dataclass(frozen=True)
class ScanOutcome:
    """What a scan established."""

    status: int
    scanned: int
    findings: tuple[str, ...] = ()
    error: str | None = None


def batch_paths(paths: Sequence[Path], max_bytes: int = MAX_BATCH_BYTES) -> Iterator[list[Path]]:
    """Split ``paths`` into batches bounded by encoded filename size.

    Every path is emitted exactly once. A single path longer than ``max_bytes``
    still gets its own batch rather than being dropped: the operating system,
    not this function, is the right place for that limit to be enforced, and
    silently skipping a file would reintroduce the defect this module exists to
    fix.
    """
    batch: list[Path] = []
    size = 0
    for path in paths:
        encoded = len(str(path).encode("utf-8", "surrogateescape")) + 1
        if batch and size + encoded > max_bytes:
            yield batch
            batch, size = [], 0
        batch.append(path)
        size += encoded
    if batch:
        yield batch


def _invoke(baseline: Path, batch: Sequence[Path], root: Path) -> tuple[int, str]:
    """Run the scanner over one batch. Returns (returncode, stderr)."""
    command = [
        sys.executable,
        "-m",
        "detect_secrets.pre_commit_hook",
        "--baseline",
        str(baseline),
        "--",
        *[str(path) for path in batch],
    ]
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            command,
            capture_output=True,
            check=False,
            cwd=root,
            timeout=_SCAN_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise RepoFileError(f"secret scanner could not be started: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RepoFileError(f"secret scanner timed out after {_SCAN_TIMEOUT}s") from exc
    except OSError as exc:
        raise RepoFileError(f"secret scanner could not be executed: {exc}") from exc
    return completed.returncode, completed.stderr.decode("utf-8", "replace")


def scan(  # noqa: PLR0911 - each return is a distinct, documented outcome
    root: Path, baseline: Path, *, include_untracked: bool = True
) -> ScanOutcome:
    """Scan every project-owned file under ``root`` against ``baseline``.

    Returns:
        A :class:`ScanOutcome`. ``status`` is one of :data:`EXIT_CLEAN`,
        :data:`EXIT_FINDINGS`, or :data:`EXIT_ERROR`; the last is used whenever
        the scan could not be completed, so that an unperformed check can never
        be mistaken for a passing one.
    """
    if not baseline.is_file():
        return ScanOutcome(EXIT_ERROR, 0, error=f"baseline not found: {baseline}")
    try:
        paths = enumerate_project_files(root, include_untracked=include_untracked)
    except RepoFileError as exc:
        return ScanOutcome(EXIT_ERROR, 0, error=str(exc))

    if not paths:
        # An empty repository is a legitimate clean result, not an error.
        return ScanOutcome(EXIT_CLEAN, 0)

    findings: list[str] = []
    for batch in batch_paths(paths):
        try:
            code, stderr = _invoke(baseline, batch, root)
        except RepoFileError as exc:
            return ScanOutcome(EXIT_ERROR, len(paths), error=str(exc))
        if code == 0:
            continue
        # detect-secrets exits 1 (and 123 via its hook entry point) for
        # findings. argparse exits 2 for a usage error, which is a tool error
        # and must not be reported as "found secrets".
        if code == _ARGPARSE_USAGE_ERROR and "unrecognized arguments" in stderr:
            return ScanOutcome(
                EXIT_ERROR,
                len(paths),
                error=f"scanner rejected its arguments: {stderr.strip().splitlines()[-1]}",
            )
        # A batch only tells us "something in here". Re-scan it one file at a
        # time so the report names the files that actually carry findings;
        # listing a clean file as a finding would be its own false alarm. This
        # costs an extra pass only on the failure path.
        for path in batch:
            try:
                single_code, single_stderr = _invoke(baseline, [path], root)
            except RepoFileError as exc:
                return ScanOutcome(EXIT_ERROR, len(paths), error=str(exc))
            if single_code == _ARGPARSE_USAGE_ERROR and "unrecognized arguments" in single_stderr:
                return ScanOutcome(
                    EXIT_ERROR,
                    len(paths),
                    error=f"scanner rejected {path.name!r}",
                )
            if single_code != 0:
                findings.append(str(path.relative_to(root)))

    if findings:
        return ScanOutcome(EXIT_FINDINGS, len(paths), findings=tuple(sorted(set(findings))))
    return ScanOutcome(EXIT_CLEAN, len(paths))


def main(argv: list[str] | None = None) -> int:
    """Scan the repository. Returns a process exit status."""
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    baseline = root / ".secrets.baseline"

    outcome = scan(root, baseline)

    if outcome.status == EXIT_ERROR:
        print(f"SECRET SCAN COULD NOT RUN: {outcome.error}")
        print("Treating this as a failure: an unperformed check is not a passing one.")
        return EXIT_ERROR
    if outcome.status == EXIT_FINDINGS:
        print(f"SECRET SCAN FAILED: {len(outcome.findings)} file(s) carry new findings.")
        print("Detected values are deliberately not printed. Run locally to inspect:")
        print("  uv run detect-secrets-hook --baseline .secrets.baseline -- <file>")
        for name in outcome.findings:
            print(f"  - {name}")
        return EXIT_FINDINGS
    print(f"Secret scan passed: {outcome.scanned} file(s), no new findings.")
    return EXIT_CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
