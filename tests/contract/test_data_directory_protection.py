"""The data directories must accept a skeleton and reject everything else.

Ignore rules are order-dependent and easy to get subtly wrong -- git does not
descend into an excluded directory, so a re-included file below one is silently
never seen. Reading the patterns is not enough, so this suite creates real files
and asks git. Every fixture is removed afterwards.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = pytest.mark.boundary

DATA_LAYERS = ("raw", "interim", "processed", "quarantine")


def _is_ignored(repo_root: Path, relative: str) -> bool:
    """Ask git whether ``relative`` is ignored."""
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo_root), "check-ignore", "-q", relative],  # noqa: S607
        check=False,
        capture_output=True,
    )
    if completed.returncode not in {0, 1}:
        pytest.fail(f"git check-ignore failed: {completed.stderr.decode(errors='replace')}")
    return completed.returncode == 0


@pytest.fixture
def temporary_data_file(repo_root: Path) -> Iterator[object]:
    """Create files under ``data/`` and remove them however the test ends."""
    created: list[Path] = []

    def _create(relative: str, content: bytes = b"placeholder") -> str:
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        created.append(path)
        return relative

    yield _create

    for path in created:
        path.unlink(missing_ok=True)


@pytest.mark.parametrize("layer", DATA_LAYERS)
@pytest.mark.parametrize(
    "filename",
    [
        "6e_trades.csv",
        "6e_bars.parquet",
        "6e_quotes.csv.gz",
        "6e_depth.json",
        "vendor_export.txt",
        "notes.md",
    ],
)
def test_every_data_file_is_ignored(
    repo_root: Path, temporary_data_file: object, layer: str, filename: str
) -> None:
    create = temporary_data_file
    assert callable(create)
    relative = create(f"data/{layer}/{filename}")
    assert _is_ignored(repo_root, relative), f"{relative} would be committable"


@pytest.mark.parametrize("layer", DATA_LAYERS)
def test_files_in_nested_data_directories_are_ignored(
    repo_root: Path, temporary_data_file: object, layer: str
) -> None:
    """A subdirectory must not become an escape hatch."""
    create = temporary_data_file
    assert callable(create)
    relative = create(f"data/{layer}/2026/09/6e_trades.csv")
    assert _is_ignored(repo_root, relative)


@pytest.mark.parametrize("layer", DATA_LAYERS)
def test_the_keep_file_remains_trackable(repo_root: Path, layer: str) -> None:
    assert not _is_ignored(repo_root, f"data/{layer}/.gitkeep")


def test_the_data_readme_remains_trackable(repo_root: Path) -> None:
    assert not _is_ignored(repo_root, "data/README.md")


@pytest.mark.parametrize("layer", DATA_LAYERS)
def test_the_skeleton_is_present_and_empty(repo_root: Path, layer: str) -> None:
    directory = repo_root / "data" / layer
    assert directory.is_dir()
    assert (directory / ".gitkeep").is_file()
    unexpected = [
        path.name for path in directory.iterdir() if path.name != ".gitkeep" and path.is_file()
    ]
    assert not unexpected, f"data/{layer} contains {unexpected}"


def test_only_the_skeleton_is_tracked(repo_root: Path) -> None:
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo_root), "ls-files", "data/"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = {line for line in completed.stdout.splitlines() if line}
    expected = {"data/README.md"} | {f"data/{layer}/.gitkeep" for layer in DATA_LAYERS}
    assert tracked == expected


def test_a_committed_env_file_would_be_ignored(repo_root: Path) -> None:
    assert _is_ignored(repo_root, ".env")
    assert not _is_ignored(repo_root, ".env.example")
