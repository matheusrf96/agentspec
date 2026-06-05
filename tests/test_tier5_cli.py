from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from agentspec.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_spec_dir():
    import yaml
    with tempfile.TemporaryDirectory() as tmp:
        spec = {
            "name": "Test Spec",
            "model": "gpt-4",
            "system_prompt": "test",
            "tests": [
                {
                    "name": "test1",
                    "prompt": "hi",
                    "assertions": [{"type": "output_contains", "value": "hello"}],
                }
            ],
        }
        path = os.path.join(tmp, "test.yaml")
        with open(path, "w") as f:
            yaml.dump(spec, f)
        yield tmp


class TestListSpecsCommand:
    def test_list_specs_in_directory(self, runner, sample_spec_dir):
        result = runner.invoke(main, ["list-specs", sample_spec_dir])
        assert result.exit_code == 0
        assert "test.yaml" in result.output
        assert "Test Spec" in result.output
        assert "tests=1" in result.output

    def test_list_specs_defaults_to_cwd(self, runner):
        result = runner.invoke(main, ["list-specs"])
        assert result.exit_code == 0

    def test_list_specs_nonexistent_path(self, runner):
        result = runner.invoke(main, ["list-specs", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_list_specs_empty_directory(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.invoke(main, ["list-specs", tmp])
            assert result.exit_code == 0
            assert "No spec files found" in result.output


class TestCompareCommand:
    def test_compare_missing_ids(self, runner):
        result = runner.invoke(main, ["compare", "nonexistent1", "nonexistent2"])
        assert result.exit_code != 0
        assert "Error" in result.output or "error" in result.output.lower()

    def test_compare_help(self, runner):
        result = runner.invoke(main, ["compare", "--help"])
        assert result.exit_code == 0

    def test_compare_with_verbose(self, runner):
        result = runner.invoke(main, ["compare", "id1", "id2", "--verbose"])
        assert result.exit_code != 0  # IDs don't exist


class TestResultsCommand:
    def test_results_prune_help(self, runner):
        result = runner.invoke(main, ["results", "prune", "--help"])
        assert result.exit_code == 0
        assert "--keep" in result.output

    def test_results_export_help(self, runner):
        result = runner.invoke(main, ["results", "export", "--help"])
        assert result.exit_code == 0
        assert "CSV" in result.output or "output" in result.output.lower()

    def test_results_history_help(self, runner):
        result = runner.invoke(main, ["results", "history", "--help"])
        assert result.exit_code == 0

    def test_results_get_help(self, runner):
        result = runner.invoke(main, ["results", "get", "--help"])
        assert result.exit_code == 0


class TestResultsPrune:
    @patch("agentspec.cli.prune_runs")
    def test_prune_default_keep(self, mock_prune, runner):
        mock_prune.return_value = {"removed": 5, "remaining": 50}
        result = runner.invoke(main, ["results", "prune"])
        assert result.exit_code == 0
        assert "5" in result.output
        assert "50" in result.output
        mock_prune.assert_called_once_with(keep=50, spec_name=None)

    @patch("agentspec.cli.prune_runs")
    def test_prune_with_spec_filter(self, mock_prune, runner):
        mock_prune.return_value = {"removed": 2, "remaining": 10}
        result = runner.invoke(main, ["results", "prune", "--spec", "My Spec"])
        assert result.exit_code == 0
        mock_prune.assert_called_once_with(keep=50, spec_name="My Spec")

    @patch("agentspec.cli.prune_runs")
    def test_prune_custom_keep(self, mock_prune, runner):
        mock_prune.return_value = {"removed": 0, "remaining": 100}
        result = runner.invoke(main, ["results", "prune", "--keep", "100"])
        assert result.exit_code == 0
        mock_prune.assert_called_once_with(keep=100, spec_name=None)


class TestResultsExport:
    @patch("agentspec.cli.list_runs")
    def test_export_creates_csv(self, mock_list_runs, runner):
        mock_list_runs.return_value = {
            "runs": [
                {
                    "run_id": "abc123",
                    "spec_name": "Test",
                    "spec_path": "/spec.yaml",
                    "timestamp": "2024-01-01T00:00:00",
                    "pass_rate": 0.8,
                    "total": 5,
                    "passed": 4,
                    "failed": 1,
                    "errors": 0,
                }
            ]
        }
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            outpath = f.name

        result = runner.invoke(main, ["results", "export", outpath])
        assert result.exit_code == 0
        assert os.path.exists(outpath)
        with open(outpath) as f:
            content = f.read()
        assert "run_id" in content
        assert "abc123" in content
        os.unlink(outpath)

    @patch("agentspec.cli.list_runs")
    def test_export_empty(self, mock_list_runs, runner):
        mock_list_runs.return_value = {"runs": []}
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
            outpath = f.name
        result = runner.invoke(main, ["results", "export", outpath])
        assert result.exit_code == 0
        assert "No runs" in result.output
        os.unlink(outpath)


class TestResultsHistory:
    @patch("agentspec.cli.list_runs")
    def test_history_shows_runs(self, mock_list_runs, runner):
        mock_list_runs.return_value = {
            "runs": [
                {
                    "run_id": "abc123",
                    "spec_name": "My Spec",
                    "timestamp": "2024-01-01T12:00:00",
                    "pass_rate": 0.8,
                    "total": 5,
                    "passed": 4,
                    "failed": 1,
                    "errors": 0,
                }
            ]
        }
        result = runner.invoke(main, ["results", "history"])
        assert result.exit_code == 0
        assert "abc123" in result.output
        assert "My Spec" in result.output

    @patch("agentspec.cli.list_runs")
    def test_history_empty(self, mock_list_runs, runner):
        mock_list_runs.return_value = {"runs": []}
        result = runner.invoke(main, ["results", "history"])
        assert result.exit_code == 0
        assert "No runs found" in result.output


class TestResultsGet:
    @patch("agentspec.cli.get_run")
    def test_get_run(self, mock_get_run, runner):
        mock_get_run.return_value = {
            "run_id": "abc123",
            "report": {"spec_name": "Test"},
        }
        result = runner.invoke(main, ["results", "get", "abc123"])
        assert result.exit_code == 0
        assert "abc123" in result.output

    @patch("agentspec.cli.get_run")
    def test_get_nonexistent(self, mock_get_run, runner):
        mock_get_run.return_value = {"error": "Run not found"}
        result = runner.invoke(main, ["results", "get", "nonexistent"])
        assert result.exit_code != 0


class TestCompletionCommand:
    def test_completion_bash(self, runner):
        result = runner.invoke(main, ["completion", "bash"])
        assert result.exit_code == 0
        assert "_AGENTSPEC_COMPLETE=bash_source" in result.output

    def test_completion_zsh(self, runner):
        result = runner.invoke(main, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "_AGENTSPEC_COMPLETE=zsh_source" in result.output

    def test_completion_fish(self, runner):
        result = runner.invoke(main, ["completion", "fish"])
        assert result.exit_code == 0
        assert "_AGENTSPEC_COMPLETE=fish_source" in result.output

    def test_completion_default_shell(self, runner):
        result = runner.invoke(main, ["completion"])
        assert result.exit_code == 0


class TestRunProgressFlag:
    @patch("agentspec.cli.os.getenv")
    @patch("agentspec.cli.OpenAICompatibleAdapter")
    @patch("agentspec.cli.TestRunner")
    def test_run_with_no_progress(self, mock_runner_cls, mock_adapter_cls, mock_getenv, runner):  # noqa: E501
        from unittest.mock import AsyncMock

        import yaml
        mock_getenv.return_value = "sk-test-key"
        mock_runner = mock_runner_cls.return_value
        mock_runner.run_all = AsyncMock()
        mock_report = mock_runner.run_all.return_value
        mock_report.spec_name = "Test"
        mock_report.summary.total = 1
        mock_report.summary.passed = 1
        mock_report.summary.failed = 0
        mock_report.summary.errors = 0
        mock_report.summary.pass_rate = 1.0
        mock_report.avg_latency = 0.5
        mock_report.total_tokens = 30
        mock_report.results = []

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"name": "Test", "model": "gpt-4", "system_prompt": "test", "tests": []}, f)  # noqa: E501
            path = f.name

        result = runner.invoke(main, ["run", path, "--no-progress"])
        assert result.exit_code == 0
        os.unlink(path)
