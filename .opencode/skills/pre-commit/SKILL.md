# Pre-commit Setup

Sets up pre-commit hooks for ruff, flake8, pyright, and pytest.

## The config already exists

The project already has a `.pre-commit-config.yaml` at the project root with all hooks configured.

## Commands

### 1. Install pre-commit

```bash
pip install pre-commit
```

### 2. Install the hooks

```bash
pre-commit install
```

### 3. Run on all files (first time)

```bash
pre-commit run --all-files
```

## What's configured

| Hook | Runs |
|------|------|
| `ruff` | Lint + auto-fix |
| `ruff-format` | Auto-format |
| `flake8` | PEP8 lint |
| `pyright` | Type check (local) |
| `pytest` | Test suite (local) |

## Manual Pre-Commit Checklist

If pre-commit is not installed, manually verify before every commit:

```bash
ruff check . && ruff format --check . && flake8 agentspec/ tests/ && pyright agentspec/ tests/
```

## Git Hook (alternative without pre-commit)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/sh
ruff check . && ruff format --check .
flake8 agentspec/ tests/
pyright agentspec/ tests/
python -m pytest tests/ -x --tb=short --cov=agentspec --cov-fail-under=80
```

Then `chmod +x .git/hooks/pre-commit`.
