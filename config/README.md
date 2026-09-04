# Configuration

Typed, immutable, validated configuration. See
[`../src/qcf/core/config.py`](../src/qcf/core/config.py) for the model and
[`../docs/architecture/decisions/0003-configuration-and-unknown-values.md`](../docs/architecture/decisions/0003-configuration-and-unknown-values.md)
for why it is shaped this way.

## Files

| File | Purpose |
| --- | --- |
| `base.example.yaml` | Every Stage 00 setting with its default and an explanation |

Files for the `research`, `replay`, and `paper` modes are **not** present. They
would require configuration schemas that do not exist yet, and writing them now
would mean inventing financial fields that no stage has validated. Each arrives
with the stage that owns it.

## Precedence

Highest first:

1. Explicit keyword arguments to `AppConfig.load(...)`
2. `QCF_`-prefixed environment variables, for example `QCF_MODE=RESEARCH`
3. The YAML file passed to `AppConfig.load(path)`
4. Field defaults

Dotenv files and secret directories are deliberately not consulted. QCF
configuration carries no secrets, so reading credential sources would only
create somewhere for one to hide.

## Rules

- **No secrets.** No credentials, API keys, account identifiers, or broker
  endpoints. See [`../SECURITY.md`](../SECURITY.md).
- **No financial parameters yet.** No fees, commissions, risk limits, profit
  targets, or strategy parameters. Those belong to the stages that define them
  with provenance and versioning.
- **Unknown keys are rejected.** Adding a key here without adding the field to
  the model is a validation error.
- **Unknown values stay `UNKNOWN`.** Never substitute `0`, `null`, `""`, or
  `NaN` for a value that has not been established.
