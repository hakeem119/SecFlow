# DEV MODE Rules

When `gate_mode.txt` is set to `dev` or scripts run with `--dev`:
- The Quality Gate will skip coverage checks (`pytest --no-cov`).
- M1/M2 are restricted from touching tests (other than adding their own fixtures) per `check_ownership.py`.
