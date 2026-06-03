# Architecture

## High-level flow

```
spec.yaml → SpecParser → TestRunner → Agent (LLM API) → Assertions → Scored report
```

## Layers

### Data layer — `agentspec/spec.py`

Parses YAML spec files into Pydantic models:

```
Spec
 ├── name: str
 ├── model: str
 ├── system_prompt: Optional[str]
 └── tests: list[TestCase]
       ├── name: str
       ├── prompt: str
       └── assertions: list[Assertion]
             └── union type (6 variants)
```

Supports loading from files (`from_yaml()`) and strings (`from_yaml_string()`).

### Evaluation layer — `agentspec/assertions.py`

Each assertion type has a dedicated `_eval_*` function. `evaluate_assertion()` dispatches via pattern matching:

```python
def evaluate_assertion(assertion, response) -> AssertionResult:
    match assertion:
        case ToolCalledAssertion(): ...
        case OutputContainsAssertion(): ...
        case OutputMatchesAssertion(): ...
        case LatencyUnderAssertion(): ...
        case OutputJsonSchemaAssertion(): ...
        case OutputContainsAnyAssertion(): ...
```

### Orchestration layer — `agentspec/runner.py`

`TestRunner` iterates over tests, calls the adapter's `run()` method, then evaluates all assertions:

```python
class TestRunner:
    async def run_all(self) -> TestReport:
        for test in self.spec.tests:
            response = await self.adapter.run(prompt=test.prompt, ...)
            assertion_results = [evaluate_assertion(a, response) for a in test.assertions]
            results.append(TestCaseResult(...))
        return TestReport(...)
```

### Reporting layer — `agentspec/scorer.py` + `agentspec/reporter.py`

Scorer defines data models (`TestCaseResult`, `TestReport`, `Summary`). Reporter renders them as terminal output (rich tables) or JSON.

### Adapter layer — `agentspec/adapters/`

`AgentAdapter` is an abstract base class. Implementations handle communication with different LLM providers:

| Adapter | Location |
|---------|----------|
| `OpenAICompatibleAdapter` | `agentspec/adapters/openai_compatible_adapter.py` |
| `MockAdapter` | `agentspec/mcp/mock_agent.py` (via MCP) |

## MCP server layer — `agentspec/mcp/`

All MCP servers share a common `BaseMcpServer` from `protocol.py` that handles JSON-RPC stdio framing, tool registration, and method dispatch. Each server registers tools via a decorator:

```python
srv = BaseMcpServer("server-name")

@srv.tool("tool_name", description="...", input_schema={...})
def my_tool(param: str) -> dict:
    return {"result": ...}
```

See [MCP Servers](mcp-servers.md) for the full list.
