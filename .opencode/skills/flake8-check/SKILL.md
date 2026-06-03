# Flake8 Check

Runs flake8 linting across the project to enforce PEP8 and code quality patterns.

## Commands

| Command | Action |
|---------|--------|
| `flake8 agentspec/ tests/` | Check all source and test files |
| `flake8 agentspec/` | Check only source code |
| `flake8 tests/` | Check only tests |
| `flake8 <path/to/file.py>` | Check a single file |

## Usage When Editing

After creating or modifying any `.py` file, always run:

```
flake8 <file>
```

Fix any reported violations. Common categories:

| Code | Rule | Meaning |
|------|------|---------|
| E1/E2/E3 | pycodestyle indent/whitespace | Bad indentation or spacing |
| E5 | pycodestyle line length | Line too long (>100 chars) |
| F4/F6 | pyflakes imports | Unused imports or undefined names |
| F8 | pyflakes name | Name defined but unused |
| W | warnings | Various style warnings |

## Common Fixes

| Issue | Fix |
|-------|-----|
| `E302 expected 2 blank lines` | Add blank line before class/function |
| `F401 imported but unused` | Remove unused import |
| `E501 line too long` | Break into multiple lines |
| `F841 local variable assigned but not used` | Remove or use the variable |

## Tooling Note

The project also uses `ruff` (same rules `E`, `F`, `W`, `I`). Run both to be safe:

```
ruff check . && flake8 agentspec/ tests/
```
