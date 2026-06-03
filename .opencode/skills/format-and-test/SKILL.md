# Format and Test Pipeline

Runs the complete code quality pipeline for AgentSpec.

## Order

1. `ruff check agentspec/ tests/` — lint check
2. `ruff format --check agentspec/ tests/` — format check (optional, only if user asks)
3. `python -m pytest tests/ -v --tb=short` — full test suite

## Quick Shortcuts

| Command | Action |
|---------|--------|
| `ruff check .` | Lint only |
| `python -m pytest tests/ -v` | Test only |
| `ruff check . && python -m pytest tests/ -v` | Both |

## Output

Report any lint errors or test failures clearly. For test failures, show the failing test name and error message.
