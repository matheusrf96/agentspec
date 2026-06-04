from __future__ import annotations

import asyncio

import pytest

from agentspec.adapters.base import AgentAdapter, AgentResponse
from agentspec.runner import TestRunner
from agentspec.spec import Spec


class _MockAdapter(AgentAdapter):
    def __init__(self, delay: float = 0):
        self.delay = delay
        self.call_count = 0

    async def run(self, prompt, system_prompt=None, model=None, fixtures=None):
        self.call_count += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return AgentResponse(text=f"Response to: {prompt}")


@pytest.fixture
def spec():
    return Spec(
        name="test-spec",
        tests=[
            {"name": "test-a", "prompt": "prompt-a", "assertions": []},
            {"name": "test-b", "prompt": "prompt-b", "assertions": []},
            {"name": "test-c", "prompt": "prompt-c", "assertions": []},
        ],
    )


class TestSequential:
    pytestmark = pytest.mark.asyncio

    async def test_runs_sequentially_by_default(self, spec):
        adapter = _MockAdapter(delay=0.01)
        runner = TestRunner(spec, adapter)
        report = await runner.run_all()

        assert len(report.results) == 3
        assert report.results[0].name == "test-a"
        assert report.results[1].name == "test-b"
        assert report.results[2].name == "test-c"

    async def test_single_test(self):
        spec = Spec(
            name="single",
            tests=[{"name": "only", "prompt": "hello", "assertions": []}],
        )
        adapter = _MockAdapter()
        runner = TestRunner(spec, adapter)
        report = await runner.run_all()

        assert len(report.results) == 1
        assert report.results[0].passed is True

    async def test_concurrency_1_is_sequential(self, spec):
        adapter = _MockAdapter(delay=0.01)
        runner = TestRunner(spec, adapter, max_concurrency=1)
        report = await runner.run_all()

        assert len(report.results) == 3


class TestConcurrent:
    pytestmark = pytest.mark.asyncio

    async def test_runs_concurrently(self, spec):
        adapter = _MockAdapter(delay=0.05)
        runner = TestRunner(spec, adapter, max_concurrency=3)

        start = asyncio.get_event_loop().time()
        report = await runner.run_all()
        elapsed = asyncio.get_event_loop().time() - start

        assert len(report.results) == 3
        assert elapsed < 0.10  # 3 tests at 50ms each should complete in <100ms

    async def test_concurrency_limit(self, spec):
        adapter = _MockAdapter(delay=0.05)
        runner = TestRunner(spec, adapter, max_concurrency=2)

        start = asyncio.get_event_loop().time()
        report = await runner.run_all()
        elapsed = asyncio.get_event_loop().time() - start

        assert len(report.results) == 3
        # With concurrency=2 and 3 tests at 50ms each, should take ~100ms
        assert elapsed >= 0.05

    async def test_error_in_one_test_does_not_affect_others(self):
        class _FailingAdapter(AgentAdapter):
            async def run(self, prompt, system_prompt=None, model=None, fixtures=None):
                if "fail" in prompt:
                    raise ValueError("Intentional error")
                return AgentResponse(text="ok")

        spec = Spec(
            name="err-spec",
            tests=[
                {"name": "good-1", "prompt": "hello", "assertions": []},
                {"name": "bad", "prompt": "fail-please", "assertions": []},
                {"name": "good-2", "prompt": "world", "assertions": []},
            ],
        )
        adapter = _FailingAdapter()
        runner = TestRunner(spec, adapter, max_concurrency=3)
        report = await runner.run_all()

        assert report.results[0].passed is True
        assert report.results[1].passed is False
        assert report.results[1].error is not None
        assert "Intentional error" in report.results[1].error
        assert report.results[2].passed is True
