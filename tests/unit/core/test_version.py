"""Version and revision resolution, including its honest failure modes."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest

import qcf
from qcf.core.unknown import UNKNOWN, is_unknown
from qcf.core.version import __version__, package_version, resolve_git_commit

# Fabricated git object ids for fixtures. Not credentials; git object ids are
# public identifiers by nature.
SHA1 = "0123456789abcdef0123456789abcdef01234567"  # pragma: allowlist secret
SHA256 = "0" * 64


def _git_dir(root: Path) -> Path:
    path = root / ".git"
    (path / "refs" / "heads").mkdir(parents=True)
    return path


def test_package_version_is_reported() -> None:
    assert package_version() == __version__
    assert __version__


def test_importing_qcf_never_requires_git() -> None:
    """A wheel has no git metadata; importing must still succeed."""
    assert qcf.__version__ == __version__


def test_no_checkout_yields_unknown(tmp_path: Path) -> None:
    """A plausible-looking commit would be worse than none at all."""
    assert is_unknown(resolve_git_commit(tmp_path))


def test_a_loose_ref_resolves(tmp_path: Path) -> None:
    git = _git_dir(tmp_path)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "refs" / "heads" / "main").write_text(f"{SHA1}\n", encoding="utf-8")
    assert resolve_git_commit(tmp_path) == SHA1


def test_a_sha256_object_id_resolves(tmp_path: Path) -> None:
    git = _git_dir(tmp_path)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "refs" / "heads" / "main").write_text(f"{SHA256}\n", encoding="utf-8")
    assert resolve_git_commit(tmp_path) == SHA256


def test_a_detached_head_resolves(tmp_path: Path) -> None:
    git = _git_dir(tmp_path)
    (git / "HEAD").write_text(f"{SHA1}\n", encoding="utf-8")
    assert resolve_git_commit(tmp_path) == SHA1


def test_a_packed_ref_resolves(tmp_path: Path) -> None:
    """Packed refs are the normal state of a freshly cloned repository."""
    git = _git_dir(tmp_path)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "packed-refs").write_text(
        f"# pack-refs with: peeled fully-peeled sorted\n{SHA1} refs/heads/main\n^{'1' * 40}\n",
        encoding="utf-8",
    )
    assert resolve_git_commit(tmp_path) == SHA1


def test_resolution_searches_upwards(tmp_path: Path) -> None:
    git = _git_dir(tmp_path)
    (git / "HEAD").write_text(f"{SHA1}\n", encoding="utf-8")
    nested = tmp_path / "src" / "qcf" / "core"
    nested.mkdir(parents=True)
    assert resolve_git_commit(nested) == SHA1


def test_a_worktree_gitdir_pointer_resolves(tmp_path: Path) -> None:
    real = tmp_path / "real"
    (real / "refs" / "heads").mkdir(parents=True)
    (real / "HEAD").write_text(f"{SHA1}\n", encoding="utf-8")
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / ".git").write_text(f"gitdir: {real}\n", encoding="utf-8")
    assert resolve_git_commit(tree) == SHA1


def test_a_relative_worktree_pointer_resolves(tmp_path: Path) -> None:
    real = tmp_path / "real"
    (real / "refs" / "heads").mkdir(parents=True)
    (real / "HEAD").write_text(f"{SHA1}\n", encoding="utf-8")
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / ".git").write_text("gitdir: ../real\n", encoding="utf-8")
    assert resolve_git_commit(tree) == SHA1


@pytest.mark.parametrize(
    ("head", "reason"),
    [
        ("ref: refs/heads/missing\n", "the ref file does not exist"),
        ("ref:\n", "the ref name is empty"),
        ("not-a-sha\n", "detached HEAD holds no object id"),
    ],
)
def test_unresolvable_states_yield_unknown(tmp_path: Path, head: str, reason: str) -> None:
    git = _git_dir(tmp_path)
    (git / "HEAD").write_text(head, encoding="utf-8")
    assert is_unknown(resolve_git_commit(tmp_path)), reason


def test_a_corrupt_ref_file_yields_unknown(tmp_path: Path) -> None:
    git = _git_dir(tmp_path)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "refs" / "heads" / "main").write_text("garbage\n", encoding="utf-8")
    assert is_unknown(resolve_git_commit(tmp_path))


def test_a_missing_head_yields_unknown(tmp_path: Path) -> None:
    _git_dir(tmp_path)
    assert is_unknown(resolve_git_commit(tmp_path))


def test_an_empty_gitdir_pointer_yields_unknown(tmp_path: Path) -> None:
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / ".git").write_text("gitdir:\n", encoding="utf-8")
    assert is_unknown(resolve_git_commit(tree))


def test_a_dangling_gitdir_pointer_yields_unknown(tmp_path: Path) -> None:
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / ".git").write_text(f"gitdir: {tmp_path / 'absent'}\n", encoding="utf-8")
    assert is_unknown(resolve_git_commit(tree))


def test_a_packed_ref_for_another_branch_is_not_used(tmp_path: Path) -> None:
    git = _git_dir(tmp_path)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "packed-refs").write_text(f"{SHA1} refs/heads/other\n", encoding="utf-8")
    assert is_unknown(resolve_git_commit(tmp_path))


def test_the_default_start_is_the_package_directory() -> None:
    """In a checkout this resolves; in an installed wheel it returns UNKNOWN."""
    result = resolve_git_commit()
    assert result is UNKNOWN or (isinstance(result, str) and len(result) in {40, 64})


def test_an_uninstalled_distribution_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """A source tree on the path without an install must still report a version."""

    def _raise(_name: str) -> str:
        raise PackageNotFoundError(_name)

    monkeypatch.setattr("qcf.core.version._distribution_version", _raise)
    assert package_version() == "0.0.0"
