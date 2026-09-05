"""Project-owned file enumeration.

The defect these guard against (R-06): the boundary checker used a hardcoded
skip-list containing `.venv`, so a virtual environment under any other name was
traversed. In the review clone 1558 of 1580 scanned Python files were
third-party — the check passed only because that dependency set happened not to
trip it.

A second defect (R-08) came from the same code: the skip branch executed only
when a cache directory already existed, so a first run in a clean checkout
measured different coverage from a second. Every fixture here builds the tree it
needs, so nothing depends on a previous run having left something behind.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from scripts.repo_files import (
    GENERATED_DIRECTORY_NAMES,
    RepoFileError,
    enumerate_project_files,
    git_is_available,
    run_git,
)

pytestmark = pytest.mark.boundary


def _git_repo(root: Path, files: dict[str, str]) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)  # noqa: S607
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)  # noqa: S607
    return root


def _names(root: Path, paths: list[Path]) -> set[str]:
    return {path.relative_to(root).as_posix() for path in paths}


def test_tracked_files_are_enumerated(tmp_path: Path) -> None:
    root = _git_repo(tmp_path, {"a.py": "1", "pkg/b.py": "2"})
    assert _names(root, enumerate_project_files(root)) == {"a.py", "pkg/b.py"}


def test_untracked_but_unignored_files_are_included(tmp_path: Path) -> None:
    """A newly written module is first-party even before it is staged."""
    root = _git_repo(tmp_path, {"a.py": "1"})
    (root / "brand_new.py").write_text("2", encoding="utf-8")
    assert "brand_new.py" in _names(root, enumerate_project_files(root))


def test_untracked_files_can_be_excluded_on_request(tmp_path: Path) -> None:
    root = _git_repo(tmp_path, {"a.py": "1"})
    (root / "brand_new.py").write_text("2", encoding="utf-8")
    found = _names(root, enumerate_project_files(root, include_untracked=False))
    assert found == {"a.py"}


def test_ignored_files_are_excluded(tmp_path: Path) -> None:
    root = _git_repo(tmp_path, {"a.py": "1", ".gitignore": "build/\n"})
    (root / "build").mkdir()
    (root / "build" / "generated.py").write_text("3", encoding="utf-8")
    assert "build/generated.py" not in _names(root, enumerate_project_files(root))


@pytest.mark.parametrize("venv_name", [".venv", ".venv312", "venv", "env", "my-weird-env"])
def test_a_virtual_environment_is_not_enumerated(tmp_path: Path, venv_name: str) -> None:
    """R-06: previously only a directory literally named `.venv` was skipped."""
    root = _git_repo(tmp_path, {"a.py": "1", ".gitignore": f"{venv_name}/\n"})
    venv = root / venv_name / "lib" / "site-packages"
    venv.mkdir(parents=True)
    (root / venv_name / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
    (venv / "third_party.py").write_text("import ib_insync\n", encoding="utf-8")
    found = _names(root, enumerate_project_files(root))
    assert found == {"a.py", ".gitignore"}


def test_tracked_first_party_code_is_never_hidden_by_pruning(tmp_path: Path) -> None:
    """Pruning must not be able to conceal committed source.

    A directory carrying a pyvenv.cfg marker is pruned in the fallback walk. If
    git tracks files inside it, git's enumeration still returns them: pruning
    applies to untracked trees only.
    """
    root = _git_repo(tmp_path, {"env/pyvenv.cfg": "home = /usr\n", "env/real_source.py": "1"})
    assert "env/real_source.py" in _names(root, enumerate_project_files(root))


@pytest.mark.parametrize("name", ["my file.py", "tab\tname.py", "-dash.py", "ünï.py"])
def test_hostile_filenames_survive_enumeration(tmp_path: Path, name: str) -> None:
    """NUL-delimited output is what makes this work; a newline would too."""
    root = _git_repo(tmp_path, {name: "1"})
    assert name in _names(root, enumerate_project_files(root))


def test_a_newline_in_a_filename_survives(tmp_path: Path) -> None:
    root = _git_repo(tmp_path, {"line\nbreak.py": "1"})
    assert "line\nbreak.py" in _names(root, enumerate_project_files(root))


def test_a_deleted_but_tracked_file_is_dropped(tmp_path: Path) -> None:
    """Git lists it; it is not on disk, and a scanner would error on it."""
    root = _git_repo(tmp_path, {"a.py": "1", "gone.py": "2"})
    (root / "gone.py").unlink()
    assert _names(root, enumerate_project_files(root)) == {"a.py"}


def test_enumeration_outside_a_checkout_uses_the_fallback_walk(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("1", encoding="utf-8")
    nested = tmp_path / "pkg"
    nested.mkdir()
    (nested / "b.py").write_text("2", encoding="utf-8")
    assert not git_is_available(tmp_path)
    assert _names(tmp_path, enumerate_project_files(tmp_path)) == {"a.py", "pkg/b.py"}


@pytest.mark.parametrize("generated", sorted(GENERATED_DIRECTORY_NAMES - {".git"}))
def test_the_fallback_walk_prunes_generated_trees(tmp_path: Path, generated: str) -> None:
    """Each fixture is built here, not inherited from an earlier test run."""
    (tmp_path / "a.py").write_text("1", encoding="utf-8")
    junk = tmp_path / generated
    junk.mkdir()
    (junk / "cached.py").write_text("2", encoding="utf-8")
    assert _names(tmp_path, enumerate_project_files(tmp_path)) == {"a.py"}


def test_the_fallback_walk_prunes_virtual_environments(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("1", encoding="utf-8")
    env = tmp_path / "some-env"
    env.mkdir()
    (env / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
    (env / "installed.py").write_text("2", encoding="utf-8")
    assert _names(tmp_path, enumerate_project_files(tmp_path)) == {"a.py"}


def test_symlinks_are_not_followed(tmp_path: Path) -> None:
    """A link can leave the tree entirely, and a cycle would not terminate."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "external.py").write_text("1", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.py").write_text("2", encoding="utf-8")
    (root / "link").symlink_to(outside, target_is_directory=True)
    assert _names(root, enumerate_project_files(root)) == {"a.py"}


def test_a_symlink_cycle_terminates(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("1", encoding="utf-8")
    (tmp_path / "loop").symlink_to(tmp_path, target_is_directory=True)
    assert _names(tmp_path, enumerate_project_files(tmp_path)) == {"a.py"}


def test_an_unreadable_root_raises_rather_than_returning_nothing(tmp_path: Path) -> None:
    """ "No files" and "I could not find out" must not look the same."""
    with pytest.raises(RepoFileError):
        enumerate_project_files(tmp_path / "does-not-exist")


def test_a_failing_git_command_raises(tmp_path: Path) -> None:
    _git_repo(tmp_path, {"a.py": "1"})
    with pytest.raises(RepoFileError):
        run_git(tmp_path, ["cat-file", "-p", "0" * 40])


def test_git_is_reported_unavailable_outside_a_checkout(tmp_path: Path) -> None:
    assert not git_is_available(tmp_path)


def test_an_empty_repository_enumerates_to_nothing(tmp_path: Path) -> None:
    _git_repo(tmp_path, {})
    assert enumerate_project_files(tmp_path) == []


def test_a_missing_git_binary_is_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _missing(*_args: object, **_kwargs: object) -> object:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", _missing)
    with pytest.raises(RepoFileError, match="not installed"):
        run_git(tmp_path, ["status"])


def test_a_git_timeout_is_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _timeout(*_args: object, **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    monkeypatch.setattr(subprocess, "run", _timeout)
    with pytest.raises(RepoFileError, match="timed out"):
        run_git(tmp_path, ["status"])


def test_an_os_error_running_git_is_reported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _oserror(*_args: object, **_kwargs: object) -> object:
        raise OSError(13, "denied")

    monkeypatch.setattr(subprocess, "run", _oserror)
    with pytest.raises(RepoFileError, match="could not be executed"):
        run_git(tmp_path, ["status"])
