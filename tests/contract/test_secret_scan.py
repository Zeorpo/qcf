"""The secret-scan enforcement path.

The defect these guard against (R-05): CI ran

    detect-secrets-hook --baseline .secrets.baseline $(git ls-files)

whose unquoted command substitution word-splits, so a tracked path containing a
space reached the scanner as several non-existent arguments and the step exited
zero having scanned nothing.

Fixtures use an obviously fabricated key. It is not a credential, has never been
valid anywhere, and is written only into temporary directories.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import scripts.run_secret_scan as runner
from scripts.run_secret_scan import (
    EXIT_CLEAN,
    EXIT_ERROR,
    EXIT_FINDINGS,
    batch_paths,
    main,
    scan,
)

pytestmark = pytest.mark.boundary

# Fabricated. Shaped to trip the detector; valid for nothing.
FAKE_KEY = "wJalrXUtnFEMIK7MDENGbPxRfiCYFAKEKEY12345"  # pragma: allowlist secret
DETECTABLE = f'aws_secret_access_key = "{FAKE_KEY}"\n'

# Names chosen to break naive shell expansion in different ways.
HOSTILE_NAMES = [
    pytest.param("my config file.py", id="space"),
    pytest.param("tab\tname.py", id="tab"),
    pytest.param("-leading-dash.py", id="leading-dash"),
    pytest.param("ünïcodé.py", id="non-ascii"),
    pytest.param("quote'and\"quote.py", id="quotes"),
    pytest.param("semi;colon&amp.py", id="shell-metacharacters"),
]


def _repo(root: Path, files: dict[str, str], baseline: Path) -> Path:
    """Build a temporary git repository containing ``files``."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)  # noqa: S607
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "-A", "-f"], cwd=root, check=True)  # noqa: S607
    (root / ".secrets.baseline").write_text(baseline.read_text(encoding="utf-8"), encoding="utf-8")
    return root


@pytest.fixture
def baseline(repo_root: Path) -> Path:
    return repo_root / ".secrets.baseline"


@pytest.mark.parametrize("name", HOSTILE_NAMES)
def test_a_secret_is_found_whatever_the_filename(tmp_path: Path, baseline: Path, name: str) -> None:
    """Every path must reach the scanner as exactly one argument."""
    root = _repo(tmp_path, {name: DETECTABLE}, baseline)
    outcome = scan(root, root / ".secrets.baseline")
    assert outcome.status == EXIT_FINDINGS
    assert name in outcome.findings


def test_the_old_shell_form_missed_what_the_runner_finds(tmp_path: Path, baseline: Path) -> None:
    """Before/after evidence for R-05, run against the real scanner.

    The old form is reconstructed here rather than described, so the regression
    is demonstrated instead of asserted.
    """
    root = _repo(tmp_path, {"my config file.py": DETECTABLE}, baseline)

    # BEFORE: unquoted command substitution, exactly as the workflow had it.
    before = subprocess.run(  # noqa: S602 - reproducing the defect is the point
        "detect-secrets-hook --baseline .secrets.baseline $(git ls-files)",  # noqa: S607
        shell=True,
        cwd=root,
        capture_output=True,
        check=False,
    )
    assert before.returncode == 0, "the old form was expected to miss this secret"

    # AFTER: the runner finds it.
    assert scan(root, root / ".secrets.baseline").status == EXIT_FINDINGS


def test_clean_input_passes(tmp_path: Path, baseline: Path) -> None:
    root = _repo(tmp_path, {"ordinary.py": "value = 1\n"}, baseline)
    outcome = scan(root, root / ".secrets.baseline")
    assert outcome.status == EXIT_CLEAN
    assert outcome.findings == ()


def test_only_the_offending_file_is_reported(tmp_path: Path, baseline: Path) -> None:
    """A batch failure must not smear blame across its clean members."""
    root = _repo(
        tmp_path,
        {"dirty.py": DETECTABLE, "clean_one.py": "a = 1\n", "clean_two.py": "b = 2\n"},
        baseline,
    )
    outcome = scan(root, root / ".secrets.baseline")
    assert outcome.status == EXIT_FINDINGS
    assert "dirty.py" in outcome.findings
    assert "clean_one.py" not in outcome.findings
    assert "clean_two.py" not in outcome.findings


def test_an_empty_repository_is_clean_not_an_error(tmp_path: Path, baseline: Path) -> None:
    root = _repo(tmp_path, {}, baseline)
    assert scan(root, root / ".secrets.baseline").status == EXIT_CLEAN


def test_a_missing_baseline_is_a_tool_error(tmp_path: Path, baseline: Path) -> None:
    """An unperformed check must never be reported as a passing one."""
    root = _repo(tmp_path, {"a.py": "x = 1\n"}, baseline)
    outcome = scan(root, root / "absent.baseline")
    assert outcome.status == EXIT_ERROR
    assert outcome.error is not None


def test_enumeration_failure_is_a_tool_error(tmp_path: Path, baseline: Path) -> None:
    outcome = scan(tmp_path / "nonexistent", baseline)
    assert outcome.status == EXIT_ERROR


def test_untracked_but_unignored_files_are_scanned(tmp_path: Path, baseline: Path) -> None:
    """A newly written, unstaged module is still first-party code."""
    root = _repo(tmp_path, {"tracked.py": "x = 1\n"}, baseline)
    (root / "brand_new.py").write_text(DETECTABLE, encoding="utf-8")
    outcome = scan(root, root / ".secrets.baseline")
    assert outcome.status == EXIT_FINDINGS
    assert "brand_new.py" in outcome.findings


def test_ignored_files_are_not_scanned(tmp_path: Path, baseline: Path) -> None:
    root = _repo(tmp_path, {"tracked.py": "x = 1\n", ".gitignore": "secret_junk/\n"}, baseline)
    junk = root / "secret_junk"
    junk.mkdir()
    (junk / "leak.py").write_text(DETECTABLE, encoding="utf-8")
    assert scan(root, root / ".secrets.baseline").status == EXIT_CLEAN


def test_the_baseline_is_never_rewritten(tmp_path: Path, baseline: Path) -> None:
    """`scan --baseline` rewrites in place and so can never fail a build."""
    root = _repo(tmp_path, {"dirty.py": DETECTABLE}, baseline)
    target = root / ".secrets.baseline"
    before = target.read_bytes()
    scan(root, target)
    assert target.read_bytes() == before


def test_batching_emits_every_path_exactly_once() -> None:
    paths = [Path(f"/repo/file_{index:04d}.py") for index in range(500)]
    batches = list(batch_paths(paths, max_bytes=200))
    assert [path for batch in batches for path in batch] == paths
    assert len(batches) > 1, "the bound was expected to force several batches"


def test_a_single_oversized_path_is_still_scanned() -> None:
    """Dropping it would silently reintroduce the defect this module fixes."""
    long_path = Path("/repo/" + "x" * 500 + ".py")
    assert list(batch_paths([long_path], max_bytes=10)) == [[long_path]]


def test_findings_are_reported_without_printing_the_value(
    tmp_path: Path, baseline: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """CI logs are more widely readable than the repository."""
    root = _repo(tmp_path, {"dirty.py": DETECTABLE}, baseline)
    assert main([str(root)]) == EXIT_FINDINGS
    output = capsys.readouterr().out
    assert "dirty.py" in output
    assert FAKE_KEY not in output


def test_main_reports_a_clean_scan(
    tmp_path: Path, baseline: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path, {"ordinary.py": "x = 1\n"}, baseline)
    assert main([str(root)]) == EXIT_CLEAN
    assert "passed" in capsys.readouterr().out


def test_main_reports_a_tool_error_distinctly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "nope")]) == EXIT_ERROR
    assert "COULD NOT RUN" in capsys.readouterr().out


def test_the_scanner_module_is_invocable(repo_root: Path) -> None:
    """The runner spawns the scanner by module path; pin that it exists."""
    completed = subprocess.run(
        [sys.executable, "-m", "detect_secrets.pre_commit_hook", "--help"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0


def test_a_missing_scanner_is_a_tool_error(
    tmp_path: Path, baseline: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the scanner cannot start, the check did not happen."""
    root = _repo(tmp_path, {"a.py": "x = 1\n"}, baseline)

    def _missing(*_args: object, **_kwargs: object) -> object:
        raise FileNotFoundError("detect_secrets")

    monkeypatch.setattr("scripts.run_secret_scan.subprocess.run", _missing)
    outcome = scan(root, root / ".secrets.baseline")
    assert outcome.status == EXIT_ERROR
    assert outcome.error is not None
    assert "could not be started" in outcome.error


def test_a_scanner_timeout_is_a_tool_error(
    tmp_path: Path, baseline: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path, {"a.py": "x = 1\n"}, baseline)

    def _timeout(*_args: object, **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="detect-secrets", timeout=1)

    monkeypatch.setattr("scripts.run_secret_scan.subprocess.run", _timeout)
    outcome = scan(root, root / ".secrets.baseline")
    assert outcome.status == EXIT_ERROR


def test_a_scanner_usage_error_is_not_reported_as_findings(
    tmp_path: Path, baseline: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """argparse exit 2 is a tool failure; calling it "secrets found" would mislead."""
    root = _repo(tmp_path, {"a.py": "x = 1\n"}, baseline)
    monkeypatch.setattr(
        runner, "_invoke", lambda *_a, **_k: (2, "error: unrecognized arguments: -x\n")
    )
    outcome = scan(root, root / ".secrets.baseline")
    assert outcome.status == EXIT_ERROR
    assert outcome.error is not None
    assert "rejected its arguments" in outcome.error
