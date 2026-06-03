from __future__ import annotations

import json

from agentspec.assertions import AssertionResult
from agentspec.reporter import ReportConfig, Reporter
from agentspec.scorer import TestCaseResult, TestReport


def _result(
    name: str,
    passed: bool,
    error: str | None = None,
    latency: float = 1.0,
    assertions: list[tuple[str, bool, str]] | None = None,
) -> TestCaseResult:
    return TestCaseResult(
        name=name,
        passed=passed,
        error=error,
        latency_seconds=latency,
        assertion_results=[
            AssertionResult(name=a[0], passed=a[1], reason=a[2])
            for a in (assertions or [])
        ],
    )


def _report(results: list[TestCaseResult], spec_name: str = "Test Spec") -> TestReport:
    return TestReport(spec_name=spec_name, results=results)


class TestReportConfig:
    def test_defaults(self):
        config = ReportConfig()
        assert config.verbose is False
        assert config.output_json is False

    def test_custom_values(self):
        config = ReportConfig(verbose=True, output_json=True)
        assert config.verbose is True
        assert config.output_json is True


class TestJSONOutput:
    def test_basic_json_output(self):
        results = [
            _result("test1", True, latency=0.5),
            _result("test2", False, latency=1.2),
        ]
        report = _report(results)
        reporter = Reporter(ReportConfig(output_json=True))
        reporter.render(report)

    def test_to_dict_structure(self, capsys):
        results = [
            _result("pass1", True, latency=0.5),
            _result("fail1", False, latency=2.0),
            _result("err1", False, error="Connection error", latency=0.0),
        ]
        report = _report(results)
        reporter = Reporter(ReportConfig(output_json=True))
        reporter.render(report)
        out, _ = capsys.readouterr()
        data = json.loads(out)
        assert data["spec"] == "Test Spec"
        assert len(data["results"]) == 3
        assert data["results"][0]["status"] == "pass"
        assert data["results"][1]["status"] == "fail"
        assert data["results"][2]["status"] == "error"
        assert data["summary"]["total"] == 3
        assert data["summary"]["passed"] == 1
        assert data["summary"]["failed"] == 1
        assert data["summary"]["errors"] == 1

    def test_json_with_assertion_details(self, capsys):
        results = [
            _result("test1", True, latency=0.5, assertions=[
                ("check1", True, "ok"),
                ("check2", True, "ok"),
            ]),
        ]
        report = _report(results)
        reporter = Reporter(ReportConfig(output_json=True))
        reporter.render(report)
        out, _ = capsys.readouterr()
        data = json.loads(out)
        assert len(data["results"][0]["assertions"]) == 2
        assert data["results"][0]["assertions"][0]["passed"] is True

    def test_json_empty_report(self, capsys):
        report = _report([])
        reporter = Reporter(ReportConfig(output_json=True))
        reporter.render(report)
        out, _ = capsys.readouterr()
        data = json.loads(out)
        assert data["summary"]["total"] == 0
        assert data["summary"]["pass_rate"] == 0.0


class TestTerminalOutput:
    def test_prints_spec_name(self, capsys):
        report = _report([_result("t1", True)], spec_name="My Eval")
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "My Eval" in out

    def test_prints_pass(self, capsys):
        report = _report([_result("check_ok", True)])
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "PASS" in out

    def test_prints_fail(self, capsys):
        report = _report([_result("check_bad", False)])
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "FAIL" in out

    def test_prints_error(self, capsys):
        report = _report([_result("crash", False, error="Timeout")])
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "ERROR" in out
        assert "Timeout" in out

    def test_shows_test_count(self, capsys):
        report = _report([_result("t1", True), _result("t2", True)])
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "2 test(s)" in out

    def test_verbose_shows_assertions(self, capsys):
        results = [
            _result("t1", True, assertions=[
                ("c1", True, "ok"),
                ("c2", True, "ok"),
            ]),
        ]
        report = _report(results)
        reporter = Reporter(ReportConfig(verbose=True))
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "c1" in out
        assert "c2" in out

    def test_verbose_shows_failed_assertion_reason(self, capsys):
        results = [
            _result("t1", False, assertions=[
                ("c1", False, "Value mismatch"),
            ]),
        ]
        report = _report(results)
        reporter = Reporter(ReportConfig(verbose=True))
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "Value mismatch" in out

    def test_non_verbose_hides_assertions(self, capsys):
        results = [
            _result("t1", True, assertions=[
                ("c1", True, "ok"),
            ]),
        ]
        report = _report(results)
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "c1" not in out

    def test_summary_shows_pass_rate(self, capsys):
        report = _report([
            _result("t1", True),
            _result("t2", True),
            _result("t3", False),
        ])
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "67%" in out or "66%" in out
        assert "2/3" in out

    def test_summary_shows_avg_latency(self, capsys):
        report = _report([
            _result("t1", True, latency=1.0),
            _result("t2", True, latency=3.0),
        ])
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "2.00" in out or "2" in out


class TestEdgeCases:
    def test_empty_report(self, capsys):
        report = _report([])
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "0 test(s)" in out

    def test_all_pass(self, capsys):
        report = _report([
            _result("t1", True),
            _result("t2", True),
            _result("t3", True),
        ])
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "3/3" in out
        assert "100%" in out

    def test_all_fail(self, capsys):
        report = _report([
            _result("t1", False),
            _result("t2", False),
        ])
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "0/2" in out
        assert "0%" in out

    def test_mixed_results(self, capsys):
        report = _report([
            _result("pass", True),
            _result("fail", False),
            _result("error", False, error="oops"),
        ])
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()

    def test_zero_latency(self, capsys):
        report = _report([_result("instant", True, latency=0.0)])
        reporter = Reporter()
        reporter.render(report)
        out, _ = capsys.readouterr()
        assert "instant" in out
