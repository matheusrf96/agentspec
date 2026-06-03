# Typecheck Check (Pyright)

Runs pyright static type checking across the project.

## Commands

| Command | Action |
|---------|--------|
| `pyright agentspec/ tests/` | Check all source and test files |
| `pyright agentspec/` | Check only source code |
| `pyright tests/` | Check only tests |
| `pyright <path/to/file.py>` | Check a single file |

## Configuration

Pyright config is in `pyrightconfig.json` at project root:

- **mode**: `standard` (moderate strictness)
- **pythonVersion**: 3.10
- **Checks**: reportMissingImports, reportOptionalCall, reportArgumentType, reportAttributeAccessIssue, reportCallIssue, reportUndefinedVariable

## Common Pyright Suppressions

When pyright flags a line that is intentionally correct, add a comment:

```python
some_code()  # pyright: ignore
# Or for specific error codes:
some_attr  # pyright: ignore[reportAttributeAccessIssue]
```

## Running All Quality Checks

```bash
ruff check . && flake8 agentspec/ tests/ && pyright agentspec/ tests/
```
