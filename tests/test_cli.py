from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from agentspec.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def valid_spec_path():
    data = {
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
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def mock_adapter_and_runner():
    with patch("agentspec.cli.OpenAICompatibleAdapter") as mock_adapter_cls:
        with patch("agentspec.cli.TestRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner.run_all = AsyncMock()
            mock_report = MagicMock()
            mock_report.spec_name = "Test Spec"
            mock_report.summary.total = 1
            mock_report.summary.passed = 1
            mock_report.summary.failed = 0
            mock_report.summary.errors = 0
            mock_report.summary.pass_rate = 1.0
            mock_report.avg_latency = 0.5
            mock_report.total_tokens = 30
            mock_report.results = []
            mock_runner.run_all.return_value = mock_report
            mock_runner_cls.return_value = mock_runner
            yield mock_adapter_cls, mock_runner_cls


class TestValidateCommand:
    def test_valid_spec(self, runner, valid_spec_path):
        result = runner.invoke(main, ["validate", valid_spec_path])
        assert result.exit_code == 0
        assert "is valid" in result.output

    def test_invalid_spec(self, runner):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: [yaml: broken")
            path = f.name
        result = runner.invoke(main, ["validate", path])
        assert result.exit_code != 0
        assert "Invalid spec" in result.output or "❌" in result.output
        os.unlink(path)

    def test_missing_file(self, runner):
        result = runner.invoke(main, ["validate", "/nonexistent/spec.yaml"])
        assert result.exit_code != 0
        assert "does not exist" in result.output or "Error" in result.output

    def test_valid_spec_shows_test_count(self, runner, valid_spec_path):
        result = runner.invoke(main, ["validate", valid_spec_path])
        assert "1 test(s)" in result.output


class TestInitCommand:
    def test_generates_template(self, runner):
        result = runner.invoke(main, ["init", "--name", "My Agent", "--model", "gpt-4"])
        assert result.exit_code == 0
        assert 'name: "My Agent"' in result.output
        assert "model: gpt-4" in result.output
        assert "tests:" in result.output
        assert "output_contains" in result.output

    def test_generates_with_defaults(self, runner):
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert 'name: "My Agent Eval"' in result.output
        assert "model: deepseek-v4-pro" in result.output

    def test_generated_yaml_is_parseable(self, runner):
        result = runner.invoke(main, ["init"])
        from agentspec.spec import Spec

        spec = Spec.from_yaml_string(result.output)
        assert spec.name == "My Agent Eval"
        assert len(spec.tests) == 1


class TestRunCommand:
    @patch("agentspec.cli.os.getenv")
    def test_run_with_api_key(
        self, mock_getenv, runner, valid_spec_path, mock_adapter_and_runner
    ):
        mock_getenv.return_value = "sk-test-key"
        result = runner.invoke(main, ["run", valid_spec_path])
        assert result.exit_code == 0

    @patch("agentspec.cli.os.getenv")
    def test_run_with_flags(
        self, mock_getenv, runner, valid_spec_path, mock_adapter_and_runner
    ):
        mock_getenv.return_value = "sk-test-key"
        result = runner.invoke(
            main,
            [
                "run",
                valid_spec_path,
                "--model",
                "gpt-4",
                "--base-url",
                "https://custom.api.com",
                "--api-key",
                "sk-custom",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        mock_adapter_and_runner[0].assert_called_once()

    @patch("agentspec.cli.os.getenv")
    def test_run_json_output(
        self, mock_getenv, runner, valid_spec_path, mock_adapter_and_runner
    ):
        mock_getenv.return_value = "sk-test-key"
        result = runner.invoke(main, ["run", valid_spec_path, "--output", "json"])
        assert result.exit_code == 0

    def test_run_missing_file(self, runner):
        result = runner.invoke(main, ["run", "/nonexistent/spec.yaml"])
        assert result.exit_code != 0
        assert "does not exist" in result.output

    @patch("agentspec.cli.os.getenv")
    def test_run_handles_spec_parse_error(
        self, mock_getenv, runner, mock_adapter_and_runner
    ):
        mock_getenv.return_value = "sk-test-key"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("broken: [yaml:")
            path = f.name
        result = runner.invoke(main, ["run", path])
        assert "Error" in result.output or result.exit_code != 0
        os.unlink(path)


class TestHelpCommand:
    def test_help_output(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "validate" in result.output
        assert "init" in result.output

    def test_run_help(self, runner):
        result = runner.invoke(main, ["run", "--help"])
        assert result.exit_code == 0
        assert "--verbose" in result.output
        assert "--output" in result.output
