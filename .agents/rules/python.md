---
trigger: glob
description: "Python standards for the SecFlow repository-analysis service."
globs: "**/*.py"
---

# Python Rules (summary of AGENTS.md sections 8 and 9)

- Python 3.12, full type hints, `mypy --strict` must pass.
- Pydantic models for every external contract and every cross-layer data structure.
- `pathlib` for all paths. Never concatenate path strings.
- Dependency injection at infrastructure boundaries. Compose with Protocols, avoid inheritance.
- Small functions, meaningful names, docstrings on public interfaces.
- Explicit exceptions only. No bare `except Exception` unless re-raised with context.
- No global mutable state, no hidden side effects, no untyped dicts across layers.
- All external processes live inside dedicated adapters (ToolRunner in Phase 5+).
- Add a design pattern only in the phase listed in the Pattern Map (AGENTS.md 8.1),
  with a one-sentence justification.
