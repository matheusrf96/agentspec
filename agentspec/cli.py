from __future__ import annotations

import asyncio
import os

import click

from agentspec.adapters.openai_compatible_adapter import (
    AdapterConfig,
    OpenAICompatibleAdapter,
)
from agentspec.reporter import ReportConfig, Reporter
from agentspec.runner import TestRunner
from agentspec.scorer import ConsolidatedReport
from agentspec.spec import Spec


@click.group()
def main():
    pass


def _run_spec(spec_path, model, base_url, api_key):
    spec = Spec.from_yaml(spec_path)
    config = AdapterConfig(
        api_key=api_key or os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        model=model or spec.model,
    )
    adapter = OpenAICompatibleAdapter(config)
    runner = TestRunner(spec, adapter)
    return runner.run_all()


@main.command()
@click.argument("spec_path", type=click.Path(exists=True))
@click.option("--model", default=None, help="Override model")
@click.option("--base-url", default=None, help="Override API base URL")
@click.option(
    "--api-key", default=None, help="Override API key (env: DEEPSEEK_API_KEY)"
)
@click.option("--verbose", "-v", is_flag=True, help="Show assertion details")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["terminal", "json", "html"]),
    default="terminal",
)
def run(spec_path, model, base_url, api_key, verbose, output):
    """Run agent evaluation against a spec file or directory of specs."""

    async def _run_single(path):
        return await _run_spec(path, model, base_url, api_key)

    async def _run_all():
        if os.path.isdir(spec_path):
            yaml_files = sorted(
                f for f in os.listdir(spec_path) if f.endswith((".yaml", ".yml"))
            )
            if not yaml_files:
                click.echo(f"No .yaml files found in {spec_path}", err=True)
                raise click.Abort()

            reports = []
            for fname in yaml_files:
                full = os.path.join(spec_path, fname)
                reports.append(await _run_single(full))

            return ConsolidatedReport(specs=reports)
        else:
            return await _run_single(spec_path)

    report = asyncio.run(_run_all())
    reporter = Reporter(
        ReportConfig(
            verbose=verbose,
            output_json=(output == "json"),
            output_html=(output == "html"),
        )
    )
    reporter.render(report)


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


if __name__ == "__main__":
    main()
