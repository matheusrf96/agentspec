from __future__ import annotations

import os
import tempfile

import pytest
import yaml

from agentspec.mcp.spec_manager import (
    add_assertion,
    add_test,
    create_spec,
    list_specs,
    read_spec,
    remove_assertion,
    remove_test,
    validate_spec,
)


@pytest.fixture
def tmp_spec():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(
            {
                "name": "Test Spec",
                "model": "deepseek-v4-pro",
                "system_prompt": "You are a test assistant.",
                "tests": [
                    {
                        "name": "test1",
                        "prompt": "Hello",
                        "assertions": [{"type": "output_contains", "value": "hello"}],
                    },
                ],
            },
            f,
        )
        fpath = f.name
    yield fpath
    if os.path.exists(fpath):
        os.unlink(fpath)


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    for root, dirs, files in os.walk(d, topdown=False):
        for name in files:
            os.unlink(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(d)


class TestListSpecs:
    def test_lists_specs_in_directory(self, tmp_dir):
        spec_path = os.path.join(tmp_dir, "test.yaml")
        with open(spec_path, "w") as f:
            yaml.dump(
                {
                    "name": "My Spec",
                    "model": "deepseek-v4-pro",
                    "tests": [{"name": "t1", "prompt": "hi"}],
                },
                f,
            )
        result = list_specs(tmp_dir)
        assert len(result["specs"]) == 1
        assert result["specs"][0]["name"] == "My Spec"
        assert result["specs"][0]["test_count"] == 1

    def test_lists_only_yaml_files(self, tmp_dir):
        open(os.path.join(tmp_dir, "notes.txt"), "w").close()
        open(os.path.join(tmp_dir, "spec.yaml"), "w").close()
        result = list_specs(tmp_dir)
        names = [s["name"] for s in result["specs"]]
        assert all(n.endswith((".yaml", ".yml")) or n in ("spec.yaml",) for n in names)

    def test_empty_directory(self, tmp_dir):
        result = list_specs(tmp_dir)
        assert result["specs"] == []

    def test_nonexistent_directory_returns_error(self):
        result = list_specs("/nonexistent/path")
        assert result["specs"] == []
        assert "error" in result


class TestReadSpec:
    def test_reads_valid_spec(self, tmp_spec):
        result = read_spec(tmp_spec)
        assert result.get("name") == "Test Spec"
        assert len(result.get("tests", [])) == 1
        assert result["tests"][0]["name"] == "test1"

    def test_file_not_found_returns_error(self):
        result = read_spec("/nonexistent/spec.yaml")
        assert "error" in result

    def test_invalid_yaml_returns_error(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: [broken")
            fpath = f.name
        try:
            result = read_spec(fpath)
            assert "error" in result
        finally:
            os.unlink(fpath)


class TestValidateSpec:
    def test_valid_spec(self, tmp_spec):
        result = validate_spec(tmp_spec)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_invalid_spec(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("name: 123\nmodel: []")
            fpath = f.name
        try:
            result = validate_spec(fpath)
            assert result["valid"] is False
            assert len(result["errors"]) > 0
        finally:
            os.unlink(fpath)

    def test_file_not_found(self):
        result = validate_spec("/nonexistent/spec.yaml")
        assert result["valid"] is False


class TestCreateSpec:
    def test_creates_spec_file(self, tmp_dir):
        output = os.path.join(tmp_dir, "new_spec.yaml")
        result = create_spec("My Agent", output)
        assert result["name"] == "My Agent"
        assert result["test_count"] == 0
        assert os.path.exists(output)
        with open(output) as f:
            data = yaml.safe_load(f)
        assert data["name"] == "My Agent"
        assert data["model"] == "deepseek-v4-pro"

    def test_creates_spec_with_custom_model(self, tmp_dir):
        output = os.path.join(tmp_dir, "custom.yaml")
        result = create_spec("Custom", output, model="gpt-4", system_prompt="Be nice.")
        assert result["path"] == os.path.abspath(output)
        with open(output) as f:
            data = yaml.safe_load(f)
        assert data["model"] == "gpt-4"
        assert data["system_prompt"] == "Be nice."
        assert data["tests"] == []


class TestAddTest:
    def test_adds_test(self, tmp_spec):
        result = add_test(tmp_spec, "new_test", "What is AI?")
        assert result["ok"] is True
        with open(tmp_spec) as f:
            data = yaml.safe_load(f)
        assert len(data["tests"]) == 2
        assert data["tests"][1]["name"] == "new_test"

    def test_file_not_found(self):
        result = add_test("/nonexistent.yaml", "t1", "hi")
        assert result["ok"] is False
        assert "error" in result


class TestAddAssertion:
    def test_adds_tool_called_assertion(self, tmp_spec):
        result = add_assertion(
            tmp_spec, "test1", "tool_called", tool_name="get_weather"
        )
        assert result["ok"] is True
        with open(tmp_spec) as f:
            data = yaml.safe_load(f)
        assert len(data["tests"][0]["assertions"]) == 2
        assert data["tests"][0]["assertions"][1]["type"] == "tool_called"
        assert data["tests"][0]["assertions"][1]["tool_name"] == "get_weather"

    def test_adds_output_contains_assertion(self, tmp_spec):
        result = add_assertion(
            tmp_spec,
            "test1",
            "output_contains",
            value="world",
            case_sensitive=False,
        )
        assert result["ok"] is True
        with open(tmp_spec) as f:
            data = yaml.safe_load(f)
        a = data["tests"][0]["assertions"][1]
        assert a["type"] == "output_contains"
        assert a["value"] == "world"
        assert a["case_sensitive"] is False

    def test_adds_output_matches_assertion(self, tmp_spec):
        result = add_assertion(tmp_spec, "test1", "output_matches", pattern=r"\d+")
        assert result["ok"] is True
        with open(tmp_spec) as f:
            data = yaml.safe_load(f)
        assert data["tests"][0]["assertions"][1]["pattern"] == r"\d+"

    def test_adds_latency_under_assertion(self, tmp_spec):
        result = add_assertion(tmp_spec, "test1", "latency_under", max_seconds=15.0)
        assert result["ok"] is True
        with open(tmp_spec) as f:
            data = yaml.safe_load(f)
        assert data["tests"][0]["assertions"][1]["max_seconds"] == 15.0

    def test_adds_output_contains_any_assertion(self, tmp_spec):
        result = add_assertion(
            tmp_spec,
            "test1",
            "output_contains_any",
            values=["a", "b"],
            match="any",
        )
        assert result["ok"] is True
        with open(tmp_spec) as f:
            data = yaml.safe_load(f)
        a = data["tests"][0]["assertions"][1]
        assert a["type"] == "output_contains_any"
        assert a["values"] == ["a", "b"]
        assert a["match"] == "any"

    def test_adds_output_json_schema_assertion(self, tmp_spec):
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        result = add_assertion(tmp_spec, "test1", "output_json_schema", schema=schema)
        assert result["ok"] is True
        with open(tmp_spec) as f:
            data = yaml.safe_load(f)
        assert data["tests"][0]["assertions"][1]["schema"] == schema

    def test_unknown_test_returns_error(self, tmp_spec):
        result = add_assertion(tmp_spec, "nonexistent", "tool_called", tool_name="x")
        assert result["ok"] is False
        assert "error" in result

    def test_file_not_found(self):
        result = add_assertion("/nonexistent.yaml", "t1", "tool_called", tool_name="x")
        assert result["ok"] is False


class TestRemoveTest:
    def test_removes_test(self, tmp_spec):
        result = remove_test(tmp_spec, "test1")
        assert result["ok"] is True
        with open(tmp_spec) as f:
            data = yaml.safe_load(f)
        assert len(data["tests"]) == 0

    def test_unknown_test_returns_error(self, tmp_spec):
        result = remove_test(tmp_spec, "nonexistent")
        assert result["ok"] is False
        assert "error" in result

    def test_file_not_found(self):
        result = remove_test("/nonexistent.yaml", "t1")
        assert result["ok"] is False


class TestRemoveAssertion:
    def test_removes_assertion_by_index(self, tmp_spec):
        result = remove_assertion(tmp_spec, "test1", 0)
        assert result["ok"] is True
        with open(tmp_spec) as f:
            data = yaml.safe_load(f)
        assert len(data["tests"][0]["assertions"]) == 0

    def test_index_out_of_range(self, tmp_spec):
        result = remove_assertion(tmp_spec, "test1", 99)
        assert result["ok"] is False

    def test_negative_index(self, tmp_spec):
        result = remove_assertion(tmp_spec, "test1", -1)
        assert result["ok"] is False

    def test_unknown_test(self, tmp_spec):
        result = remove_assertion(tmp_spec, "nonexistent", 0)
        assert result["ok"] is False

    def test_file_not_found(self):
        result = remove_assertion("/nonexistent.yaml", "t1", 0)
        assert result["ok"] is False
