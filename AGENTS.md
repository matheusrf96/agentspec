# AGENTS.md - AgentSpec Project Guide

**Spec-driven evaluation framework for AI agents.** Define agent behaviors as YAML specs, run agents against test cases, and get scored results.

## Quick Start

```bash
pip install -e ".[dev]"          # install with dev deps
agentspec run examples/tool-calling.yaml  # run eval
agentspec validate examples/tool-calling.yaml  # validate spec
agentspec init --name "My Eval" > my-spec.yaml  # create spec
python -m pytest tests/ -v       # run tests
ruff check .                     # lint
```

## Project Structure

```
agentspec/
  agentspec/
    spec.py           # Pydantic models for specs (Spec, TestCase, Assertion types)
    assertions.py     # Evaluation logic for all 6 assertion types
    runner.py         # TestRunner orchestrates agent runs + assertion evaluation
    scorer.py         # TestReport / TestCaseResult / Summary dataclasses
    reporter.py       # Terminal + JSON output rendering (rich tables)
    cli.py            # Click CLI: run, validate, init
    adapters/         # AgentAdapter interface + OpenAICompatibleAdapter + MockAdapter
    mcp/              # 6 MCP servers: spec-manager, eval-runner, results-store, mock-agent, spec-templates, tests-runner
  tests/
    test_assertions.py   # 14 tests for assertion evaluation
    test_spec.py         # 4 tests for YAML parsing
    test_reporter.py     # 21 tests for terminal + JSON report output
    test_cli.py          # 18 tests for CLI commands (CliRunner)
    test_openai_adapter.py # 16 tests for API adapter parsing
    mcp/                 # 118 tests for all 6 MCP servers
  docs/
    index.md, architecture.md, assertion-types.md, cli-reference.md,
    mcp-servers.md, contributing.md, faq.md
  examples/
    tool-calling.yaml    # Example spec
  .mcp.json              # MCP server registry (6 servers)
```

## Architecture

```
spec.yaml → SpecParser → TestRunner → Agent (OpenAI-compatible API) → Assertions → Scored report
```

Layers:
- **Data**: `spec.py` — YAML → Pydantic models
- **Evaluation**: `assertions.py` — per-assertion logic (tool_called, output_contains, etc.)
- **Orchestration**: `runner.py` — iterate tests, call adapter, evaluate
- **Reporting**: `scorer.py` + `reporter.py` — results → terminal/JSON
- **Interface**: `cli.py` — Click-based CLI; `mcp/` — JSON-RPC MCP servers

## Key Conventions

- **Line length**: 100 chars (ruff config)
- **Python**: 3.10+, strict typing
- **Testing**: pytest with pytest-asyncio for async tests
- **Linting**: ruff (E, F, W, I rules)
- **No markdown files** in project root except AGENTS.md (RULE #0)

## MCP Servers (registered in .mcp.json)

| Server | Purpose |
|--------|---------|
| `spec-manager` | CRUD for spec files (list, read, validate, create, add tests/assertions) |
| `eval-runner` | Run evaluations against real LLM APIs |
| `results-store` | Persist results to JSON files, query history, compare runs |
| `mock-agent` | Test specs without API keys using configurable mock behaviors |
| `spec-templates` | 5 pre-built templates (tool-calling, rag, chat, code-gen, structured-output) |
| `tests-runner` | Run pytest + ruff on agentspec itself |

## Assertion Types

| Type | Description |
|------|-------------|
| `tool_called` | Assert a tool was called (optionally with matching args) |
| `output_contains` | Substring match (case-sensitive or not) |
| `output_contains_any` | Any/all of a list of substrings |
| `output_matches` | Regex pattern match |
| `latency_under` | Response time under threshold |
| `output_json_schema` | Output is valid JSON matching a JSON Schema |

## Dev Commands

| Command | Action |
|---------|--------|
| `python -m pytest tests/ -v` | Run all tests |
| `ruff check .` | Lint |
| `pip install -e ".[dev]"` | Install with dev deps |
