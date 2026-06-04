from agentspec.spec import Spec


def test_from_yaml():
    spec = Spec.from_yaml("tests/fixtures/sample.yaml")
    assert spec.name == "Sample Eval"
    assert spec.model == "deepseek-v4-pro"
    assert len(spec.tests) == 1
    assert spec.tests[0].name == "says hello"
    # only OutputContainsAssertion has attr .value
    assert spec.tests[0].assertions[0].value == "hello"  # pyright: ignore


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
      - type: tool_call_count
        exact: 1
      - type: output_not_contains
        value: "error"
      - type: cost_under
        max_cost: 0.01
      - type: output_length_between
        min_length: 1
        max_length: 1000
    """
    spec = Spec.from_yaml_string(content)
    assert len(spec.tests[0].assertions) == 10


def test_include_tag(tmp_path):
    included = tmp_path / "shared.yaml"
    included.write_text("""
- name: "Shared A"
  prompt: "prompt A"
  assertions:
    - type: output_contains
      value: "hello"
- name: "Shared B"
  prompt: "prompt B"
  assertions: []
""")
    spec_file = tmp_path / "main.yaml"
    spec_file.write_text("""
name: "Composite"
model: deepseek-v4-pro
tests:
  - !include "shared.yaml"
  - name: "Local test"
    prompt: "local"
    assertions: []
""")
    spec = Spec.from_yaml(str(spec_file))
    assert len(spec.tests) == 3
    assert spec.tests[0].name == "Shared A"
    assert spec.tests[1].name == "Shared B"
    assert spec.tests[2].name == "Local test"


def test_include_from_full_spec(tmp_path):
    included = tmp_path / "child.yaml"
    included.write_text("""
name: "Child"
model: deepseek-v4-pro
tests:
  - name: "From child"
    prompt: "child prompt"
    assertions: []
""")
    spec_file = tmp_path / "parent.yaml"
    spec_file.write_text("""
name: "Parent"
model: deepseek-v4-pro
tests:
  - !include "child.yaml"
  - name: "Local"
    prompt: "local"
    assertions: []
""")
    spec = Spec.from_yaml(str(spec_file))
    assert len(spec.tests) == 2
    assert spec.tests[0].name == "From child"
    assert spec.tests[1].name == "Local"

def test_include_empty_file(tmp_path):
    included = tmp_path / "empty.yaml"
    included.write_text("")
    spec_file = tmp_path / "main.yaml"
    spec_file.write_text("""
name: "Main"
model: deepseek-v4-pro
tests:
  - !include "empty.yaml"
  - name: "Local"
    prompt: "local"
    assertions: []
""")
    spec = Spec.from_yaml(str(spec_file))
    assert len(spec.tests) == 1
    assert spec.tests[0].name == "Local"