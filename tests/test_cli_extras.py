from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from agentspec.cli import main
from agentspec.scorer import TestReport


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_adapter_and_runner():
    with patch("agentspec.cli.OpenAICompatibleAdapter"):
        with patch("agentspec.cli.TestRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner.run_all = AsyncMock()
            mock_report = MagicMock(spec=TestReport)
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
            yield mock_runner_cls


@pytest.fixture
def spec_dir():
    with tempfile.TemporaryDirectory() as tmp:
        specs = [
            {"name": "Spec A", "model": "gpt-4", "system_prompt": "test",
             "tests": [{"name": "t1", "prompt": "hi",
                        "assertions": [{"type": "output_contains",
                                        "value": "hello"}]}]},
            {"name": "Spec B", "model": "gpt-4", "system_prompt": "test",
             "tests": [{"name": "t2", "prompt": "hey",
                        "assertions": [{"type": "output_contains",
                                        "value": "world"}]}]},
        ]
        for i, spec in enumerate(specs):
            path = os.path.join(tmp, f"spec_{i}.yaml")
            with open(path, "w") as f:
                yaml.dump(spec, f)
        yield tmp


class TestDirectorySpecs:
    @patch("agentspec.cli.os.getenv")
    def test_runs_directory(
        self, mock_getenv, runner, spec_dir, mock_adapter_and_runner
    ):
        mock_getenv.return_value = "sk-test-key"
        result = runner.invoke(main, ["run", spec_dir])
        assert result.exit_code == 0
        assert mock_adapter_and_runner.call_count == 2

    @patch("agentspec.cli.os.getenv")
    def test_consolidated_json_output(
        self, mock_getenv, runner, spec_dir, mock_adapter_and_runner
    ):
        mock_getenv.return_value = "sk-test-key"
        result = runner.invoke(main, ["run", spec_dir, "--output", "json"])
        assert result.exit_code == 0
        assert '"consolidated": true' in result.output
        assert '"spec_count": 2' in result.output

    def test_empty_directory(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.invoke(main, ["run", tmp])
            assert result.exit_code != 0
            assert "No .yaml files found" in result.output

    @patch("agentspec.cli.os.getenv")
    def test_single_file_still_works(
        self, mock_getenv, runner, spec_dir, mock_adapter_and_runner
    ):
        mock_getenv.return_value = "sk-test-key"
        single = os.path.join(spec_dir, "spec_0.yaml")
        result = runner.invoke(main, ["run", single])
        assert result.exit_code == 0
        assert mock_adapter_and_runner.call_count == 1
