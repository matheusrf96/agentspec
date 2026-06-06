# Contributing

## Setup

```bash
# Clone and install
git clone <repo>
cd agentspec
pip install -e ".[dev]"

# Verify installation
agentspec --help
python -m pytest tests/ -v
```

## Development workflow

### 1. Make changes

Edit files under `agentspec/` for the main package, `tests/` for tests, and `docs/` for documentation.

### 2. Lint

```bash
ruff check .
ruff format --check .
flake8 agentspec/ tests/
```

We use ruff with rules E, F, W, I and flake8. Line length is 88 characters.

### 3. Type check

```bash
pyright agentspec/ tests/
```

### 4. Test

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=agentspec

# Run a specific test file
python -m pytest tests/test_spec.py -v
```

### 5. Check coverage

Target coverage is 95%+. Run `python -m pytest tests/ --cov=agentspec --cov-fail-under=95` to verify.

## Code conventions

- **Python 3.10+** with strict typing — all functions must have type annotations
- **Line length**: 88 characters
- **Imports**: stdlib → third-party → local (ruff handles sorting)
- **Async**: Use `async def` for adapter methods and MCP handlers. Mark async tests with `@pytest.mark.asyncio`
- **Testing**: Use `pytest` with `pytest-asyncio`. Prefer `unittest.mock` over monkeypatching. Use `CliRunner` for CLI tests

## Adding a new assertion type

1. Add a `Literal` member to `AssertionType` in `agentspec/spec.py`
2. Create a Pydantic model for the assertion with `type: Literal[...]`
3. Add it to the `Assertion` union type
4. Add an `_eval_*` function in `agentspec/assertions.py`
5. Add the match case to `evaluate_assertion()`
6. Add tests in `tests/test_assertions.py`

## Adding a new MCP server

1. Create `agentspec/mcp/<name>.py` using `BaseMcpServer` from `protocol.py`
2. Register tools with the `@srv.tool()` decorator
3. Create `tests/mcp/test_<name>.py` with tests for each tool
4. Register the server in `.mcp.json`
5. Verify with `ruff check`, `flake8`, `pyright`, and `pytest`

## PR checklist

- [ ] Code lints with `ruff check .`
- [ ] Formatting passes with `ruff format --check .`
- [ ] Type checks with `pyright agentspec/ tests/`
- [ ] All tests pass with `python -m pytest tests/ -v`
- [ ] Coverage is 95%+ with `python -m pytest tests/ --cov=agentspec --cov-fail-under=95`
- [ ] New code has tests covering happy path, validation errors, and edge cases
- [ ] Type annotations are complete
- [ ] Documentation updated if public API changed
