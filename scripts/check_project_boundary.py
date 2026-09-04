"""Verify QCF's non-negotiable project boundaries.

A boundary that is only written down is a boundary that erodes. This command is
the executable form of the rules in `README.md` and ADR-0001/ADR-0005: it fails
the build if a live operating mode appears, if a broker or market-data client is
imported, if a real-order path is defined, if market data or a `.env` file is
tracked, or if the repository drifts from its own documented shape.

It is read-only. It writes no file, opens no socket, and prints no value that
could be sensitive. Every check takes a root directory so that the test-suite
can point it at a temporary tree containing a deliberate violation, rather than
proving the checks work by writing violations into tracked source.

Usage::

    uv run python scripts/check_project_boundary.py [ROOT]

Exit status is zero only if every check passes. A check that cannot run -- git
metadata is unavailable outside a checkout, for example -- reports SKIP and says
so, rather than passing silently.
"""

from __future__ import annotations

import ast
import importlib
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal

Status = Literal["PASS", "FAIL", "SKIP"]

# --------------------------------------------------------------------------
# Policy data. Each list is deliberately narrow and documented; a broad
# allowlist would quietly re-open the boundary it is meant to defend.
# --------------------------------------------------------------------------

#: Top-level modules of broker, exchange, and market-data clients. Importing any
#: of these would give QCF a route to a real account or a live feed.
FORBIDDEN_CLIENT_MODULES: Final[frozenset[str]] = frozenset(
    {
        "alpaca",
        "alpaca_trade_api",
        "cbpro",
        "ccxt",
        "coinbase",
        "databento",
        "ib_insync",
        "ibapi",
        "ibkr",
        "interactive_brokers",
        "krakenex",
        "metatrader5",
        "ninjatrader",
        "oanda",
        "oandapyV20",
        "polygon",
        "quickfix",
        "rithmic",
        "robin_stocks",
        "schwab",
        "simplefix",
        "tastytrade",
        "tda",
        "tdameritrade",
        "tradovate",
        "tws",
        "yfinance",
    }
)

#: Network modules. A library that cannot open a connection cannot route an
#: order, so `src/qcf` is held to a stricter standard than tooling is.
FORBIDDEN_NETWORK_MODULES: Final[frozenset[str]] = frozenset(
    {
        "aiohttp",
        "ftplib",
        "http",
        "httpx",
        "requests",
        "smtplib",
        "socket",
        "telnetlib",
        "urllib.request",
        "websocket",
        "websockets",
        "xmlrpc",
    }
)

#: Verbs that, applied to an order, describe transmission rather than research.
_ORDER_VERBS: Final = "submit|send|transmit|place|route|dispatch"
_ORDER_FUNCTION: Final = re.compile(rf"(?:{_ORDER_VERBS})\w*order", re.IGNORECASE)

#: The only markers that make an order-shaped function name acceptable. A
#: simulated order never leaves the process; a real one is the thing QCF must
#: not be able to do.
_SIMULATION_MARKERS: Final[frozenset[str]] = frozenset({"simulated", "paper"})

#: Files whose absence means the Stage 00 foundation is incomplete.
REQUIRED_FILES: Final[tuple[str, ...]] = (
    ".editorconfig",
    ".env.example",
    ".gitattributes",
    ".gitignore",
    ".pre-commit-config.yaml",
    ".secrets.baseline",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE_POLICY.md",
    "README.md",
    "SECURITY.md",
    "config/base.example.yaml",
    "docs/architecture/decisions/0000-adr-process.md",
    "docs/architecture/layering-rules.md",
    "docs/architecture/target-layout.md",
    "docs/project-state.md",
    "docs/stages/roadmap.md",
    "pyproject.toml",
    "src/qcf/__init__.py",
    "src/qcf/py.typed",
    "uv.lock",
)

#: Paths that may be tracked under `data/`. Nothing else, ever.
ALLOWED_DATA_FILES: Final[frozenset[str]] = frozenset(
    {
        "data/README.md",
        "data/raw/.gitkeep",
        "data/interim/.gitkeep",
        "data/processed/.gitkeep",
        "data/quarantine/.gitkeep",
    }
)

#: Lines carrying this marker may mention the incorrect product code `E6`,
#: because saying which spelling is wrong requires writing it once.
E6_ALLOW_MARKER: Final = "qcf:allow-E6"
_E6_TOKEN: Final = re.compile(r"\bE6\b")

_MARKDOWN_LINK: Final = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

#: Paths exempt from content scans. The checker must be able to name the
#: spellings it forbids, and tests must be able to construct violations; neither
#: is a violation itself.
SELF_AND_TESTS: Final[tuple[str, ...]] = ("scripts/check_project_boundary.py", "tests/")

_SKIPPED_DIRECTORIES: Final[frozenset[str]] = frozenset(
    {".git", ".venv", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "htmlcov"}
)


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one boundary check."""

    name: str
    status: Status
    details: tuple[str, ...] = field(default_factory=tuple)


def _walk(root: Path, suffix: str) -> Iterator[Path]:
    """Yield files under ``root`` with ``suffix``, skipping generated trees."""
    for path in sorted(root.rglob(f"*{suffix}")):
        if any(part in _SKIPPED_DIRECTORIES for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def _is_self_or_test(relative: str) -> bool:
    """Return ``True`` for the checker itself and for test modules."""
    return relative.startswith(SELF_AND_TESTS)


def _imported_modules(source: str) -> Iterator[str]:
    """Yield dotted module names imported by ``source``.

    Import statements are read from the syntax tree, so prose, string literals,
    and this file's own policy lists cannot trigger a match.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module


def _matches_forbidden(module: str, forbidden: Iterable[str]) -> str | None:
    """Return the forbidden entry ``module`` falls under, if any."""
    parts = module.split(".")
    prefixes = {".".join(parts[: index + 1]) for index in range(len(parts))}
    for entry in forbidden:
        if entry in prefixes:
            return entry
    return None


def _git_tracked_files(root: Path) -> list[str] | None:
    """Return tracked paths, or ``None`` when git metadata is unavailable."""
    if not (root / ".git").exists():
        return None
    try:
        # A fixed argument list, no shell, no network: this reads local git
        # metadata only.
        completed = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "ls-files"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return [line for line in completed.stdout.splitlines() if line]


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


def check_no_live_mode(root: Path) -> CheckResult:
    """Assert that ``OperatingMode`` declares no live member."""
    source_path = root / "src" / "qcf" / "core" / "enums.py"
    if not source_path.is_file():
        return CheckResult("no live operating mode", "FAIL", (f"missing {source_path}",))

    permitted = {"DISABLED", "RESEARCH", "BACKTEST", "REPLAY", "PAPER"}
    forbidden = {"LIVE", "REAL", "PRODUCTION", "FUNDED"}
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "OperatingMode":
            continue
        members = {
            target.id
            for statement in node.body
            if isinstance(statement, ast.Assign)
            for target in statement.targets
            if isinstance(target, ast.Name)
        }
        problems.extend(
            f"OperatingMode declares forbidden member {name!r}"
            for name in sorted(members & forbidden)
        )
        if members != permitted:
            problems.append(
                f"OperatingMode members are {sorted(members)}, expected {sorted(permitted)}"
            )
    if problems:
        return CheckResult("no live operating mode", "FAIL", tuple(problems))
    return CheckResult("no live operating mode", "PASS")


def check_no_forbidden_imports(root: Path) -> CheckResult:
    """Assert that no module imports a broker, exchange, or market-data client."""
    problems: list[str] = []
    for path in _walk(root, ".py"):
        relative = path.relative_to(root).as_posix()
        # The checker's own policy lists are string literals, not imports, so
        # AST inspection already excludes them. The explicit skip keeps the
        # intent obvious to a reader.
        if relative == SELF_AND_TESTS[0]:
            continue
        in_package = relative.startswith("src/qcf/")
        forbidden = (
            FORBIDDEN_CLIENT_MODULES | FORBIDDEN_NETWORK_MODULES
            if in_package
            else FORBIDDEN_CLIENT_MODULES
        )
        for module in _imported_modules(path.read_text(encoding="utf-8")):
            hit = _matches_forbidden(module, forbidden)
            if hit is not None:
                problems.append(f"{relative} imports {module!r} (forbidden: {hit!r})")
    if problems:
        return CheckResult("no broker or network client imports", "FAIL", tuple(problems))
    return CheckResult("no broker or network client imports", "PASS")


def check_no_real_order_functions(root: Path) -> CheckResult:
    """Assert that no function in the package is shaped like an order transmitter.

    A name is accepted only if it marks itself as simulated or paper. The
    allowlist is exactly those two words, because every other qualifier -- helper,
    internal, wrapper -- would let a real path in under a reassuring name.
    """
    package = root / "src" / "qcf"
    if not package.is_dir():
        return CheckResult("no real-order transmission path", "SKIP", ("src/qcf is absent",))
    problems: list[str] = []
    for path in _walk(package, ".py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            problems.append(f"{path.relative_to(root).as_posix()} is not parseable: {exc.msg}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            normalised = node.name.replace("_", "").lower()
            if not _ORDER_FUNCTION.search(normalised):
                continue
            if any(marker in node.name.lower() for marker in _SIMULATION_MARKERS):
                continue
            problems.append(
                f"{path.relative_to(root).as_posix()}:{node.lineno} defines {node.name!r}, "
                f"which names order transmission without a simulation marker"
            )
    if problems:
        return CheckResult("no real-order transmission path", "FAIL", tuple(problems))
    return CheckResult("no real-order transmission path", "PASS")


def check_no_tracked_env_file(root: Path) -> CheckResult:
    """Assert that no `.env` file is tracked."""
    tracked = _git_tracked_files(root)
    if tracked is None:
        return CheckResult("no tracked .env file", "SKIP", ("git metadata unavailable",))
    offenders = [
        path
        for path in tracked
        if Path(path).name == ".env" or Path(path).name.startswith(".env.")
        if Path(path).name != ".env.example"
    ]
    if offenders:
        return CheckResult("no tracked .env file", "FAIL", tuple(sorted(offenders)))
    return CheckResult("no tracked .env file", "PASS")


def check_no_tracked_market_data(root: Path) -> CheckResult:
    """Assert that only the documented skeleton is tracked under ``data/``."""
    tracked = _git_tracked_files(root)
    if tracked is None:
        return CheckResult("no tracked market data", "SKIP", ("git metadata unavailable",))
    offenders = sorted(
        path for path in tracked if path.startswith("data/") and path not in ALLOWED_DATA_FILES
    )
    if offenders:
        return CheckResult("no tracked market data", "FAIL", tuple(offenders))
    return CheckResult("no tracked market data", "PASS")


def check_required_files_exist(root: Path) -> CheckResult:
    """Assert that every file the Stage 00 foundation depends on is present."""
    missing = tuple(name for name in REQUIRED_FILES if not (root / name).is_file())
    if missing:
        return CheckResult("required files present", "FAIL", missing)
    return CheckResult("required files present", "PASS")


def check_package_imports(root: Path) -> CheckResult:
    """Assert that the installed package imports.

    This validates the installed distribution rather than ``root``; a source
    tree that only imports because the working directory happens to contain it
    is not the thing that ships.
    """
    del root
    problems: list[str] = []
    for module in ("qcf", "qcf.core.config", "qcf.core.enums", "qcf.core.fingerprint"):
        try:
            importlib.import_module(module)
        except ImportError as exc:
            problems.append(f"cannot import {module}: {exc}")
    if problems:
        return CheckResult("package imports", "FAIL", tuple(problems))
    return CheckResult("package imports", "PASS")


def check_example_config_validates(root: Path) -> CheckResult:
    """Assert that the committed example configuration still validates."""
    path = root / "config" / "base.example.yaml"
    if not path.is_file():
        return CheckResult("example configuration validates", "FAIL", (f"missing {path}",))
    try:
        # Imported here on purpose: the checker must still run and report a
        # failure when the package is not installed, rather than failing to start.
        from qcf.core.config import AppConfig  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - covered by check_package_imports
        return CheckResult("example configuration validates", "SKIP", (str(exc),))
    try:
        AppConfig.load(path)
    except Exception as exc:
        return CheckResult("example configuration validates", "FAIL", (str(exc),))
    return CheckResult("example configuration validates", "PASS")


def check_internal_timezone_is_utc(root: Path) -> CheckResult:
    """Assert that the internal timezone is fixed to UTC and cannot be configured away."""
    problems: list[str] = []
    path = root / "config" / "base.example.yaml"
    if path.is_file() and "timezone: UTC" not in path.read_text(encoding="utf-8"):
        problems.append("config/base.example.yaml does not set timezone: UTC")
    try:
        # Deferred for the same reason as above.
        from qcf.core.config import AppConfig  # noqa: PLC0415
        from qcf.core.exceptions import ConfigurationError  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - covered by check_package_imports
        return CheckResult("internal timezone is UTC", "SKIP", (str(exc),))
    try:
        AppConfig.load(timezone="America/New_York")
    except ConfigurationError:
        pass
    else:
        problems.append("a non-UTC internal timezone was accepted")
    if problems:
        return CheckResult("internal timezone is UTC", "FAIL", tuple(problems))
    return CheckResult("internal timezone is UTC", "PASS")


def check_product_code_terminology(root: Path) -> CheckResult:
    """Assert the CME Euro FX product code is written ``6E``, never ``E6``.

    Lines carrying the documented marker are exempt, because stating which
    spelling is wrong requires writing the wrong one exactly once.
    """
    problems: list[str] = []
    readme = root / "README.md"
    if readme.is_file() and "6E" not in readme.read_text(encoding="utf-8"):
        problems.append("README.md never names the product code 6E")
    for suffix in (".md", ".py", ".yaml", ".yml", ".toml"):
        for path in _walk(root, suffix):
            if _is_self_or_test(path.relative_to(root).as_posix()):
                continue
            for number, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
            ):
                if E6_ALLOW_MARKER in line:
                    continue
                if _E6_TOKEN.search(line):
                    problems.append(
                        f"{path.relative_to(root).as_posix()}:{number} writes 'E6'; "
                        f"the CME Euro FX product code is '6E'"
                    )
    if problems:
        return CheckResult("product code terminology", "FAIL", tuple(problems))
    return CheckResult("product code terminology", "PASS")


def check_documentation_links(root: Path) -> CheckResult:
    """Assert that relative markdown links resolve to files that exist."""
    problems: list[str] = []
    for path in _walk(root, ".md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _MARKDOWN_LINK.finditer(text):
            target = match.group(1).strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "#", "<")):
                continue
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                problems.append(f"{path.relative_to(root).as_posix()} links to missing {target!r}")
    if problems:
        return CheckResult("documentation links resolve", "FAIL", tuple(problems))
    return CheckResult("documentation links resolve", "PASS")


ALL_CHECKS: Final = (
    check_no_live_mode,
    check_no_forbidden_imports,
    check_no_real_order_functions,
    check_no_tracked_env_file,
    check_no_tracked_market_data,
    check_required_files_exist,
    check_package_imports,
    check_example_config_validates,
    check_internal_timezone_is_utc,
    check_product_code_terminology,
    check_documentation_links,
)


def run_all_checks(root: Path) -> list[CheckResult]:
    """Run every boundary check against ``root``."""
    return [check(root) for check in ALL_CHECKS]


def main(argv: list[str] | None = None) -> int:
    """Run the checks and report. Returns zero only if none failed."""
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]

    print(f"QCF project boundary check — {root}")
    results = run_all_checks(root)
    for result in results:
        print(f"  [{result.status:<4}] {result.name}")
        for detail in result.details:
            print(f"         - {detail}")

    failed = [result for result in results if result.status == "FAIL"]
    skipped = [result for result in results if result.status == "SKIP"]
    print(
        f"\n{len(results) - len(failed) - len(skipped)} passed, "
        f"{len(failed)} failed, {len(skipped)} skipped"
    )
    if failed:
        print("\nBOUNDARY CHECK FAILED")
        return 1
    print("\nBoundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
