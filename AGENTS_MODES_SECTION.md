## Modes (added by M3; overrides Sections 13 and 16 while DEV MODE is active)

- DEV MODE (Phases 4-10)
  - Do NOT create or edit anything under tests/ (M3 may add fixtures only).
  - Allowed checks: ruff format --check, ruff check, mypy --strict, bandit,
    and `python -m pytest --no-cov -q` (existing tests only, as a regression guard).
  - If an existing test fails after your change: STOP and report. Never edit or delete it.
  - Never edit pyproject.toml, ruff config, per-file-ignores, or frozen contracts.
  - Edit only files listed under your OWNERSHIP. Anything else: write "REQUEST TO OWNER".
  - Final report must state: "New tests: not written (DEV MODE)".
- VERIFY MODE (Phase 11): write tests, coverage 100%, full quality gate.

Pattern Map change: ToolRunner (CommandRunner Protocol + implementation) moves from Phase 5
to "needed from Phase 4". Owner: M2. M1 codes against the Protocol with a FakeCommandRunner.
