# FAQ

## General

### What is AgentSpec?

AgentSpec is a spec-driven evaluation framework for AI agents. You define expected agent behaviors as YAML specs, run agents against test cases, and get scored results.

### How is this different from regular testing?

LLM agents are probabilistic. Traditional assertion testing doesn't account for LLM variability. AgentSpec provides specialized assertion types for agent behavior: tool calls, output patterns, latency, JSON schema compliance, and more.

## Setup

### Do I need an API key?

Only if you want to run evaluations against a real LLM. Set `DEEPSEEK_API_KEY` (or use `--api-key`). For testing spec syntax without an API key, use:

```bash
agentspec validate my-spec.yaml
```

Or use the mock-agent MCP server.

### Which LLM providers are supported?

Any OpenAI-compatible API. DeepSeek, OpenAI, Together AI, Ollama (local), and others. Set the base URL with `LLM_BASE_URL` or `--base-url`.

## Specs

### How do I write a spec?

```bash
agentspec init > my-spec.yaml
```

Or use the `spec-templates` MCP server for pre-built templates.

### Can I reuse specs across different agents?

Yes. The spec format is agent-agnostic. Change the `model` field or use `--model` at runtime.

### What assertion types are available?

See [Assertion Types](assertion-types.md) for full documentation.

## MCP Servers

### What are MCP servers?

MCP (Model Context Protocol) servers let AI agents interact with AgentSpec programmatically. They provide tools for spec management, evaluation, results tracking, and more.

### How do I start an MCP server?

Each server runs as a standalone process:

```bash
python -m agentspec.mcp.spec_manager
```

They're also registered in `.mcp.json` for automatic discovery.

## Troubleshooting

### Tests fail with "Missing credentials"

You need an API key. Set `DEEPSEEK_API_KEY` or use the mock-agent MCP server for testing without a real LLM.

### YAML parsing errors

Use `agentspec validate` to check your spec file. Common issues:

- Invalid indentation (YAML is indentation-sensitive)
- Unknown assertion types
- Missing required fields

### Tests are slow

Set `--model` to a faster model, or use the mock-agent MCP server during development.

### Ruff reports errors unrelated to my changes

Run `ruff check . --fix` to auto-fix, or check that your editor is respecting the project's ruff config in `pyproject.toml`.
