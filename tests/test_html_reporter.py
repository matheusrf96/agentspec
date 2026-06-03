from __future__ import annotations

from agentspec.assertions import AssertionResult
from agentspec.reporter import ReportConfig, Reporter, _build_html
from agentspec.scorer import (
    ConsolidatedReport,
    TestCaseResult,
    TestReport,
)


def _make_report(
    spec_name: str = "Test Spec",
    passed: int = 2,
    failed: int = 1,
    errors: int = 0,
) -> TestReport:
    results = []
    for i in range(passed):
        results.append(
            TestCaseResult(
                name=f"pass_{i}",
                passed=True,
                latency_seconds=0.3,
                token_usage={"total_tokens": 50},
                assertion_results=[AssertionResult(name="check_output", passed=True)],
            )
        )
    for i in range(failed):
        results.append(
            TestCaseResult(
                name=f"fail_{i}",
                passed=False,
                latency_seconds=0.5,
                assertion_results=[
                    AssertionResult(
                        name="check_output",
                        passed=False,
                        reason="not found",
                    )
                ],
            )
        )
    for i in range(errors):
        results.append(
            TestCaseResult(
                name=f"error_{i}",
                passed=False,
                error="Something broke",
                latency_seconds=0.0,
            )
        )
    return TestReport(spec_name=spec_name, results=results)


class TestHtmlOutput:
    def test_generates_valid_html(self):
        report = _make_report()
        html = _build_html(report)
        assert "<!DOCTYPE html>" in html
        assert "Test Spec" in html
        assert html.count("<div") > 5

    def test_shows_summary_stats(self):
        report = _make_report(passed=3, failed=1)
        html = _build_html(report)
        assert "Pass rate" in html
        assert "Avg latency" in html
        assert "Tokens" in html

    def test_shows_pass_fail_error(self):
        report = _make_report(passed=1, failed=1, errors=1)
        html = _build_html(report)
        assert "PASS" in html
        assert "FAIL" in html
        assert "ERROR" in html

    def test_shows_assertion_details(self):
        report = _make_report(passed=0, failed=1)
        html = _build_html(report)
        assert "check_output" in html
        assert "not found" in html

    def test_shows_error_message(self):
        report = _make_report(passed=0, failed=0, errors=1)
        html = _build_html(report)
        assert "Something broke" in html

    def test_consolidated_html(self):
        r1 = _make_report(spec_name="Spec A", passed=2, failed=0)
        r2 = _make_report(spec_name="Spec B", passed=1, failed=1)
        consolidated = ConsolidatedReport(specs=[r1, r2])
        html = _build_html(consolidated)
        assert "Consolidated Report" in html
        assert "Spec A" in html
        assert "Spec B" in html

    def test_renders_via_reporter(self, capsys):
        report = _make_report()
        config = ReportConfig(output_html=True)
        reporter = Reporter(config)
        reporter.render(report)
        captured = capsys.readouterr()
        assert "<!DOCTYPE html>" in captured.out

    def test_render_consolidated_via_reporter(self, capsys):
        r1 = _make_report(spec_name="A")
        r2 = _make_report(spec_name="B")
        config = ReportConfig(output_html=True)
        reporter = Reporter(config)
        reporter.render(ConsolidatedReport(specs=[r1, r2]))
        captured = capsys.readouterr()
        assert "Consolidated Report" in captured.out

    def test_empty_report_does_not_crash(self):
        report = _make_report(passed=0, failed=0, errors=0)
        html = _build_html(report)
        assert html.count("PASS") < 2  # no pass label

    def test_no_assertions_does_not_crash(self):
        report = TestReport(
            spec_name="Empty",
            results=[
                TestCaseResult(name="no_assertion", passed=True, latency_seconds=0.1)
            ],
        )
        html = _build_html(report)
        assert "no_assertion" in html


class TestCoverageGaps:
    def test_consolidated_json_via_reporter(self, capsys):
        r1 = _make_report(spec_name="A")
        config = ReportConfig(output_json=True)
        reporter = Reporter(config)
        reporter.render(ConsolidatedReport(specs=[r1]))
        captured = capsys.readouterr()
        assert '"consolidated": true' in captured.out
        assert '"spec_count": 1' in captured.out

    def test_consolidated_terminal_via_reporter(self, capsys):
        r1 = _make_report(spec_name="Spec X", passed=2, failed=1)
        config = ReportConfig(verbose=True)
        reporter = Reporter(config)
        reporter.render(ConsolidatedReport(specs=[r1]))
        captured = capsys.readouterr()
        assert "Consolidated Report" in captured.out
        assert "Spec X" in captured.out
        assert "Aggregate Summary" in captured.out
        assert "check_output" in captured.out
