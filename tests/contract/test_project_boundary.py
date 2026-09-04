"""Project boundaries, and proof that the checker enforcing them works.

A check that has only ever been observed to pass has not been shown to be
capable of failing. Each check here is therefore pointed at a temporary tree
containing a deliberate violation, so that its failure is demonstrated rather
than assumed. No violation is written into tracked source.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from scripts import check_project_boundary as boundary

from qcf.core.config import AppConfig
from qcf.core.enums import OperatingMode

pytestmark = pytest.mark.boundary

APPROVED_RUNTIME = {"pydantic", "pydantic-settings", "PyYAML", "structlog"}
APPROVED_DEV = {
    "pytest",
    "pytest-cov",
    "hypothesis",
    "ruff",
    "mypy",
    "pre-commit",
    "types-PyYAML",
    "detect-secrets",
}


def _requirement_names(entries: list[str]) -> set[str]:
    """Strip version specifiers from PEP 508 requirement strings."""
    return {
        entry.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip() for entry in entries
    }


def _fake_package(root: Path, relative: str, source: str) -> None:
    """Write a Python file into a temporary tree that imitates the repository."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _git_repo(root: Path, files: dict[str, str]) -> None:
    """Create a local git repository with ``files`` staged. No network, no commit."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)  # noqa: S607
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "-A", "-f"], cwd=root, check=True)  # noqa: S607


# --------------------------------------------------------------------------
# The boundaries themselves
# --------------------------------------------------------------------------


def test_only_the_permitted_modes_exist() -> None:
    assert [mode.value for mode in OperatingMode] == [
        "DISABLED",
        "RESEARCH",
        "BACKTEST",
        "REPLAY",
        "PAPER",
    ]


def test_the_default_mode_is_disabled() -> None:
    assert AppConfig().mode is OperatingMode.DISABLED


def test_no_live_mode_exists_anywhere() -> None:
    assert not hasattr(OperatingMode, "LIVE")
    with pytest.raises(ValueError, match="not a valid OperatingMode"):
        OperatingMode("LIVE")


def test_no_broker_or_network_module_is_importable_from_the_package() -> None:
    """If the package never imported one, it is not loaded on our account."""
    package_modules = [name for name in sys.modules if name.startswith("qcf")]
    assert package_modules, "qcf was not imported; the assertion below would be vacuous"
    for forbidden in boundary.FORBIDDEN_CLIENT_MODULES:
        assert forbidden not in sys.modules


def test_the_declared_dependency_set_matches_the_approved_list(repo_root: Path) -> None:
    """A dependency cannot be added without this test being changed deliberately."""
    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    assert _requirement_names(data["project"]["dependencies"]) == APPROVED_RUNTIME
    assert _requirement_names(data["dependency-groups"]["dev"]) == APPROVED_DEV


def test_no_broker_or_data_client_is_declared_as_a_dependency(repo_root: Path) -> None:
    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    declared = _requirement_names(data["project"]["dependencies"]) | _requirement_names(
        data["dependency-groups"]["dev"]
    )
    assert not {name.lower() for name in declared} & {
        name.lower() for name in boundary.FORBIDDEN_CLIENT_MODULES
    }


# --------------------------------------------------------------------------
# The checker passes on this repository
# --------------------------------------------------------------------------


def test_every_check_passes_on_the_repository(repo_root: Path) -> None:
    failures = [result for result in boundary.run_all_checks(repo_root) if result.status == "FAIL"]
    assert not failures, "\n".join(f"{r.name}: {r.details}" for r in failures)


def test_the_checker_exits_zero_on_the_repository(
    repo_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert boundary.main([str(repo_root)]) == 0
    assert "Boundary check passed." in capsys.readouterr().out


def test_the_checker_modifies_nothing(repo_root: Path) -> None:
    """It is a read-only command; a check with side effects is not a check."""
    before = {
        path: path.stat().st_mtime_ns for path in sorted(repo_root.glob("*")) if path.is_file()
    }
    boundary.run_all_checks(repo_root)
    after = {
        path: path.stat().st_mtime_ns for path in sorted(repo_root.glob("*")) if path.is_file()
    }
    assert before == after


# --------------------------------------------------------------------------
# The checker fails on deliberate violations
# --------------------------------------------------------------------------


def test_a_live_mode_is_caught(tmp_path: Path) -> None:
    _fake_package(
        tmp_path,
        "src/qcf/core/enums.py",
        "from enum import StrEnum\n\n\n"
        "class OperatingMode(StrEnum):\n"
        '    DISABLED = "DISABLED"\n'
        '    RESEARCH = "RESEARCH"\n'
        '    BACKTEST = "BACKTEST"\n'
        '    REPLAY = "REPLAY"\n'
        '    PAPER = "PAPER"\n'
        '    LIVE = "LIVE"\n',
    )
    result = boundary.check_no_live_mode(tmp_path)
    assert result.status == "FAIL"
    assert any("LIVE" in detail for detail in result.details)


def test_a_missing_enums_module_is_caught(tmp_path: Path) -> None:
    assert boundary.check_no_live_mode(tmp_path).status == "FAIL"


def test_a_renamed_mode_set_is_caught(tmp_path: Path) -> None:
    """Silently dropping a permitted mode is a change worth noticing too."""
    _fake_package(
        tmp_path,
        "src/qcf/core/enums.py",
        'from enum import StrEnum\n\n\nclass OperatingMode(StrEnum):\n    DISABLED = "DISABLED"\n',
    )
    assert boundary.check_no_live_mode(tmp_path).status == "FAIL"


def test_a_broker_client_import_is_caught(tmp_path: Path) -> None:
    _fake_package(tmp_path, "src/qcf/adapter.py", "import ib_insync\n")
    result = boundary.check_no_forbidden_imports(tmp_path)
    assert result.status == "FAIL"
    assert any("ib_insync" in detail for detail in result.details)


def test_a_from_import_of_a_broker_client_is_caught(tmp_path: Path) -> None:
    _fake_package(tmp_path, "src/qcf/adapter.py", "from tradovate.api import Client\n")
    assert boundary.check_no_forbidden_imports(tmp_path).status == "FAIL"


def test_a_network_import_inside_the_package_is_caught(tmp_path: Path) -> None:
    """A library that cannot open a connection cannot route an order."""
    _fake_package(tmp_path, "src/qcf/feed.py", "import socket\n")
    assert boundary.check_no_forbidden_imports(tmp_path).status == "FAIL"


def test_a_network_import_outside_the_package_is_allowed(tmp_path: Path) -> None:
    """Tooling may use the network; the package may not."""
    _fake_package(tmp_path, "scripts/fetch_docs.py", "import urllib.request\n")
    assert boundary.check_no_forbidden_imports(tmp_path).status == "PASS"


def test_prose_mentioning_a_broker_client_is_not_flagged(tmp_path: Path) -> None:
    """Imports are read from the syntax tree, so describing a rule cannot break it."""
    _fake_package(
        tmp_path,
        "src/qcf/notes.py",
        '"""QCF must never import ib_insync, tradovate, or rithmic."""\n'
        'FORBIDDEN = ["ib_insync", "tradovate"]\n',
    )
    assert boundary.check_no_forbidden_imports(tmp_path).status == "PASS"


def test_an_order_transmission_function_is_caught(tmp_path: Path) -> None:
    _fake_package(
        tmp_path, "src/qcf/exec.py", "def submit_order(contract: str) -> None:\n    ...\n"
    )
    result = boundary.check_no_real_order_functions(tmp_path)
    assert result.status == "FAIL"
    assert any("submit_order" in detail for detail in result.details)


@pytest.mark.parametrize(
    "name", ["send_order", "transmit_order", "place_order", "route_order", "dispatchOrder"]
)
def test_every_transmission_verb_is_caught(tmp_path: Path, name: str) -> None:
    _fake_package(tmp_path, "src/qcf/exec.py", f"def {name}() -> None:\n    ...\n")
    assert boundary.check_no_real_order_functions(tmp_path).status == "FAIL"


def test_an_async_order_function_is_caught(tmp_path: Path) -> None:
    _fake_package(tmp_path, "src/qcf/exec.py", "async def send_order() -> None:\n    ...\n")
    assert boundary.check_no_real_order_functions(tmp_path).status == "FAIL"


@pytest.mark.parametrize("name", ["submit_simulated_order", "place_paper_order"])
def test_simulated_order_functions_are_permitted(tmp_path: Path, name: str) -> None:
    """Later stages need these; only unmarked transmission is forbidden."""
    _fake_package(tmp_path, "src/qcf/paper.py", f"def {name}() -> None:\n    ...\n")
    assert boundary.check_no_real_order_functions(tmp_path).status == "PASS"


def test_missing_required_files_are_caught(tmp_path: Path) -> None:
    result = boundary.check_required_files_exist(tmp_path)
    assert result.status == "FAIL"
    assert "pyproject.toml" in result.details


def test_a_dangling_documentation_link_is_caught(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("See [the plan](missing/plan.md).\n", encoding="utf-8")
    result = boundary.check_documentation_links(tmp_path)
    assert result.status == "FAIL"
    assert any("missing/plan.md" in detail for detail in result.details)


def test_external_and_anchor_links_are_not_checked(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text(
        "[web](https://example.invalid/x) [anchor](#section) [mail](mailto:a@b.invalid)\n",
        encoding="utf-8",
    )
    assert boundary.check_documentation_links(tmp_path).status == "PASS"


def test_a_link_with_a_fragment_resolves_to_the_file(tmp_path: Path) -> None:
    (tmp_path / "target.md").write_text("# Heading\n", encoding="utf-8")
    (tmp_path / "doc.md").write_text("[here](target.md#heading)\n", encoding="utf-8")
    assert boundary.check_documentation_links(tmp_path).status == "PASS"


def test_the_wrong_product_code_is_caught(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Trading 6E futures.\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("We trade E6 contracts.\n", encoding="utf-8")
    result = boundary.check_product_code_terminology(tmp_path)
    assert result.status == "FAIL"
    assert any("notes.md" in detail for detail in result.details)


def test_the_documented_marker_exempts_a_line(tmp_path: Path) -> None:
    """Saying which spelling is wrong requires writing it once."""
    (tmp_path / "README.md").write_text(
        f"Use 6E, never E6. <!-- {boundary.E6_ALLOW_MARKER} -->\n", encoding="utf-8"
    )
    assert boundary.check_product_code_terminology(tmp_path).status == "PASS"


def test_a_readme_that_never_names_the_product_code_is_caught(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("A futures research project.\n", encoding="utf-8")
    assert boundary.check_product_code_terminology(tmp_path).status == "FAIL"


def test_tracked_market_data_is_caught(tmp_path: Path) -> None:
    _git_repo(tmp_path, {"data/raw/6e_trades.csv": "ts,price\n"})
    result = boundary.check_no_tracked_market_data(tmp_path)
    assert result.status == "FAIL"
    assert "data/raw/6e_trades.csv" in result.details


def test_the_tracked_data_skeleton_is_permitted(tmp_path: Path) -> None:
    _git_repo(tmp_path, {"data/README.md": "# Data\n", "data/raw/.gitkeep": ""})
    assert boundary.check_no_tracked_market_data(tmp_path).status == "PASS"


def test_a_tracked_env_file_is_caught(tmp_path: Path) -> None:
    _git_repo(tmp_path, {".env": "QCF_MODE=DISABLED\n"})
    result = boundary.check_no_tracked_env_file(tmp_path)
    assert result.status == "FAIL"
    assert ".env" in result.details


def test_a_tracked_env_example_is_permitted(tmp_path: Path) -> None:
    _git_repo(tmp_path, {".env.example": "QCF_MODE=DISABLED\n"})
    assert boundary.check_no_tracked_env_file(tmp_path).status == "PASS"


def test_git_checks_report_skip_outside_a_checkout(tmp_path: Path) -> None:
    """A check that cannot run says so; it does not pass silently."""
    assert boundary.check_no_tracked_env_file(tmp_path).status == "SKIP"
    assert boundary.check_no_tracked_market_data(tmp_path).status == "SKIP"


def test_an_invalid_example_configuration_is_caught(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "base.example.yaml").write_text("mode: LIVE\n", encoding="utf-8")
    assert boundary.check_example_config_validates(tmp_path).status == "FAIL"


def test_a_missing_example_configuration_is_caught(tmp_path: Path) -> None:
    assert boundary.check_example_config_validates(tmp_path).status == "FAIL"


def test_an_example_without_utc_is_caught(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "base.example.yaml").write_text("mode: DISABLED\n", encoding="utf-8")
    assert boundary.check_internal_timezone_is_utc(tmp_path).status == "FAIL"


def test_the_checker_exits_non_zero_when_a_check_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert boundary.main([str(tmp_path)]) == 1
    assert "BOUNDARY CHECK FAILED" in capsys.readouterr().out


def test_unparseable_package_source_is_reported(tmp_path: Path) -> None:
    _fake_package(tmp_path, "src/qcf/broken.py", "def (\n")
    result = boundary.check_no_real_order_functions(tmp_path)
    assert result.status == "FAIL"
    assert any("not parseable" in detail for detail in result.details)


def test_an_absent_package_reports_skip(tmp_path: Path) -> None:
    assert boundary.check_no_real_order_functions(tmp_path).status == "SKIP"
