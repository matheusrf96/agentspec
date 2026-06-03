# MCP Servers

AgentSpec includes 6 MCP (Model Context Protocol) servers that provide tools for AI agents to interact with the evaluation framework. All servers communicate via JSON-RPC over stdio.

## Configuration

All servers are registered in `.mcp.json` at the project root:

```json
{
  "mcpServers": {
    "spec-manager": {
      "command": "python",
      "args": ["-m", "agentspec.mcp.spec_manager"]
    },
    ...
  }
}
```

To use with an MCP client, point it to `.mcp.json` or configure the servers individually.

## Server reference

### `spec-manager`

CRUD operations for YAML evaluation spec files.

| Tool | Input | Output | Description |
|------|-------|--------|-------------|
| `list_specs` | `path?` | `{specs}` | List spec files in a directory |
| `read_spec` | `path` | `{spec}` | Parse and return a spec file |
| `validate_spec` | `path` | `{valid, errors}` | Validate a spec file |
| `create_spec` | `name, output, model?, system_prompt?` | `{path, name}` | Generate a new spec file |
| `add_test` | `spec_path, name, prompt` | `{ok}` | Add a test case |
| `add_assertion` | `spec_path, test_name, type, ...` | `{ok}` | Add an assertion to a test |
| `remove_test` | `spec_path, test_name` | `{ok}` | Remove a test case |
| `remove_assertion` | `spec_path, test_name, index` | `{ok}` | Remove an assertion by index |

### `eval-runner`

Run evaluations against real LLM APIs.

| Tool | Input | Output | Description |
|------|-------|--------|-------------|
| `run_eval` | `spec_path, model?, base_url?, api_key?` | `{spec_name, summary, results}` | Run full evaluation |
| `run_single_test` | `spec_path, test_name, ...` | `{spec_name, summary, results}` | Run a single test case |

### `results-store`

Persist and query evaluation history. Storage at `~/.agentspec/results/`.

| Tool | Input | Output | Description |
|------|-------|--------|-------------|
| `save_result` | `report, spec_path?` | `{run_id}` | Save a result |
| `list_runs` | `limit?, spec_name?` | `{runs}` | List past runs |
| `get_run` | `run_id` | `{report, timestamp}` | Get a run's details |
| `compare_runs` | `id1, id2` | `{differences}` | Compare two runs |
| `get_trends` | `spec_name?, days?` | `{trends}` | Pass rate trends over time |

### `mock-agent`

Test specs without API keys using configurable mock behaviors.

| Tool | Input | Output | Description |
|------|-------|--------|-------------|
| `create_mock` | `name?` | `{agent_id}` | Create a mock agent |
| `set_behavior` | `agent_id, behaviors` | `{ok}` | Set response behaviors |
| `run_with_mock` | `spec_path, agent_id` | `{report}` | Run spec against mock |
| `list_behaviors` | — | `{templates}` | List behavior templates |
| `destroy_mock` | `agent_id` | `{ok}` | Destroy a mock agent |

Behaviors support sequential scripting with `step` and conditional triggers with `on`:

```json
{
  "step": 0,
  "on": {"tool_name": "get_weather"},
  "response": {
    "text": "The weather is sunny",
    "tool_calls": [{"name": "get_weather", "args": {"city": "London"}}],
    "latency_seconds": 0.5
  }
}
```

### `spec-templates`

Pre-built evaluation templates for common agent patterns.

| Tool | Input | Output | Description |
|------|-------|--------|-------------|
| `list_templates` | — | `{templates}` | List available templates |
| `get_template` | `name` | `{name, spec}` | Get a template |
| `apply_template` | `name, output_path, overrides?` | `{path, name}` | Create spec from template |

Templates available:

| Template | Tests | Description |
|----------|-------|-------------|
| `tool-calling` | 3 | Basic tool-use evaluation |
| `rag` | 2 | RAG quality with citation checks |
| `chat` | 3 | General chat with safety tests |
| `code-gen` | 2 | Code generation correctness |
| `structured-output` | 1 | JSON schema compliance |

### `tests-runner`

Run AgentSpec's own test suite (pytest + ruff).

| Tool | Input | Output | Description |
|------|-------|--------|-------------|
| `run_pytest` | `path?, marker?, verbose?` | `{exit_code, passed, failed, errors}` | Run pytest |
| `run_ruff` | `path?` | `{exit_code, passed}` | Run ruff linter |
| `run_all` | `path?` | `{lint, tests}` | Run both sequentially |
