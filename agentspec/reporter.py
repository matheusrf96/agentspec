from __future__ import annotations

import json
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

from agentspec.scorer import TestCaseResult, TestReport


@dataclass
class ReportConfig:
    verbose: bool = False
    output_json: bool = False


class Reporter:
    def __init__(self, config: ReportConfig | None = None):
        self.config = config or ReportConfig()
        self.console = Console()

    def render(self, report: TestReport) -> None:
        if self.config.output_json:
            print(json.dumps(self._to_dict(report), indent=2, ensure_ascii=False))
            return

        self._render_terminal(report)

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

    def _render_summary(self, report: TestReport) -> None:
        summary = report.summary

        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="bold")
        table.add_column("Value")

        pass_rate = summary.pass_rate * 100
        pass_color = "green" if pass_rate >= 80 else ("yellow" if pass_rate >= 50 else "red")

        table.add_row(
            "Pass rate",
            f"[{pass_color}]{summary.passed}/{summary.total} ({pass_rate:.0f}%)[/{pass_color}]",
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
                    "status": "error" if r.error else ("pass" if r.passed else "fail"),
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
