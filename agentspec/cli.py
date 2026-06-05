from __future__ import annotations

import asyncio
import csv
import json
import os
from pathlib import Path

import click
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from agentspec.adapters.openai_compatible_adapter import (
    AdapterConfig,
    OpenAICompatibleAdapter,
)
from agentspec.mcp.results_store import (
    compare_runs as _compare_runs,
)
from agentspec.mcp.results_store import (
    get_run,
    list_runs,
    prune_runs,
    save_result,
)
from agentspec.reporter import ReportConfig, Reporter
from agentspec.runner import TestRunner
from agentspec.scorer import ConsolidatedReport, TestReport
from agentspec.spec import Spec

console = Console()


@click.group()
def main():
    pass


def _run_spec(spec_path, model, base_url, api_key, concurrency, progress_callback=None):
    spec = Spec.from_yaml(spec_path)
    config = AdapterConfig(
        api_key=api_key or os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        model=model or spec.model,
    )
    adapter = OpenAICompatibleAdapter(config)
    runner = TestRunner(spec, adapter, max_concurrency=concurrency)
    return runner.run_all(progress_callback=progress_callback)


@main.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option("--model", default=None, help="Override model")
@click.option("--base-url", default=None, help="Override API base URL")
@click.option(
    "--api-key", default=None, help="Override API key (env: DEEPSEEK_API_KEY)"
)
@click.option("--verbose", "-v", is_flag=True, help="Show assertion details")
@click.option("--concurrency", "-c", default=1, type=int, help="Max parallel tests")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["terminal", "json", "html"]),
    default="terminal",
)
@click.option("--no-progress", is_flag=True, help="Hide progress bar")
def run(spec_path, model, base_url, api_key, verbose, concurrency, output, no_progress):
    """Run agent evaluation against a spec file or directory of specs."""

    async def _run_single(path, progress=None, task_id=None):
        def _progress(name, status):
            if progress and task_id is not None:
                progress.advance(task_id)

        return await _run_spec(
            path, model, base_url, api_key, concurrency,
            progress_callback=_progress if not no_progress else None,
        )

    async def _run_all():
        if os.path.isdir(spec_path):
            yaml_files = sorted(
                f for f in os.listdir(spec_path) if f.endswith((".yaml", ".yml"))
            )
            if not yaml_files:
                click.echo(f"No .yaml files found in {spec_path}", err=True)
                raise click.Abort()

            reports = []
            total = len(yaml_files)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
                disable=no_progress,
            ) as progress:
                task = progress.add_task("Running specs...", total=total)
                for fname in yaml_files:
                    full = os.path.join(spec_path, fname)
                    report = await _run_single(full, progress, task)
                    reports.append(report)
                    progress.update(task, advance=1)

            return ConsolidatedReport(specs=reports)
        else:
            spec = Spec.from_yaml(spec_path)
            total_tests = len(spec.tests)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=console,
                disable=no_progress,
            ) as progress:
                task = progress.add_task(
                    f"Running {Path(spec_path).name}...", total=total_tests
                )

                def _progress(name, status):
                    progress.advance(task)

                return await _run_spec(
                    spec_path, model, base_url, api_key, concurrency,
                    progress_callback=_progress if not no_progress else None,
                )

    report = asyncio.run(_run_all())
    reporter = Reporter(
        ReportConfig(
            verbose=verbose,
            output_json=(output == "json"),
            output_html=(output == "html"),
        )
    )
    reporter.render(report)
    _auto_save(report)


def _auto_save(report):
    """Save report to results store for later retrieval."""
    try:
        if isinstance(report, ConsolidatedReport):
            for r in report.specs:
                d = _report_to_dict(r)
                save_result(d)
        else:
            d = _report_to_dict(report)
            save_result(d)
    except Exception:
        pass


def _report_to_dict(report: TestReport) -> dict:
    return {
        "spec_name": report.spec_name,
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "error": r.error,
                "latency_seconds": r.latency_seconds,
                "token_usage": r.token_usage,
                "assertion_results": [
                    {"name": a.name, "passed": a.passed, "reason": a.reason}
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


@main.command()
@click.argument("spec_file", type=click.Path(exists=True))
def validate(spec_file):
    """Validate a spec file without running it."""
    try:
        spec = Spec.from_yaml(spec_file)
        click.echo(f"OK Spec '{spec.name}' is valid ({len(spec.tests)} test(s))")
    except Exception as e:
        click.echo(f"FAIL Invalid spec: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option("--name", default="My Agent Eval", help="Spec name")
@click.option("--model", default="deepseek-v4-pro", help="Default model")
def init(name, model):
    """Generate a template spec.yaml file."""
    template = (
        "# Agent Evaluation Spec\n"
        f'name: "{name}"\n'
        f"model: {model}\n"
        'system_prompt: "You are a helpful assistant."\n'
        "\n"
        "tests:\n"
        '  - name: "Basic response"\n'
        '    prompt: "Say hello"\n'
        "    assertions:\n"
        "      - type: output_contains\n"
        '        value: "hello"\n'
        "        case_sensitive: true\n"
    )
    click.echo(template)


@main.command()
@click.argument("path", default=".", type=click.Path(exists=True))
def list_specs(path):
    """List spec files in a directory."""
    spec_dir = Path(path)
    if spec_dir.is_file():
        spec_dir = spec_dir.parent

    yaml_files = sorted(spec_dir.glob("*.yaml")) + sorted(spec_dir.glob("*.yml"))
    if not yaml_files:
        click.echo(f"No spec files found in {spec_dir}")
        return

    for f in yaml_files:
        try:
            spec = Spec.from_yaml(str(f))
            click.echo(
                f"  {f.name}  name={spec.name}  tests={len(spec.tests)}"
            )
        except Exception as e:
            click.echo(f"  {f.name}  [invalid: {e}]")


@main.command()
@click.argument("id1", type=str)
@click.argument("id2", type=str)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed diff")
def compare(id1, id2, verbose):
    """Compare two evaluation runs by their run IDs."""
    result = _compare_runs(id1, id2)
    if "error" in result:
        click.echo(f"Error: {result['error']}", err=True)
        raise click.Abort()

    r1 = result["run1"]
    r2 = result["run2"]
    diffs = result["differences"]
    s1 = result.get("summary1", {}) or {}
    s2 = result.get("summary2", {}) or {}

    click.echo()
    click.echo("Comparison Results:")
    click.echo(f"  Run 1: {r1['run_id']} ({r1.get('timestamp', '?')})")
    click.echo(f"  Run 2: {r2['run_id']} ({r2.get('timestamp', '?')})")
    click.echo()

    click.echo(
        f"  Summary 1: {s1.get('passed', 0)}/{s1.get('total', 0)} passed"
        f" ({s1.get('pass_rate', 0) * 100:.0f}%)"
    )
    click.echo(
        f"  Summary 2: {s2.get('passed', 0)}/{s2.get('total', 0)} passed"
        f" ({s2.get('pass_rate', 0) * 100:.0f}%)"
    )
    click.echo()

    if not diffs:
        click.echo("  No differences found.")
    else:
        click.echo(f"  Differences ({len(diffs)}):")
        for d in diffs:
            click.echo(
                f"    {d['test_name']}: {d['status_before']} -> {d['status_after']}"
            )


@main.group()
def results():
    """Manage evaluation results."""


@results.command()
@click.option("--keep", default=50, type=int, help="Number of recent runs to keep")
@click.option("--spec", "spec_name", default=None, help="Filter by spec name")
def prune(keep, spec_name):
    """Remove old evaluation runs, keeping the most recent ones."""
    result = prune_runs(keep=keep, spec_name=spec_name)
    click.echo(
        f"Pruned {result.get('removed', 0)} old run(s)."
        f" {result.get('remaining', 0)} remaining."
    )


@results.command()
@click.argument("output", type=click.Path())
@click.option("--spec", "spec_name", default=None, help="Filter by spec name")
@click.option("--limit", default=None, type=int, help="Max number of runs to export")
def export(output, spec_name, limit):
    """Export evaluation results to a CSV file."""
    runs = list_runs(limit=limit, spec_name=spec_name)
    entries = runs.get("runs", [])

    if not entries:
        click.echo("No runs to export.")
        return

    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "run_id",
                "spec_name",
                "spec_path",
                "timestamp",
                "pass_rate",
                "total",
                "passed",
                "failed",
                "errors",
            ]
        )
        for r in entries:
            writer.writerow(
                [
                    r.get("run_id", ""),
                    r.get("spec_name", ""),
                    r.get("spec_path", ""),
                    r.get("timestamp", ""),
                    r.get("pass_rate", 0),
                    r.get("total", 0),
                    r.get("passed", 0),
                    r.get("failed", 0),
                    r.get("errors", 0),
                ]
            )

    click.echo(f"Exported {len(entries)} run(s) to {output}")


@results.command()
@click.option("--limit", default=20, type=int, help="Number of runs to show")
@click.option("--spec", "spec_name", default=None, help="Filter by spec name")
def history(limit, spec_name):
    """Show recent evaluation runs."""
    runs = list_runs(limit=limit, spec_name=spec_name)
    entries = runs.get("runs", [])
    if not entries:
        click.echo("No runs found.")
        return

    click.echo()
    for r in entries:
        ts = r.get("timestamp", "?")[:19]
        rate = r.get("pass_rate", 0) * 100
        click.echo(
            f"  {r['run_id']}  {ts}  {r.get('spec_name', '?'):20s}  "
            f"{rate:5.0f}%  ({r.get('passed', 0)}/{r.get('total', 0)})"
        )
    click.echo()


@results.command()
@click.argument("run_id", type=str)
def get(run_id):
    """Show details of a specific evaluation run."""
    result = get_run(run_id)
    if "error" in result:
        click.echo(f"Error: {result['error']}", err=True)
        raise click.Abort()
    click.echo(json.dumps(result, indent=2, default=str))


@main.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]), default="bash")
def completion(shell):
    """Print shell completion script. Source it to enable tab completion."""
    if shell == "bash":
        click.echo('eval "$(_AGENTSPEC_COMPLETE=bash_source agentspec)"')
    elif shell == "zsh":
        click.echo('eval "$(_AGENTSPEC_COMPLETE=zsh_source agentspec)"')
    elif shell == "fish":
        click.echo("eval (env _AGENTSPEC_COMPLETE=fish_source agentspec)")


if __name__ == "__main__":
    main()
