# Review Gate — Flake8 Patterns

Enforces flake8-compliant Python patterns during code review. All new and modified code must pass these checks before being accepted.

## Gate Criteria

Every `.py` file in a review must pass:

| Check | Command | Fails If |
|-------|---------|----------|
| pycodestyle (E/W) | `flake8 <file>` | Indentation, spacing, blank lines, line length > 100 |
| PyFlakes (F) | `flake8 <file>` | Unused imports, undefined names, unused variables |
| Import order | `ruff check --select I <file>` | Imports not grouped (stdlib / third-party / local) |

## Review Checklist

Review each changed `.py` file for:

1. **Imports** — unused imports removed, grouped by stdlib/third-party/local
2. **Line length** — no line exceeds 100 characters
3. **Naming** — snake_case for functions/vars, PascalCase for classes, UPPER_CASE for constants
4. **Blank lines** — 2 blank lines before top-level classes/functions, 1 before methods
5. **Trailing whitespace** — none
6. **Unused variables** — remove or prefix with `_`
7. **Redundant code** — unused assignments, dead code removed

## Quick Commands

```bash
# Check a single file
flake8 path/to/file.py

# Check all reviewed files
flake8 agentspec/ tests/

# Also run ruff (stricter)
ruff check --select E,F,W,I path/to/file.py
```

## Blocking Issues

Block the review if any of these fail:
- `F401` — module imported but unused
- `F821` — undefined name
- `E302` — expected 2 blank lines (indicates structural issue)
- `E501` — line too long (readability)

## Non-Blocking (comment only)

- `W291` — trailing whitespace
- `W293` — blank line contains whitespace
- `E231` — missing whitespace after `,`

## Reference

This gate matches the project's `ruff` config in `pyproject.toml`:
```
select = ["E", "F", "W", "I"]
line-length = 100
```
