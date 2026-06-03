from __future__ import annotations

import os
import tempfile

from agentspec.mcp.spec_templates import TEMPLATES, apply_template, get_template, list_templates


class TestListTemplates:
    def test_returns_all_templates(self):
        result = list_templates()
        assert "templates" in result
        assert len(result["templates"]) == len(TEMPLATES)

    def test_templates_have_name_and_description(self):
        result = list_templates()
        for t in result["templates"]:
            assert "name" in t
            assert "description" in t

    def test_expected_templates_present(self):
        result = list_templates()
        names = [t["name"] for t in result["templates"]]
        assert "tool-calling" in names
        assert "rag" in names
        assert "chat" in names
        assert "code-gen" in names
        assert "structured-output" in names


class TestGetTemplate:
    def test_returns_parsed_template(self):
        result = get_template("tool-calling")
        assert "error" not in result
        assert result["name"] == "tool-calling"
        assert "spec" in result
        assert "name" in result["spec"]
        assert "tests" in result["spec"]
        assert len(result["spec"]["tests"]) > 0

    def test_unknown_template_returns_error(self):
        result = get_template("nonexistent")
        assert "error" in result

    def test_rag_template_has_correct_structure(self):
        result = get_template("rag")
        spec = result["spec"]
        assert "RAG" in spec["name"]
        assert len(spec["tests"]) >= 2

    def test_chat_template_has_safety_test(self):
        result = get_template("chat")
        spec = result["spec"]
        prompts = [t["prompt"] for t in spec["tests"]]
        assert any("hack" in p.lower() for p in prompts)

    def test_code_gen_template_checks_python_syntax(self):
        result = get_template("code-gen")
        spec = result["spec"]
        assertions = spec["tests"][0]["assertions"]
        types = [a["type"] for a in assertions]
        assert "output_contains" in types


class TestApplyTemplate:
    def test_applies_template_to_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            output = f.name
        try:
            result = apply_template("tool-calling", output)
            assert "error" not in result
            assert result["name"] == "Tool Calling Eval"
            assert os.path.exists(output)
            with open(output) as f:
                content = f.read()
            assert "name:" in content
            assert "tests:" in content
        finally:
            os.unlink(output)

    def test_applies_with_overrides(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            output = f.name
        try:
            result = apply_template(
                "tool-calling", output,
                overrides={"name": "My Custom Eval", "model": "gpt-4"},
            )
            assert "error" not in result
            with open(output) as f:
                import yaml
                data = yaml.safe_load(f)
            assert data["name"] == "My Custom Eval"
            assert data["model"] == "gpt-4"
        finally:
            os.unlink(output)

    def test_unknown_template_returns_error(self):
        result = apply_template("nonexistent", "/tmp/out.yaml")
        assert "error" in result

    def test_deep_merge_overrides_nested(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            output = f.name
        try:
            result = apply_template("structured-output", output, overrides={
                "tests": [{"name": "custom test", "prompt": "do stuff", "assertions": []}],
            })
            assert "error" not in result
            with open(output) as f:
                import yaml
                data = yaml.safe_load(f)
            assert len(data["tests"]) == 1
            assert data["tests"][0]["name"] == "custom test"
        finally:
            os.unlink(output)
