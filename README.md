# agentspec

**Spec-driven evaluation framework for AI agents.** Define agent behaviors as YAML specs, run agents against test cases, and get scored results. Built for DeepSeek V4 and any OpenAI-compatible API.

```bash
pip install -e .
agentspec run examples/tool-calling.yaml
```

## Why

Testing AI agents is hard. Agent behavior is probabilistic, tool selection is unpredictable, and output format varies. `agentspec` brings software engineering rigor to agent development with **spec-driven evaluation** — the same philosophy as spec-driven development (SDD), applied to agents.

## How it works

```
spec.yaml → SpecParser → TestRunner → Agent (OpenAI-compatible API) → Assertions → Scored report
```

1. Write a YAML spec describing expected agent behavior
2. `agentspec` runs each test case against the agent
3. Assertions evaluate tool usage, output content, latency, and more
4. A scored report shows pass/fail per test with details

## Quick start

```bash
# Install
pip install -e .

# Set your API key
export DEEPSEEK_API_KEY=sk-...

# Run the built-in example spec
agentspec run examples/tool-calling.yaml

# Validate a spec without running
agentspec validate examples/tool-calling.yaml

# Generate a template spec
agentspec init --name "My Agent" > my-agent.yaml
```

## CLI reference

```
agentspec run <file>            Run agent evaluation against a spec
  --model                       Override model (default: deepseek-v4-pro)
  --base-url                    Override API base URL
  --verbose / -v                Show per-assertion details
  --output terminal|json        Output format (default: terminal)

agentspec validate <file>       Validate spec YAML without running

agentspec init                  Generate a template spec.yaml
  --name                        Spec name (default: "My Agent Eval")
  --model                       Default model (default: deepseek-v4-pro)
```

## Spec format

```yaml
name: "Financial Agent Eval"
model: deepseek-v4-pro
system_prompt: "You are a financial assistant."

tests:
  - name: "fetches stock price"
    prompt: "What is AAPL at?"
    assertions:
      - type: tool_called
        tool_name: get_stock_price
      - type: output_matches
        pattern: '\$\d+\.?\d*'
      - type: latency_under
        max_seconds: 30

  - name: "handles unknown gracefully"
    prompt: "What is FAKE123?"
    assertions:
      - type: output_contains_any
        values: ["not found", "unknown", "invalid"]
        match: any
```

### Assertion types

| Type | Fields | Description |
|------|--------|-------------|
| `tool_called` | `tool_name`, `args?` | Assert a specific tool was called (optionally with matching args) |
| `output_contains` | `value`, `case_sensitive?` | Assert output contains a substring |
| `output_contains_any` | `values`, `match: any\|all?` | Assert output contains at least one (or all) substrings |
| `output_matches` | `pattern` | Assert output matches a regex pattern |
| `latency_under` | `max_seconds` | Assert response time under threshold |
| `output_json_schema` | `schema` | Assert output is valid JSON matching a JSON Schema |

## Configuration

| Environment variable | Default | Description |
|---------------------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | API key for DeepSeek (or other provider) |
| `LLM_BASE_URL` | `https://api.deepseek.com` | API base URL for any OpenAI-compatible provider |

Override per-run with `--model` and `--base-url` flags.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ spec.yaml                                            │
│  ├── name, model, system_prompt                       │
│  └── tests[]                                         │
│       ├── name, prompt                                │
│       └── assertions[]                                │
└─────────┬───────────────────────────────────────────┘
          │ spec.parse()
          ▼
┌─────────────────────┐
│  TestRunner          │
│  ├── iterates tests  │
│  └── calls adapter   │
└─────────┬───────────┘
          │ adapter.run()
          ▼
┌──────────────────────┐
│  Agent (DeepSeek V4)  │
│  └── returns response │
└─────────┬────────────┘
          │ evaluate_assertion()
          ▼
┌──────────────────────┐
│  Scorer + Reporter    │
│  └── terminal / JSON  │
└──────────────────────┘
```

### Adding new assertion types

1. Add the enum value to `AssertionType` in `agentspec/spec.py`
2. Create a Pydantic model for the assertion with `type: Literal[AssertionType.NEW_TYPE]`
3. Add it to the `Assertion` union type
4. Add an `_eval_new_type()` function in `agentspec/assertions.py`
5. Add the match case to `evaluate_assertion()`

### Adding new adapters

1. Create a new file in `agentspec/adapters/` that inherits `AgentAdapter`
2. Implement the `run()` async method
3. Add `--adapter` CLI option to `agentspec/cli.py`

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=agentspec
```

## Roadmap

See the full [roadmap](docs/roadmap.md) in the docs for planned features across all tiers.
