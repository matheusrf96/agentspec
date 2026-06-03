from __future__ import annotations

import json
import re
from dataclasses import dataclass

import jsonschema

from agentspec.adapters.base import AgentResponse
from agentspec.spec import (
    Assertion,
    LatencyUnderAssertion,
    OutputContainsAnyAssertion,
    OutputContainsAssertion,
    OutputJsonSchemaAssertion,
    OutputMatchesAssertion,
    ToolCalledAssertion,
)


@dataclass
class AssertionResult:
    name: str
    passed: bool
    reason: str = ""


def evaluate_assertion(
    assertion: Assertion, response: AgentResponse
) -> AssertionResult:
    match assertion:
        case ToolCalledAssertion():
            return _eval_tool_called(assertion, response)
        case OutputContainsAssertion():
            return _eval_output_contains(assertion, response)
        case OutputContainsAnyAssertion():
            return _eval_output_contains_any(assertion, response)
        case OutputMatchesAssertion():
            return _eval_output_matches(assertion, response)
        case LatencyUnderAssertion():
            return _eval_latency_under(assertion, response)
        case OutputJsonSchemaAssertion():
            return _eval_output_json_schema(assertion, response)
        case _:
            return AssertionResult(
                name="unknown",
                passed=False,
                reason=f"Unknown assertion type: {type(assertion).__name__}",
            )


def _eval_tool_called(
    assertion: ToolCalledAssertion, response: AgentResponse
) -> AssertionResult:
    for tc in response.tool_calls:
        if tc.name == assertion.tool_name:
            if assertion.args is not None:
                try:
                    actual = (
                        json.loads(tc.args) if isinstance(tc.args, str) else tc.args
                    )
                except json.JSONDecodeError:
                    actual = tc.args
                if _dict_contains(actual, assertion.args):
                    return AssertionResult(
                        name=f"tool_called({assertion.tool_name})",
                        passed=True,
                        reason=f"Tool {assertion.tool_name} called with matching args",
                    )
                return AssertionResult(
                    name=f"tool_called({assertion.tool_name})",
                    passed=False,
                    reason=(
                        f"Tool {assertion.tool_name} called but args mismatch."
                        f" Got {actual}"
                    ),
                )
            return AssertionResult(
                name=f"tool_called({assertion.tool_name})",
                passed=True,
                reason=f"Tool {assertion.tool_name} was called",
            )
    return AssertionResult(
        name=f"tool_called({assertion.tool_name})",
        passed=False,
        reason=(
            f"Tool {assertion.tool_name} was never called. "
            f"Called: {[t.name for t in response.tool_calls]}"
        ),
    )


def _eval_output_contains(
    assertion: OutputContainsAssertion, response: AgentResponse
) -> AssertionResult:
    text = response.text if assertion.case_sensitive else response.text.lower()
    value = assertion.value if assertion.case_sensitive else assertion.value.lower()
    if value in text:
        return AssertionResult(
            name=f"output_contains({assertion.value!r})",
            passed=True,
            reason=f"Output contains {assertion.value!r}",
        )
    return AssertionResult(
        name=f"output_contains({assertion.value!r})",
        passed=False,
        reason=f"Output does not contain {assertion.value!r}",
    )


def _eval_output_contains_any(
    assertion: OutputContainsAnyAssertion, response: AgentResponse
) -> AssertionResult:
    text_lower = response.text.lower()
    results = [v.lower() in text_lower for v in assertion.values]
    if assertion.match == "any":
        passed = any(results)
    else:
        passed = all(results)

    matched = [v for v, r in zip(assertion.values, results) if r]
    missing = [v for v, r in zip(assertion.values, results) if not r]

    return AssertionResult(
        name=f"output_contains_any(match={assertion.match})",
        passed=passed,
        reason=f"Matched: {matched}, Missing: {missing}"
        if not passed
        else f"Matched: {matched}",
    )


def _eval_output_matches(
    assertion: OutputMatchesAssertion, response: AgentResponse
) -> AssertionResult:
    if re.search(assertion.pattern, response.text):
        return AssertionResult(
            name=f"output_matches({assertion.pattern!r})",
            passed=True,
            reason=f"Output matches pattern {assertion.pattern!r}",
        )
    return AssertionResult(
        name=f"output_matches({assertion.pattern!r})",
        passed=False,
        reason=f"Output does not match pattern {assertion.pattern!r}",
    )


def _eval_latency_under(
    assertion: LatencyUnderAssertion, response: AgentResponse
) -> AssertionResult:
    if response.latency_seconds <= assertion.max_seconds:
        return AssertionResult(
            name=f"latency_under({assertion.max_seconds}s)",
            passed=True,
            reason=(
                f"Response in {response.latency_seconds:.2f}s"
                f" (limit {assertion.max_seconds}s)"
            ),
        )
    return AssertionResult(
        name=f"latency_under({assertion.max_seconds}s)",
        passed=False,
        reason=(
            f"Response took {response.latency_seconds:.2f}s"
            f" (limit {assertion.max_seconds}s)"
        ),
    )


def _eval_output_json_schema(
    assertion: OutputJsonSchemaAssertion, response: AgentResponse
) -> AssertionResult:
    try:
        data = json.loads(response.text)
    except json.JSONDecodeError as e:
        return AssertionResult(
            name="output_json_schema",
            passed=False,
            reason=f"Output is not valid JSON: {e}",
        )
    try:
        jsonschema.validate(data, assertion.json_schema)
        return AssertionResult(
            name="output_json_schema",
            passed=True,
            reason="Output matches JSON schema",
        )
    except jsonschema.ValidationError as e:
        return AssertionResult(
            name="output_json_schema",
            passed=False,
            reason=f"Schema validation failed: {e.message}",
        )


def _dict_contains(actual: dict, expected: dict) -> bool:
    for key, value in expected.items():
        if key not in actual:
            return False
        if isinstance(value, dict) and isinstance(actual[key], dict):
            if not _dict_contains(actual[key], value):
                return False
        elif actual[key] != value:
            return False
    return True
