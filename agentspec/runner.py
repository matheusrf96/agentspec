from __future__ import annotations

import asyncio
import traceback

from agentspec.adapters.base import AgentAdapter
from agentspec.assertions import evaluate_assertion
from agentspec.scorer import TestCaseResult, TestReport
from agentspec.spec import Spec


class TestRunner:
    def __init__(self, spec: Spec, adapter: AgentAdapter, max_concurrency: int = 1):
        self.spec = spec
        self.adapter = adapter
        self.max_concurrency = max_concurrency

    async def run_all(self) -> TestReport:
        if self.max_concurrency <= 1:
            results: list[TestCaseResult] = []
            for test in self.spec.tests:
                result = await self._run_test(test)
                results.append(result)
        else:
            sem = asyncio.Semaphore(self.max_concurrency)

            async def _run(sem, test):
                async with sem:
                    return await self._run_test(test)

            tasks = [_run(sem, t) for t in self.spec.tests]
            results = await asyncio.gather(*tasks)

        return TestReport(spec_name=self.spec.name, results=results)

    async def _run_test(self, test) -> TestCaseResult:
        try:
            fixtures_dict = (
                self.spec.fixtures.model_dump(mode="json")
                if self.spec.fixtures
                else None
            )
            response = await self.adapter.run(
                prompt=test.prompt,
                system_prompt=self.spec.system_prompt,
                model=self.spec.model,
                fixtures=fixtures_dict,
            )
        except Exception as e:
            return TestCaseResult(
                name=test.name,
                passed=False,
                error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
            )

        assertion_results = [evaluate_assertion(a, response) for a in test.assertions]

        all_passed = all(ar.passed for ar in assertion_results)

        return TestCaseResult(
            name=test.name,
            passed=all_passed,
            latency_seconds=response.latency_seconds,
            token_usage=response.token_usage,
            assertion_results=assertion_results,
        )
