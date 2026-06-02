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
from agentspec.spec import Spec


@click.group()
def main():
    pass


@main.command()
@click.argument("spec_file", type=click.Path(exists=True))
@click.option("--model", default=None, help="Override model (default: deepseek-v4-pro)")
@click.option("--base-url", default=None, help="Override API base URL")
@click.option("--api-key", default=None, help="Override API key (env: DEEPSEEK_API_KEY)")
@click.option("--verbose", "-v", is_flag=True, help="Show per-assertion details")
@click.option("--output", "-o", type=click.Choice(["terminal", "json"]), default="terminal")
def run(spec_file, model, base_url, api_key, verbose, output):
    """Run agent evaluation against a spec file."""
    async def _run():
        spec = Spec.from_yaml(spec_file)

        config = AdapterConfig(
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
            model=model or spec.model,
        )
        adapter = OpenAICompatibleAdapter(config)
        runner = TestRunner(spec, adapter)
        report = await runner.run_all()

        reporter = Reporter(ReportConfig(verbose=verbose, output_json=(output == "json")))
        reporter.render(report)

    asyncio.run(_run())


@main.command()
@click.argument("spec_file", type=click.Path(exists=True))
def validate(spec_file):
    """Validate a spec file without running it."""
    try:
        spec = Spec.from_yaml(spec_file)
        click.echo(f"✅ Spec '{spec.name}' is valid ({len(spec.tests)} test(s))")
    except Exception as e:
        click.echo(f"❌ Invalid spec: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option("--name", default="My Agent Eval", help="Spec name")
@click.option("--model", default="deepseek-v4-pro", help="Default model")
def init(name, model):
    """Generate a template spec.yaml file."""
    template = f"""# Agent Evaluation Spec
name: "{name}"
model: {model}
system_prompt: "You are a helpful assistant."

tests:
  - name: "Basic response"
    prompt: "Say hello"
    assertions:
      - type: output_contains
        value: "hello"
        case_sensitive: true
"""
    click.echo(template)


if __name__ == "__main__":
    main()
