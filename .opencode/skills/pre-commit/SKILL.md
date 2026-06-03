# Pre-commit Flake8 Setup

Sets up pre-commit hooks to run flake8 (and ruff) before every commit.

## Commands

### 1. Install pre-commit

```bash
pip install pre-commit
```

### 2. Create `.pre-commit-config.yaml`

```bash
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pycqa/flake8
    rev: 7.1.0
    hooks:
      - id: flake8
        args: ["--max-line-length=100"]
        exclude: "^.opencode/|opencode.json"
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.11.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
EOF
```

### 3. Install the hooks

```bash
pre-commit install
```

### 4. Run on all files (first time)

```bash
pre-commit run --all-files
```

## Manual Pre-Commit Checklist

If pre-commit is not installed, manually verify before every commit:

```bash
ruff check .
flake8 agentspec/ tests/
```

## Git Hook (alternative without pre-commit)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/sh
ruff check .
flake8 agentspec/ tests/
python -m pytest tests/ -x --tb=short
```

Then `chmod +x .git/hooks/pre-commit`.
