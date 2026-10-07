# SecFlow DEV MODE (always on)
Read AGENTS.md first. You are in DEV MODE:
1. Write NO new tests and touch nothing under tests/ (except M3 fixtures).
2. Run only: python -m ruff format --check . ; python -m ruff check . ; python -m mypy ;
   python -m bandit -r app -c pyproject.toml ; python -m pytest --no-cov -q
3. A failing existing test means you broke something: STOP, report, do not edit the test.
4. Edit ONLY files in your OWNERSHIP list. Otherwise write a "REQUEST TO OWNER" in your report.
5. Frozen contracts (ports, CommandRunner, ToolResult, snapshot schema) change only after owner approval.
6. No shell=True. No logging of paths, filenames, exception messages or tracebacks.
7. One phase/PR at a time. When done: report and STOP.
