"""Package version and best-effort source revision.

A recorded result is only reproducible if the code that produced it can be
identified, so every run record carries a version and, where one can be
established, a commit. "Where one can be established" is doing real work here:
an installed wheel has no git metadata, and reporting a plausible-looking commit
in that situation would be worse than reporting nothing.

The commit is read directly from git's on-disk files. No subprocess is spawned,
so there is no command to inject into and nothing to go wrong if git is absent
from the image; no network is touched. Importing :mod:`qcf` never fails because
git metadata is unavailable -- resolution happens when it is asked for, and
returns :data:`~qcf.core.unknown.UNKNOWN` when it cannot succeed.
"""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version
from pathlib import Path
from typing import Final

from qcf.core.unknown import UNKNOWN, UnknownType

__all__ = ["__version__", "package_version", "resolve_git_commit"]

_DISTRIBUTION: Final = "qcf"

# Used only when the distribution metadata is unavailable, which happens when
# the source tree is on the path without having been installed.
_FALLBACK_VERSION: Final = "0.0.0"

# Accepts both SHA-1 and SHA-256 object formats.
_OBJECT_ID: Final = re.compile(r"\A(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def package_version() -> str:
    """Return the installed distribution version, or a fallback."""
    try:
        return _distribution_version(_DISTRIBUTION)
    except PackageNotFoundError:
        return _FALLBACK_VERSION


def _find_git_dir(start: Path) -> Path | None:
    """Walk upwards from ``start`` looking for a git directory."""
    for candidate in (start, *start.parents):
        entry = candidate / ".git"
        if entry.is_dir():
            return entry
        if entry.is_file():
            # A worktree or submodule records `gitdir: <path>` instead.
            text = entry.read_text(encoding="utf-8", errors="replace").strip()
            _, _, target = text.partition("gitdir:")
            if not target.strip():
                return None
            resolved = Path(target.strip())
            if not resolved.is_absolute():
                resolved = (candidate / resolved).resolve()
            return resolved if resolved.is_dir() else None
    return None


def _read_packed_ref(git_dir: Path, ref: str) -> str | None:
    """Return the object id for ``ref`` from ``packed-refs``, if present."""
    packed = git_dir / "packed-refs"
    if not packed.is_file():
        return None
    for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith(("#", "^")):
            continue
        object_id, _, name = line.partition(" ")
        if name.strip() == ref and _OBJECT_ID.fullmatch(object_id):
            return object_id
    return None


def resolve_git_commit(start: Path | str | None = None) -> str | UnknownType:
    """Return the commit currently checked out, or UNKNOWN.

    Args:
        start: Directory to begin searching from. Defaults to the directory
            containing this module. Tests inject a temporary directory here
            rather than depending on the repository they happen to run in.

    Returns:
        A full object id, or :data:`~qcf.core.unknown.UNKNOWN` when no git
        checkout is present or the reference cannot be resolved.
    """
    origin = Path(start) if start is not None else Path(__file__).resolve().parent
    git_dir = _find_git_dir(origin)
    if git_dir is None:
        return UNKNOWN

    head = git_dir / "HEAD"
    if not head.is_file():
        return UNKNOWN
    text = head.read_text(encoding="utf-8", errors="replace").strip()

    if not text.startswith("ref:"):
        # Detached HEAD records the object id directly.
        return text if _OBJECT_ID.fullmatch(text) else UNKNOWN

    ref = text.removeprefix("ref:").strip()
    if not ref:
        return UNKNOWN

    loose = git_dir / ref
    if loose.is_file():
        object_id = loose.read_text(encoding="utf-8", errors="replace").strip()
        return object_id if _OBJECT_ID.fullmatch(object_id) else UNKNOWN

    packed = _read_packed_ref(git_dir, ref)
    return packed if packed is not None else UNKNOWN


#: The installed package version.
__version__: Final[str] = package_version()
