# CLI Reference

## Installation

```bash
pip install agentspec
```

Or with dev dependencies:

```bash
pip install "agentspec[dev]"
```

## Commands

### `agentspec run`

Run agent evaluation against a spec file.

```bash
agentspec run <spec_file> [options]
```

**Arguments:**

| Arg | Description |
|-----|-------------|
| `spec_file` | Path to a YAML spec file (required) |

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | spec value | Override model name |
| `--base-url` | `DEEPSEEK_API` env | Override API base URL |
| `--api-key` | `DEEPSEEK_API_KEY` env | Override API key |
| `--verbose` / `-v` | `False` | Show per-assertion details |
| `--output` / `-o` | `terminal` | Output format: `terminal` or `json` |

**Examples:**

```bash
# Basic run
agentspec run examples/tool-calling.yaml

# Custom model with verbose output
agentspec run my-spec.yaml --model gpt-4 --verbose

# JSON output for programmatic use
agentspec run my-spec.yaml --output json

# Override API endpoint
agentspec run my-spec.yaml --base-url https://api.openai.com/v1
```

### `agentspec validate`

Validate a spec file without running it.

```bash
agentspec validate <spec_file>
```

**Examples:**

```bash
agentspec validate examples/tool-calling.yaml
# ✅ Spec 'Tool Calling Agent Eval' is valid (3 test(s))

agentspec validate broken.yaml
# ❌ Invalid spec: ...
```

### `agentspec init`

Generate a template spec YAML file.

```bash
agentspec init [options]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--name` | `My Agent Eval` | Spec name |
| `--model` | `deepseek-v4-pro` | Default model |

**Examples:**

```bash
# Generate to stdout
agentspec init > my-agent.yaml

# Custom name and model
agentspec init --name "Financial Agent Eval" --model gpt-4
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | API key for DeepSeek (or other provider) |
| `LLM_BASE_URL` | `https://api.deepseek.com` | API base URL |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid spec, missing file, API error) |
