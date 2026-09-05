# Development environment

## Requirements

- **Python 3.12 or newer.** Enforced by `requires-python`. Note that a machine's
  default `python3` may be older; select 3.12 explicitly.
- **[uv](https://docs.astral.sh/uv/)** for environment and dependency management.
- **git.**

Ruff, mypy, pytest, pre-commit, and detect-secrets are **development
dependencies**, not system tools. Versions installed globally are not the
project toolchain and are never cited as validation evidence — see
[ADR-0002](../architecture/decisions/0002-python-and-environment.md).

## Setup

```bash
git clone https://github.com/Zeorpo/qcf.git
cd qcf

# Create the environment from a 3.12 interpreter explicitly.
uv venv --python 3.12

# Install runtime and development dependencies from the committed lock.
uv sync --all-groups --frozen

# Install the git hooks.
uv run pre-commit install
```

`--frozen` installs the locked dependencies without updating `uv.lock`, and fails if the lock is
stale, rather than quietly resolving something newer.

### Windows PowerShell

```powershell
git clone https://github.com/Zeorpo/qcf.git
Set-Location qcf

uv venv --python 3.12
uv sync --all-groups --frozen
uv run pre-commit install
```

## Running things

Always through `uv run`, so commands execute against the locked environment
rather than whatever is first on `PATH`:

```bash
uv run python -c "import qcf; print(qcf.__version__)"
uv run pytest
uv run python scripts/check_project_boundary.py --strict
```

## Configuration

Copy `.env.example` to `.env` for local settings, or pass a YAML file:

```python
from qcf.core.config import AppConfig

config = AppConfig.load("config/base.example.yaml")
```

Precedence is explicit arguments, then `QCF_`-prefixed environment variables,
then the YAML file. `.env` is git-ignored and must never contain a credential —
QCF has nothing to authenticate against. See [`../../SECURITY.md`](../../SECURITY.md).

## Updating dependencies

```bash
uv lock --upgrade-package <name>
uv sync --all-groups --frozen
uv run pytest
```

Commit the resulting `uv.lock` change on its own, with the reason. A new
dependency additionally requires that the current stage import it; see
[`../../CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `ModuleNotFoundError: qcf` | The package is not installed in the environment. Run `uv sync --all-groups --frozen`. |
| `uv sync --frozen` fails | `uv.lock` is out of date with `pyproject.toml`. Run `uv lock` and review the diff. |
| Tests pass locally, fail in CI | A command was run outside `uv run`, or against a different Python version. CI runs 3.12 and 3.13. |
| Boundary check fails on a new file | Intended. Read the failure: it names the file and the rule. |
