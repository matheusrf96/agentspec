from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentspec.mcp.eval_runner import run_eval, run_single_test


@pytest.fixture
def mock_spec():
    spec = MagicMock()
    spec.name = "Test Spec"
    spec.model = "deepseek-v4-pro"
    spec.tests = [
        MagicMock(name="test1", prompt="Hello"),
        MagicMock(name="test2", prompt="World"),
    ]
    return spec


@pytest.fixture
def mock_report():
    summary = MagicMock()
    summary.total = 2
    summary.passed = 1
    summary.failed = 1
    summary.errors = 0
    summary.pass_rate = 0.5

    result1 = MagicMock()
    result1.name = "test1"
    result1.passed = True
    result1.error = None
    result1.latency_seconds = 1.0
    result1.token_usage = {"total_tokens": 100}
    result1.assertion_results = [MagicMock(name="check1", passed=True, reason="ok")]

    result2 = MagicMock()
    result2.name = "test2"
    result2.passed = False
    result2.error = None
    result2.latency_seconds = 2.0
    result2.token_usage = {"total_tokens": 200}
    result2.assertion_results = [MagicMock(name="check2", passed=False, reason="fail")]

    report = MagicMock()
    report.spec_name = "Test Spec"
    report.summary = summary
    report.avg_latency = 1.5
    report.total_tokens = 300
    report.results = [result1, result2]
    return report


class TestRunEval:
    @patch("agentspec.mcp.eval_runner.OpenAICompatibleAdapter")
    @patch("agentspec.mcp.eval_runner.TestRunner")
    @patch("agentspec.mcp.eval_runner.Spec")
    def test_run_eval_returns_report(
        self,
        mock_spec_cls,
        mock_runner_cls,
        mock_adapter_cls,
        mock_spec,
        mock_report,
    ):
        mock_spec_cls.from_yaml.return_value = mock_spec
        mock_runner = MagicMock()
        mock_runner.run_all = AsyncMock(return_value=mock_report)
        mock_runner_cls.return_value = mock_runner

        result = run_eval("test.yaml")
        assert "error" not in result
        assert result["spec_name"] == "Test Spec"
        assert result["summary"]["total"] == 2
        assert result["summary"]["passed"] == 1
        assert result["summary"]["pass_rate"] == 0.5
        assert len(result["results"]) == 2

    @patch("agentspec.mcp.eval_runner.Spec")
    def test_run_eval_spec_parse_error(self, mock_spec_cls):
        mock_spec_cls.from_yaml.side_effect = ValueError("Invalid YAML")
        result = run_eval("bad.yaml")
        assert "error" in result
        assert "Invalid YAML" in result["error"]

    @patch("agentspec.mcp.eval_runner.OpenAICompatibleAdapter")
    @patch("agentspec.mcp.eval_runner.TestRunner")
    @patch("agentspec.mcp.eval_runner.Spec")
    def test_run_eval_with_overrides(
        self,
        mock_spec_cls,
        mock_runner_cls,
        mock_adapter_cls,
        mock_spec,
        mock_report,
    ):
        mock_spec_cls.from_yaml.return_value = mock_spec
        mock_runner = MagicMock()
        mock_runner.run_all = AsyncMock(return_value=mock_report)
        mock_runner_cls.return_value = mock_runner

        result = run_eval(
            "test.yaml",
            model="gpt-4",
            base_url="https://custom.api.com",
            api_key="sk-test",
        )
        assert "error" not in result
        mock_runner_cls.assert_called_once()


class TestRunSingleTest:
    @patch("agentspec.mcp.eval_runner.OpenAICompatibleAdapter")
    @patch("agentspec.mcp.eval_runner.TestRunner")
    @patch("agentspec.mcp.eval_runner.Spec")
    def test_runs_single_test(
        self,
        mock_spec_cls,
        mock_runner_cls,
        mock_adapter_cls,
        mock_spec,
        mock_report,
    ):
        mock_test = MagicMock(name="test1", prompt="Hello")
        mock_test.configure_mock(name="test1")
        mock_spec.tests = [mock_test]
        mock_spec_cls.from_yaml.return_value = mock_spec
        mock_runner = MagicMock()
        mock_runner.run_all = AsyncMock(return_value=mock_report)
        mock_runner_cls.return_value = mock_runner

        result = run_single_test("test.yaml", "test1")
        assert "error" not in result

    @patch("agentspec.mcp.eval_runner.Spec")
    def test_test_not_found(self, mock_spec_cls, mock_spec):
        mock_spec.tests = []
        mock_spec_cls.from_yaml.return_value = mock_spec
        result = run_single_test("test.yaml", "nonexistent")
        assert "error" in result
        assert "not found" in result["error"]

    @patch("agentspec.mcp.eval_runner.Spec")
    def test_spec_parse_error(self, mock_spec_cls):
        mock_spec_cls.from_yaml.side_effect = ValueError("bad spec")
        result = run_single_test("bad.yaml", "test1")
        assert "error" in result
