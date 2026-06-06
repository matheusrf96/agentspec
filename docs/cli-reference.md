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

Run agent evaluation against a spec file or directory.

```bash
agentspec run <spec_file_or_dir> [options]
```

**Arguments:**

| Arg | Description |
|-----|-------------|
| `spec_file_or_dir` | Path to a YAML spec file or a directory of `.yaml` files (required) |

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | spec value | Override model name |
| `--base-url` | `DEEPSEEK_API` env | Override API base URL |
| `--api-key` | `DEEPSEEK_API_KEY` env | Override API key |
| `--verbose` / `-v` | `False` | Show per-assertion details |
| `--output` / `-o` | `terminal` | Output format: `terminal`, `json`, or `html` |
| `--concurrency` / `-c` | `1` | Max parallel tests (0 = unlimited) |
| `--no-progress` | `False` | Disable progress bar |

**Examples:**

```bash
# Basic run
agentspec run examples/tool-calling.yaml

# Run all specs in a directory
agentspec run ./specs/

# Custom model with verbose output
agentspec run my-spec.yaml --model gpt-4 --verbose

# JSON output for programmatic use
agentspec run my-spec.yaml --output json

# HTML report
agentspec run my-spec.yaml --output html

# Concurrent evaluation
agentspec run my-spec.yaml --concurrency 5

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

### `agentspec list`

List all specs in a directory with test counts.

```bash
agentspec list [path]
```

**Examples:**

```bash
# List specs in current directory
agentspec list

# List specs in a specific directory
agentspec list ./examples/
```

### `agentspec compare`

Compare two evaluation runs and show the differences.

```bash
agentspec compare <run_id_1> <run_id_2>
```

### `agentspec results`

Manage evaluation run results.

```bash
agentspec results history [--limit N]
agentspec results get <run_id>
agentspec results export <run_id> [--format csv|json]
agentspec results prune [--keep N]
```

### `agentspec completion`

Generate shell completion script.

```bash
agentspec completion bash
agentspec completion zsh
agentspec completion fish
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | API key for DeepSeek (or other provider) |
| `LLM_BASE_URL` | `https://api.deepseek.com` | API base URL |
| `ANTHROPIC_API_KEY` | — | API key for Anthropic Claude |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid spec, missing file, API error) |
