from __future__ import annotations

import traceback

from agentspec.adapters.base import AgentAdapter
from agentspec.assertions import evaluate_assertion
from agentspec.scorer import TestCaseResult, TestReport
from agentspec.spec import Spec


class TestRunner:
    def __init__(self, spec: Spec, adapter: AgentAdapter):
        self.spec = spec
        self.adapter = adapter

    async def run_all(self) -> TestReport:
        results: list[TestCaseResult] = []

        for test in self.spec.tests:
            result = await self._run_test(test)
            results.append(result)

        return TestReport(spec_name=self.spec.name, results=results)

    async def _run_test(self, test) -> TestCaseResult:
        try:
            response = await self.adapter.run(
                prompt=test.prompt,
                system_prompt=self.spec.system_prompt,
                model=self.spec.model,
            )
        except Exception as e:
            return TestCaseResult(
                name=test.name,
                passed=False,
                error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
            )

        assertion_results = [
            evaluate_assertion(a, response) for a in test.assertions
        ]

        all_passed = all(ar.passed for ar in assertion_results)

        return TestCaseResult(
            name=test.name,
            passed=all_passed,
            latency_seconds=response.latency_seconds,
            token_usage=response.token_usage,
            assertion_results=assertion_results,
        )
