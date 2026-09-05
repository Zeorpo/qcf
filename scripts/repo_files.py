"""Filename-safe enumeration of the files this project owns.

Shell word-splitting is the wrong way to move a file list between git and a
tool: a path containing a space becomes several arguments, and the tool silently
inspects nothing. This module is the single place that enumeration happens, so
that defect cannot be reintroduced in one caller and not another.

Enumeration is NUL-delimited (``git ls-files -z``) and every path is handed to
subprocesses as an element of an argument array. No filename is ever
interpolated into a shell string.

Scope
    "Files this project owns" means git's view of the working tree: tracked
    files, plus untracked files that are not ignored. Untracked-but-not-ignored
    files are included deliberately — a newly written module that has not been
    staged yet is still first-party code, and a check that skipped it would go
    green on exactly the code most likely to be wrong.

    Outside a git checkout, enumeration falls back to a filesystem walk that
    prunes generated trees and virtual environments. That fallback cannot know
    what is ignored, so callers that treat it as equivalent should say so.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Final

__all__ = [
    "GENERATED_DIRECTORY_NAMES",
    "RepoFileError",
    "enumerate_project_files",
    "git_is_available",
    "run_git",
]

#: Directories that never contain first-party source.
#:
#: This list prunes *untracked* trees only. Anything git tracks is always
#: enumerated, so a name collision here can never hide first-party code that has
#: been committed.
GENERATED_DIRECTORY_NAMES: Final[frozenset[str]] = frozenset(
    {
        ".git",
        ".hypothesis",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        "__pycache__",
        "htmlcov",
        "build",
        "dist",
        "node_modules",
    }
)

_GIT_TIMEOUT: Final = 60


class RepoFileError(RuntimeError):
    """Enumeration failed.

    Raised rather than returning an empty list, because "no files" and "I could
    not find out which files" must never produce the same result: the first is a
    clean check, the second is an unperformed one.
    """


def run_git(root: Path, args: Sequence[str]) -> str:
    """Run a git command in ``root`` and return stdout.

    Args:
        root: Repository working tree.
        args: Arguments after ``git``, as an argument array. Never a shell
            string, so no element can be re-split or interpreted.

    Returns:
        Standard output, decoded as UTF-8 with surrogate escapes so that a path
        which is not valid UTF-8 survives the round trip.

    Raises:
        RepoFileError: If git is missing, times out, or exits non-zero.
    """
    command = ["git", "-C", str(root), *args]
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell, local only
            command,
            capture_output=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise RepoFileError("git is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise RepoFileError(f"git timed out after {_GIT_TIMEOUT}s: {' '.join(args)}") from exc
    except OSError as exc:
        raise RepoFileError(f"git could not be executed: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip().splitlines()
        reason = detail[-1] if detail else f"exit status {completed.returncode}"
        raise RepoFileError(f"git {' '.join(args)} failed: {reason}")
    return completed.stdout.decode("utf-8", "surrogateescape")


def git_is_available(root: Path) -> bool:
    """Return ``True`` if ``root`` is inside a usable git working tree."""
    try:
        return run_git(root, ["rev-parse", "--is-inside-work-tree"]).strip() == "true"
    except RepoFileError:
        return False


def _walk_fallback(root: Path) -> Iterator[Path]:
    """Yield files under ``root``, pruning generated trees and environments.

    A directory holding ``pyvenv.cfg`` is a virtual environment and is pruned.
    This is a *fallback* only: when git is available, tracked files are
    enumerated from git and this pruning cannot hide them.
    """
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except OSError as exc:
            raise RepoFileError(f"cannot read directory {current}: {exc}") from exc
        for entry in entries:
            if entry.is_symlink():
                # Never follow a symlink: it can leave the tree entirely, and a
                # link cycle would not terminate.
                continue
            if entry.is_dir():
                if entry.name in GENERATED_DIRECTORY_NAMES:
                    continue
                if (entry / "pyvenv.cfg").is_file():
                    continue
                stack.append(entry)
            elif entry.is_file():
                yield entry


def enumerate_project_files(root: Path, *, include_untracked: bool = True) -> list[Path]:
    """Return the project-owned files under ``root``, as absolute paths.

    Args:
        root: Directory to enumerate.
        include_untracked: Also return untracked files that git does not ignore.
            Defaults to ``True`` so that a newly written, unstaged module is
            still checked.

    Returns:
        Sorted absolute paths. Deduplicated: git can list a path more than once.

    Raises:
        RepoFileError: If enumeration fails. Never returns an empty list to
            signal failure.
    """
    root = root.resolve()
    if git_is_available(root):
        args = ["ls-files", "-z", "--cached"]
        if include_untracked:
            args += ["--others", "--exclude-standard"]
        raw = run_git(root, args)
        names = [name for name in raw.split("\0") if name]
        paths = {root / name for name in names}
    else:
        paths = set(_walk_fallback(root))
    # A tracked path can be absent from disk (deleted but not staged); the
    # scanner would report that as an error, so drop it here deliberately.
    return sorted(path for path in paths if path.is_file())
