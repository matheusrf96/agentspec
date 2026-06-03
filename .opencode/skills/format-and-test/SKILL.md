# Format and Test Pipeline

Runs the complete code quality pipeline for AgentSpec.

## Order

1. `ruff check .` — lint check
2. `ruff format --check .` — format check
3. `flake8 agentspec/ tests/` — flake8 lint
4. `pyright agentspec/ tests/` — type check
5. `python -m pytest tests/ -v --cov=agentspec --cov-fail-under=80` — full test suite + coverage

## Quick Shortcuts

| Command | Action |
|---------|--------|
| `ruff check . && ruff format --check .` | Ruff lint + format |
| `ruff check . && ruff format --check . && flake8 agentspec/ tests/ && pyright agentspec/ tests/` | All checks |
| `python -m pytest tests/ -v` | Test only |

## Pre-Commit

To run automatically on every commit:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # first-time setup
```

## Coverage

Coverage is enforced at 80% minimum via `--cov-fail-under=80`. If coverage drops below the threshold, tests will fail.
