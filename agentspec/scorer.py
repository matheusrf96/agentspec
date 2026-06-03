from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agentspec.assertions import AssertionResult


@dataclass
class TestCaseResult:
    __test__ = False
    name: str
    passed: bool
    error: Optional[str] = None
    latency_seconds: float = 0.0
    token_usage: Optional[dict] = None
    assertion_results: list[AssertionResult] = field(default_factory=list)


@dataclass
class Summary:
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total


@dataclass
class TestReport:
    __test__ = False
    spec_name: str
    results: list[TestCaseResult] = field(default_factory=list)

    @property
    def summary(self) -> Summary:
        s = Summary(total=len(self.results))
        for r in self.results:
            if r.error:
                s.errors += 1
            elif r.passed:
                s.passed += 1
            else:
                s.failed += 1
        return s

    @property
    def avg_latency(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.latency_seconds for r in self.results) / len(self.results)

    @property
    def total_tokens(self) -> int:
        total = 0
        for r in self.results:
            if r.token_usage:
                total += r.token_usage.get("total_tokens", 0)
        return total


@dataclass
class ConsolidatedReport:
    specs: list[TestReport] = field(default_factory=list)

    @property
    def summary(self) -> Summary:
        s = Summary()
        for report in self.specs:
            sub = report.summary
            s.total += sub.total
            s.passed += sub.passed
            s.failed += sub.failed
            s.errors += sub.errors
        return s

    @property
    def avg_latency(self) -> float:
        total_cases = sum(len(r.results) for r in self.specs)
        if total_cases == 0:
            return 0.0
        total = sum(result.latency_seconds for r in self.specs for result in r.results)
        return total / total_cases

    @property
    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.specs)
