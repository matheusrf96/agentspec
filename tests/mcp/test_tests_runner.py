from __future__ import annotations

from unittest.mock import MagicMock, patch

from agentspec.mcp.tests_runner import (
    PROJECT_DIR,
    _parse_pytest_summary,
    _run_cmd,
    run_all,
    run_pytest,
    run_ruff,
)


class TestRunCmd:
    @patch("agentspec.mcp.tests_runner.subprocess.run")
    def test_runs_command_successfully(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = _run_cmd(["echo", "hello"])
        assert result["exit_code"] == 0
        assert result["stdout"] == "output"

    @patch("agentspec.mcp.tests_runner.subprocess.run")
    def test_handles_timeout(self, mock_run):
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("cmd", 120)

        result = _run_cmd(["sleep", "999"])
        assert result["exit_code"] == -1
        assert "timed out" in result["stderr"]

    @patch("agentspec.mcp.tests_runner.subprocess.run")
    def test_handles_file_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()

        result = _run_cmd(["nonexistent_cmd"])
        assert result["exit_code"] == -1
        assert "not found" in result["stderr"]

    @patch("agentspec.mcp.tests_runner.subprocess.run")
    def test_uses_project_cwd(self, mock_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        _run_cmd(["pwd"])
        _, kwargs = mock_run.call_args
        assert "cwd" in kwargs
        assert kwargs["cwd"] == str(PROJECT_DIR)


class TestParsePytestSummary:
    def test_parses_all_passed(self):
        output = "collected 10 items\n\n10 passed in 0.50s"
        result = _parse_pytest_summary(output)
        assert result["passed"] == 10
        assert result["failed"] == 0
        assert result["errors"] == 0

    def test_parses_mixed_results(self):
        output = "collected 15 items\n\n12 passed, 2 failed, 1 error in 1.20s"
        result = _parse_pytest_summary(output)
        assert result["passed"] == 12
        assert result["failed"] == 2
        assert result["errors"] == 1

    def test_parses_all_failed(self):
        output = "collected 5 items\n\n5 failed in 0.30s"
        result = _parse_pytest_summary(output)
        assert result["passed"] == 0
        assert result["failed"] == 5
        assert result["errors"] == 0

    def test_parses_with_errors_only(self):
        output = "collected 3 items\n\n3 error in 0.10s"
        result = _parse_pytest_summary(output)
        assert result["passed"] == 0
        assert result["failed"] == 0
        assert result["errors"] == 3

    def test_empty_output(self):
        result = _parse_pytest_summary("")
        assert result["passed"] == 0
        assert result["failed"] == 0
        assert result["errors"] == 0

    def test_no_numbers_in_output(self):
        result = _parse_pytest_summary("no results here")
        assert result["passed"] == 0
        assert result["failed"] == 0
        assert result["errors"] == 0


class TestRunPytest:
    @patch("agentspec.mcp.tests_runner._run_cmd")
    def test_builds_correct_command(self, mock_run_cmd):
        mock_run_cmd.return_value = {"exit_code": 0, "stdout": "1 passed", "stderr": ""}

        result = run_pytest(path="tests/mcp", marker="unit", verbose=True)
        assert result["exit_code"] == 0

        args, _ = mock_run_cmd.call_args
        cmd = args[0]
        assert "pytest" in cmd
        assert "tests/mcp" in cmd
        assert "-m" in cmd
        assert "unit" in cmd
        assert "-v" in cmd

    @patch("agentspec.mcp.tests_runner._run_cmd")
    def test_minimal_command(self, mock_run_cmd):
        mock_run_cmd.return_value = {"exit_code": 0, "stdout": "1 passed", "stderr": ""}
        result = run_pytest()
        assert result["exit_code"] == 0
        args, _ = mock_run_cmd.call_args
        cmd = args[0]
        assert cmd == ["python", "-m", "pytest"]

    @patch("agentspec.mcp.tests_runner._run_cmd")
    def test_parses_summary(self, mock_run_cmd):
        mock_run_cmd.return_value = {"exit_code": 1, "stdout": "5 passed, 2 failed", "stderr": ""}
        result = run_pytest()
        assert result["passed"] == 5
        assert result["failed"] == 2


class TestRunRuff:
    @patch("agentspec.mcp.tests_runner._run_cmd")
    def test_passed_when_exit_code_zero(self, mock_run_cmd):
        mock_run_cmd.return_value = {"exit_code": 0, "stdout": "", "stderr": ""}
        result = run_ruff()
        assert result["passed"] is True
        assert result["exit_code"] == 0

    @patch("agentspec.mcp.tests_runner._run_cmd")
    def test_failed_when_exit_code_nonzero(self, mock_run_cmd):
        mock_run_cmd.return_value = {"exit_code": 1, "stdout": "issues found", "stderr": ""}
        result = run_ruff()
        assert result["passed"] is False
        assert result["exit_code"] == 1

    @patch("agentspec.mcp.tests_runner._run_cmd")
    def test_includes_path(self, mock_run_cmd):
        mock_run_cmd.return_value = {"exit_code": 0, "stdout": "", "stderr": ""}
        run_ruff(path="agentspec/mcp")
        args, _ = mock_run_cmd.call_args
        cmd = args[0]
        assert "ruff" in cmd
        assert "agentspec/mcp" in cmd


class TestRunAll:
    @patch("agentspec.mcp.tests_runner.run_ruff")
    @patch("agentspec.mcp.tests_runner.run_pytest")
    def test_runs_both_and_returns_combined(self, mock_pytest, mock_ruff):
        mock_ruff.return_value = {"exit_code": 0, "passed": True, "output": ""}
        mock_pytest.return_value = {
            "exit_code": 0, "passed": 5, "failed": 0,
            "errors": 0, "output": "",
        }

        result = run_all()
        assert "lint" in result
        assert "tests" in result
        mock_ruff.assert_called_once()
        mock_pytest.assert_called_once()
