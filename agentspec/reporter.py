from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Union

from rich.console import Console
from rich.table import Table

from agentspec.scorer import ConsolidatedReport, TestCaseResult, TestReport


@dataclass
class ReportConfig:
    verbose: bool = False
    output_json: bool = False
    output_html: bool = False


AnyReport = Union[TestReport, ConsolidatedReport]


class Reporter:
    def __init__(self, config: ReportConfig | None = None):
        self.config = config or ReportConfig()
        self.console = Console()

    def render(self, report: AnyReport) -> None:
        if isinstance(report, ConsolidatedReport):
            if self.config.output_html:
                print(_build_html(report))
                return
            if self.config.output_json:
                print(
                    json.dumps(
                        self._consolidated_to_dict(report),
                        indent=2,
                        ensure_ascii=False,
                    )
                )
                return
            self._render_consolidated(report)
        else:
            if self.config.output_html:
                print(_build_html(report))
                return
            if self.config.output_json:
                print(json.dumps(self._to_dict(report), indent=2, ensure_ascii=False))
                return
            self._render_terminal(report)

    def _render_consolidated(self, report: ConsolidatedReport) -> None:
        self.console.print(
            f"\n[bold cyan]Consolidated Report "
            f"({len(report.specs)} spec(s))[/bold cyan]\n"
        )
        for spec_report in report.specs:
            self.console.print(
                f"  [bold]{spec_report.spec_name}[/bold] "
                f"([dim]{len(spec_report.results)} test(s)[/dim])"
            )
            for result in spec_report.results:
                self._render_test_case(result)
            self.console.print()

        self.console.print("[bold]Aggregate Summary[/bold]")
        self._render_summary(report)

    def _render_terminal(self, report: TestReport) -> None:
        self.console.print(f"\n[bold cyan]{report.spec_name}[/bold cyan]")
        self.console.print(f"[dim]{len(report.results)} test(s)[/dim]\n")

        for result in report.results:
            self._render_test_case(result)

        self.console.print()
        self._render_summary(report)

    def _render_test_case(self, result: TestCaseResult) -> None:
        if result.error:
            icon = "[bold red]💥[/bold red]"
            label = "ERROR"
        elif result.passed:
            icon = "[green]✅[/green]"
            label = "PASS"
        else:
            icon = "[red]❌[/red]"
            label = "FAIL"

        self.console.print(
            f"  {icon} [bold]{label}[/bold] {result.name} "
            f"([dim]{result.latency_seconds:.1f}s[/dim])"
        )

        if result.error:
            self.console.print(f"     [red]Error: {result.error}[/red]")

        if self.config.verbose and result.assertion_results:
            for ar in result.assertion_results:
                if ar.passed:
                    self.console.print(f"     [dim]✓ {ar.name}[/dim]")
                else:
                    self.console.print(f"     [red]✗ {ar.name}: {ar.reason}[/red]")

    def _render_summary(self, report: TestReport | ConsolidatedReport) -> None:
        summary = report.summary

        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="bold")
        table.add_column("Value")

        pass_rate = summary.pass_rate * 100
        pass_color = (
            "green" if pass_rate >= 80 else ("yellow" if pass_rate >= 50 else "red")
        )

        table.add_row(
            "Pass rate",
            f"[{pass_color}]{summary.passed}/{summary.total} "
            f"({pass_rate:.0f}%)[/{pass_color}]",
        )
        table.add_row("Passed", f"[green]{summary.passed}[/green]")
        table.add_row("Failed", f"[red]{summary.failed}[/red]")
        table.add_row("Errors", f"[red]{summary.errors}[/red]")
        table.add_row("Avg latency", f"{report.avg_latency:.2f}s")
        table.add_row("Total tokens", str(report.total_tokens))

        self.console.print(table)

    def _to_dict(self, report: TestReport) -> dict:
        return {
            "spec": report.spec_name,
            "results": [
                {
                    "name": r.name,
                    "status": (
                        "error" if r.error else ("pass" if r.passed else "fail")
                    ),
                    "latency_seconds": r.latency_seconds,
                    "error": r.error,
                    "assertions": [
                        {
                            "name": a.name,
                            "passed": a.passed,
                            "reason": a.reason,
                        }
                        for a in r.assertion_results
                    ],
                }
                for r in report.results
            ],
            "summary": {
                "total": report.summary.total,
                "passed": report.summary.passed,
                "failed": report.summary.failed,
                "errors": report.summary.errors,
                "pass_rate": report.summary.pass_rate,
                "avg_latency": report.avg_latency,
                "total_tokens": report.total_tokens,
            },
        }

    def _consolidated_to_dict(self, report: ConsolidatedReport) -> dict:
        return {
            "consolidated": True,
            "spec_count": len(report.specs),
            "specs": [self._to_dict(s) for s in report.specs],
            "summary": {
                "total": report.summary.total,
                "passed": report.summary.passed,
                "failed": report.summary.failed,
                "errors": report.summary.errors,
                "pass_rate": report.summary.pass_rate,
                "avg_latency": report.avg_latency,
                "total_tokens": report.total_tokens,
            },
        }


def _fmt_result(result) -> dict:
    if result.error:
        return {"cls": "error", "icon": "\u26a1", "label": "ERROR"}
    if result.passed:
        return {"cls": "pass", "icon": "\u2714", "label": "PASS"}
    return {"cls": "fail", "icon": "\u2718", "label": "FAIL"}


def _build_html(report: AnyReport) -> str:
    from html import escape

    is_consolidated = isinstance(report, ConsolidatedReport)
    specs = report.specs if is_consolidated else [report]
    s = report.summary
    pass_rate_pct = s.pass_rate * 100
    rate_color = (
        "#22c55e"
        if pass_rate_pct >= 80
        else ("#eab308" if pass_rate_pct >= 50 else "#ef4444")
    )

    rows_html = ""
    for sr in specs:
        rows_html += f'<h2 class="spec-name">{escape(sr.spec_name)}</h2>\n'
        for r in sr.results:
            fm = _fmt_result(r)
            assertions_html = ""
            if r.assertion_results:
                for ar in r.assertion_results:
                    ic = "\u2714" if ar.passed else "\u2718"
                    cl = "pass" if ar.passed else "fail"
                    assertions_html += (
                        f'<div class="assertion {cl}">'
                        f'<span class="assert-icon">{ic}</span> '
                        f'<span class="assert-name">{escape(ar.name)}</span>'
                    )
                    if ar.reason:
                        assertions_html += (
                            f'<span class="assert-reason">{escape(ar.reason)}</span>'
                        )
                    assertions_html += "</div>\n"

            latency = r.latency_seconds
            error_html = (
                f'<div class="test-error">{escape(r.error)}</div>\n' if r.error else ""
            )
            rows_html += (
                f'<div class="test-case {fm["cls"]}" '
                f'onclick="toggle(this)">\n'
                f'  <div class="test-header">\n'
                f'    <span class="test-icon">{fm["icon"]}</span>\n'
                f'    <span class="test-label">{fm["label"]}</span>\n'
                f'    <span class="test-name">{escape(r.name)}</span>\n'
                f'    <span class="test-latency">{latency:.1f}s</span>\n'
                f"  </div>\n"
                f'  <div class="test-detail" style="display:none">\n'
                f"    {error_html}"
                f"    {assertions_html}"
                f"  </div>\n"
                f"</div>\n"
            )

    title = "Consolidated Report" if is_consolidated else escape(report.spec_name)
    sub = f"({len(report.specs)} specs)" if is_consolidated else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AgentSpec Report - {escape(str(title))}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
         background: #0f172a; color: #e2e8f0; padding: 2rem; }}
  .container {{ max-width: 800px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
  .subtitle {{ color: #64748b; font-size: 0.875rem; margin-bottom: 1.5rem; }}
  .summary {{ display: flex; gap: 1.5rem; flex-wrap: wrap;
              background: #1e293b; border-radius: 0.5rem; padding: 1rem 1.5rem;
              margin-bottom: 1.5rem; }}
  .summary-item {{ text-align: center; }}
  .summary-value {{ font-size: 1.5rem; font-weight: 700; }}
  .summary-label {{ font-size: 0.75rem; color: #94a3b8; }}
  .spec-name {{ font-size: 1.125rem; font-weight: 600; margin: 1rem 0 0.5rem; }}
  .test-case {{ background: #1e293b; border-radius: 0.375rem; margin-bottom: 0.375rem;
                cursor: pointer; transition: background 0.15s; }}
  .test-case:hover {{ background: #334155; }}
  .test-case.pass {{ border-left: 3px solid #22c55e; }}
  .test-case.fail {{ border-left: 3px solid #ef4444; }}
  .test-case.error {{ border-left: 3px solid #f97316; }}
  .test-header {{ display: flex; align-items: center; gap: 0.5rem;
                  padding: 0.625rem 1rem; }}
  .test-icon {{ font-size: 1rem; width: 1.25rem; text-align: center; }}
  .test-case.pass .test-icon {{ color: #22c55e; }}
  .test-case.fail .test-icon {{ color: #ef4444; }}
  .test-case.error .test-icon {{ color: #f97316; }}
  .test-label {{ font-size: 0.75rem; font-weight: 700; width: 3rem;
                 text-transform: uppercase; }}
  .test-case.pass .test-label {{ color: #22c55e; }}
  .test-case.fail .test-label {{ color: #ef4444; }}
  .test-case.error .test-label {{ color: #f97316; }}
  .test-name {{ flex: 1; font-size: 0.875rem; }}
  .test-latency {{ color: #64748b; font-size: 0.75rem; }}
  .test-detail {{ padding: 0 1rem 0.75rem; font-size: 0.8125rem; }}
  .test-error {{ color: #f97316; margin-bottom: 0.5rem; }}
  .assertion {{ display: flex; align-items: center; gap: 0.375rem;
                padding: 0.25rem 0; }}
  .assertion.pass {{ color: #22c55e; }}
  .assertion.fail {{ color: #ef4444; }}
  .assert-icon {{ font-size: 0.75rem; }}
  .assert-reason {{ color: #94a3b8; margin-left: 0.25rem; }}
</style>
</head>
<body>
<div class="container">
  <h1>{escape(str(title))}</h1>
  <div class="subtitle">{sub}</div>
  <div class="summary">
    <div class="summary-item">
      <div class="summary-value" style="color:{rate_color}">{pass_rate_pct:.0f}%</div>
      <div class="summary-label">Pass rate</div>
    </div>
    <div class="summary-item">
      <div class="summary-value" style="color:#22c55e">{s.passed}</div>
      <div class="summary-label">Passed</div>
    </div>
    <div class="summary-item">
      <div class="summary-value" style="color:#ef4444">{s.failed}</div>
      <div class="summary-label">Failed</div>
    </div>
    <div class="summary-item">
      <div class="summary-value" style="color:#f97316">{s.errors}</div>
      <div class="summary-label">Errors</div>
    </div>
    <div class="summary-item">
      <div class="summary-value">{report.avg_latency:.2f}s</div>
      <div class="summary-label">Avg latency</div>
    </div>
    <div class="summary-item">
      <div class="summary-value">{report.total_tokens}</div>
      <div class="summary-label">Tokens</div>
    </div>
  </div>
  {rows_html}
</div>
<script>
function toggle(el) {{
  var d = el.querySelector('.test-detail');
  d.style.display = d.style.display === 'none' ? 'block' : 'none';
}}
</script>
</body>
</html>"""
