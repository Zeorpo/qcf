"""Shared fixtures.

The repository root is placed on ``sys.path`` so that contract tests can import
``scripts.check_project_boundary``. The package under test is *not* imported
that way: ``qcf`` is imported from the installed distribution, so the tests
exercise what would actually ship rather than the source tree they happen to sit
beside.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog
from hypothesis import settings

# Property tests run derandomised: a suite that fails only sometimes cannot be
# used as evidence. Deadlines are disabled because a timing threshold would make
# outcomes depend on machine load.
settings.register_profile("qcf", derandomize=True, deadline=None)
settings.load_profile("qcf")

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def repo_root() -> Path:
    """Return the repository root."""
    return REPO_ROOT


@pytest.fixture(autouse=True)
def _reset_structlog() -> Iterator[None]:
    """Undo any logging configuration a test performs.

    structlog configuration and its context variables are process-global. Left
    in place they would make test outcomes depend on execution order, which is
    exactly the kind of nondeterminism the suite is meant to exclude.
    """
    yield
    structlog.contextvars.clear_contextvars()
    structlog.reset_defaults()


@pytest.fixture(autouse=True)
def _isolate_qcf_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every ``QCF_``-prefixed variable before each test.

    Configuration now fails closed on an unrecognised ``QCF_`` name (R-12), so
    an unrelated variable in the developer's shell would make unrelated tests
    fail — and, worse, a *matching* ambient variable would make them pass for
    the wrong reason. Clearing the namespace makes every run start from the same
    environment regardless of the machine. ``monkeypatch`` restores it
    afterwards, so the developer's shell is left exactly as it was.
    """
    for name in [key for key in os.environ if key.upper().startswith("QCF_")]:
        monkeypatch.delenv(name, raising=False)
