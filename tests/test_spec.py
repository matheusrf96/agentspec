from agentspec.spec import Spec


def test_from_yaml():
    spec = Spec.from_yaml("tests/fixtures/sample.yaml")
    assert spec.name == "Sample Eval"
    assert spec.model == "deepseek-v4-pro"
    assert len(spec.tests) == 1
    assert spec.tests[0].name == "says hello"
    assert spec.tests[0].assertions[0].value == "hello"


def test_from_yaml_string():
    content = """
name: "Test"
model: deepseek-v4-pro
tests:
  - name: "test1"
    prompt: "hello"
    """
    spec = Spec.from_yaml_string(content)
    assert spec.name == "Test"
    assert len(spec.tests) == 1


def test_multiple_assertions():
    content = """
name: "Multi"
model: deepseek-v4-pro
tests:
  - name: "full test"
    prompt: "analyze AAPL"
    assertions:
      - type: tool_called
        tool_name: get_stock_price
      - type: output_matches
        pattern: '\\$\\d+'
      - type: latency_under
        max_seconds: 15
    """
    spec = Spec.from_yaml_string(content)
    assert len(spec.tests[0].assertions) == 3


def test_all_assertion_types():
    content = """
name: "All Types"
model: deepseek-v4-pro
tests:
  - name: "all assertions"
    prompt: "test"
    assertions:
      - type: tool_called
        tool_name: test_tool
        args: { key: "val" }
      - type: output_contains
        value: "hello"
      - type: output_contains_any
        values: ["a", "b"]
        match: any
      - type: output_matches
        pattern: "^test$"
      - type: latency_under
        max_seconds: 10
      - type: output_json_schema
        schema:
          type: object
          properties:
            name: { type: string }
          required: []
    """
    spec = Spec.from_yaml_string(content)
    assert len(spec.tests[0].assertions) == 6
