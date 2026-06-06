# Assertion Types

AgentSpec supports 10 assertion types for evaluating LLM agent behavior. Each type checks a different aspect of the agent's response.

## `tool_called`

Assert that an agent called a specific tool (optionally with matching arguments).

```yaml
- type: tool_called
  tool_name: get_stock_price
```

With argument matching:

```yaml
- type: tool_called
  tool_name: get_stock_price
  args:
    symbol: AAPL
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_name` | string | yes | Name of the tool to check for |
| `args` | dict | no | Expected arguments (partial match — checks that all specified args exist with matching values) |

## `output_contains`

Assert that the agent's text output contains a substring.

```yaml
- type: output_contains
  value: "hello"
  case_sensitive: true
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `value` | string | yes | — | Substring to search for |
| `case_sensitive` | bool | no | `true` | Whether the match is case-sensitive |

## `output_contains_any`

Assert that the agent's output contains at least one (or all) of a list of substrings.

```yaml
- type: output_contains_any
  values:
    - "not found"
    - "invalid"
    - "error"
  match: any
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `values` | string[] | yes | — | List of substrings to check |
| `match` | `"any"` or `"all"` | no | `"any"` | Whether to match any or all values |

## `output_matches`

Assert that the agent's output matches a regular expression.

```yaml
- type: output_matches
  pattern: '\$\d+\.?\d*'
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pattern` | string | yes | Regex pattern (Python `re.search`) |

## `latency_under`

Assert that the agent responded within a time threshold.

```yaml
- type: latency_under
  max_seconds: 30
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `max_seconds` | number | yes | Maximum response time in seconds (must be > 0) |

## `output_json_schema`

Assert that the agent's output is valid JSON matching a JSON Schema.

```yaml
- type: output_json_schema
  schema:
    type: object
    properties:
      name:
        type: string
      age:
        type: integer
    required:
      - name
      - age
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema` | dict | yes | JSON Schema to validate against |

## `tool_call_count`

Assert the exact, minimum, or maximum number of tool calls made by the agent.

```yaml
- type: tool_call_count
  exact: 2
```

With min/max bounds:

```yaml
- type: tool_call_count
  min_count: 1
  max_count: 5
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `exact` | integer | no | Exact expected number of tool calls |
| `min_count` | integer | no | Minimum number of tool calls (>= 0) |
| `max_count` | integer | no | Maximum number of tool calls (>= 0) |

## `output_not_contains`

Assert that the agent's output does NOT contain a substring (useful for safety checks).

```yaml
- type: output_not_contains
  value: "password"
  case_sensitive: true
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `value` | string | yes | — | Substring that must be absent |
| `case_sensitive` | bool | no | `true` | Whether the check is case-sensitive |

## `cost_under`

Assert that the API call cost is under a threshold.

```yaml
- type: cost_under
  max_cost: 0.01
  input_price_per_token: 0.000002
  output_price_per_token: 0.000008
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `max_cost` | number | yes | — | Maximum allowed cost in USD |
| `input_price_per_token` | number | no | `0` | Price per input token in USD |
| `output_price_per_token` | number | no | `0` | Price per output token in USD |

## `output_length_between`

Assert that the output length (in characters or tokens) falls within a range.

```yaml
- type: output_length_between
  min_length: 10
  max_length: 500
  unit: chars
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `min_length` | integer | no | — | Minimum length (>= 0) |
| `max_length` | integer | no | — | Maximum length (>= 0) |
| `unit` | `"chars"` or `"tokens"` | no | `"chars"` | Unit of measurement |

## Spec example

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
