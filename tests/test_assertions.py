# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
from __future__ import annotations

import json

from agentspec.adapters.base import AgentResponse, ToolCall
from agentspec.assertions import evaluate_assertion
from agentspec.spec import (
    CostUnderAssertion,
    LatencyUnderAssertion,
    OutputContainsAnyAssertion,
    OutputContainsAssertion,
    OutputJsonSchemaAssertion,
    OutputLengthBetweenAssertion,
    OutputMatchesAssertion,
    OutputNotContainsAssertion,
    ToolCallCountAssertion,
    ToolCalledAssertion,
)


def test_tool_called_passes():
    response = AgentResponse(
        text="",
        tool_calls=[ToolCall(name="get_stock_price", args={"symbol": "AAPL"})],
    )
    assertion = ToolCalledAssertion(tool_name="get_stock_price")
    result = evaluate_assertion(assertion, response)
    assert result.passed is True


def test_tool_called_fails():
    response = AgentResponse(text="", tool_calls=[])
    assertion = ToolCalledAssertion(tool_name="get_stock_price")
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


def test_tool_called_with_args_passes():
    response = AgentResponse(
        text="",
        tool_calls=[ToolCall(name="get_stock_price", args={"symbol": "AAPL"})],
    )
    assertion = ToolCalledAssertion(
        tool_name="get_stock_price", args={"symbol": "AAPL"}
    )
    result = evaluate_assertion(assertion, response)
    assert result.passed is True


def test_tool_called_with_args_mismatch():
    response = AgentResponse(
        text="",
        tool_calls=[ToolCall(name="get_stock_price", args={"symbol": "MSFT"})],
    )
    assertion = ToolCalledAssertion(
        tool_name="get_stock_price", args={"symbol": "AAPL"}
    )
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


def test_output_contains_passes():
    response = AgentResponse(text="The stock price is $150.25")
    assertion = OutputContainsAssertion(value="$150.25")
    result = evaluate_assertion(assertion, response)
    assert result.passed is True


def test_output_contains_case_sensitive():
    response = AgentResponse(text="Hello World")
    assertion = OutputContainsAssertion(value="hello", case_sensitive=False)
    result = evaluate_assertion(assertion, response)
    assert result.passed is True


def test_output_contains_any_passes():
    response = AgentResponse(text="not found")
    assertion = OutputContainsAnyAssertion(values=["not found", "error", "invalid"])
    result = evaluate_assertion(assertion, response)
    assert result.passed is True


def test_output_contains_any_fails():
    response = AgentResponse(text="everything is fine")
    assertion = OutputContainsAnyAssertion(values=["not found", "error", "invalid"])
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


def test_output_matches_passes():
    response = AgentResponse(text="$150.25")
    assertion = OutputMatchesAssertion(pattern=r"\$\d+\.?\d*")
    result = evaluate_assertion(assertion, response)
    assert result.passed is True


def test_output_matches_fails():
    response = AgentResponse(text="150 dollars")
    assertion = OutputMatchesAssertion(pattern=r"\$\d+")
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


def test_latency_under_passes():
    response = AgentResponse(text="", latency_seconds=2.5)
    assertion = LatencyUnderAssertion(max_seconds=10.0)
    result = evaluate_assertion(assertion, response)
    assert result.passed is True


def test_latency_under_fails():
    response = AgentResponse(text="", latency_seconds=15.0)
    assertion = LatencyUnderAssertion(max_seconds=10.0)
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


def test_output_json_schema_passes():
    response = AgentResponse(text=json.dumps({"name": "test", "value": 42}))
    assertion = OutputJsonSchemaAssertion(
        schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }
    )
    result = evaluate_assertion(assertion, response)
    assert result.passed is True


def test_output_json_schema_fails():
    response = AgentResponse(text=json.dumps({"name": 123}))
    assertion = OutputJsonSchemaAssertion(
        schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }
    )
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


def test_unknown_assertion_type():
    class FakeAssertion:
        type = "fake"

    # pyright: ignore
    result = evaluate_assertion(FakeAssertion(), AgentResponse(text=""))
    assert result.passed is False
    assert "unknown" in result.name


def test_tool_called_args_invalid_json():
    response = AgentResponse(
        text="",
        tool_calls=[
            ToolCall(  # pyright: ignore[reportArgumentType]
                name="get_stock_price", args="not valid json{{{"
            )
        ],
    )
    assertion = ToolCalledAssertion(
        tool_name="get_stock_price", args={"symbol": "AAPL"}
    )
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


def test_output_contains_fails():
    response = AgentResponse(text="Hello World")
    assertion = OutputContainsAssertion(value="Goodbye")
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


def test_output_contains_any_match_all_passes():
    response = AgentResponse(text="hello world foo")
    assertion = OutputContainsAnyAssertion(values=["hello", "foo"], match="all")
    result = evaluate_assertion(assertion, response)
    assert result.passed is True


def test_output_contains_any_match_all_fails():
    response = AgentResponse(text="hello world")
    assertion = OutputContainsAnyAssertion(values=["hello", "missing"], match="all")
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


def test_output_json_schema_invalid_json():
    response = AgentResponse(text="not json at all")
    assertion = OutputJsonSchemaAssertion(schema={"type": "object"})
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


def test_tool_called_args_nested_dict_matches():
    response = AgentResponse(
        text="",
        tool_calls=[
            ToolCall(name="get_weather", args={"location": {"city": "London"}})
        ],
    )
    assertion = ToolCalledAssertion(
        tool_name="get_weather", args={"location": {"city": "London"}}
    )
    result = evaluate_assertion(assertion, response)
    assert result.passed is True


def test_tool_called_args_nested_dict_mismatch():
    response = AgentResponse(
        text="",
        tool_calls=[ToolCall(name="get_weather", args={"location": {"city": "Paris"}})],
    )
    assertion = ToolCalledAssertion(
        tool_name="get_weather", args={"location": {"city": "London"}}
    )
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


def test_tool_called_args_expected_has_extra_key():
    response = AgentResponse(
        text="",
        tool_calls=[ToolCall(name="test", args={"a": 1})],
    )
    assertion = ToolCalledAssertion(tool_name="test", args={"a": 1, "b": 2})
    result = evaluate_assertion(assertion, response)
    assert result.passed is False


class TestToolCallCount:
    def test_exact_match(self):
        response = AgentResponse(
            text="",
            tool_calls=[ToolCall(name="a", args={}), ToolCall(name="b", args={})],
        )
        assertion = ToolCallCountAssertion(exact=2)
        assert evaluate_assertion(assertion, response).passed is True

    def test_exact_mismatch(self):
        response = AgentResponse(text="", tool_calls=[ToolCall(name="a", args={})])
        assertion = ToolCallCountAssertion(exact=2)
        assert evaluate_assertion(assertion, response).passed is False

    def test_min_count(self):
        response = AgentResponse(
            text="",
            tool_calls=[
                ToolCall(name="a", args={}),
                ToolCall(name="b", args={}),
                ToolCall(name="c", args={}),
            ],
        )
        assertion = ToolCallCountAssertion(min_count=2)
        assert evaluate_assertion(assertion, response).passed is True

    def test_min_count_fails(self):
        response = AgentResponse(text="", tool_calls=[ToolCall(name="a", args={})])
        assertion = ToolCallCountAssertion(min_count=2)
        assert evaluate_assertion(assertion, response).passed is False

    def test_max_count(self):
        response = AgentResponse(text="", tool_calls=[ToolCall(name="a", args={})])
        assertion = ToolCallCountAssertion(max_count=2)
        assert evaluate_assertion(assertion, response).passed is True

    def test_max_count_fails(self):
        response = AgentResponse(
            text="",
            tool_calls=[
                ToolCall(name="a", args={}),
                ToolCall(name="b", args={}),
                ToolCall(name="c", args={}),
            ],
        )
        assertion = ToolCallCountAssertion(max_count=2)
        assert evaluate_assertion(assertion, response).passed is False

    def test_no_tool_calls_exact_zero(self):
        response = AgentResponse(text="", tool_calls=[])
        assertion = ToolCallCountAssertion(exact=0)
        assert evaluate_assertion(assertion, response).passed is True


class TestOutputNotContains:
    def test_passes_when_absent(self):
        response = AgentResponse(text="hello world")
        assertion = OutputNotContainsAssertion(value="forbidden")
        result = evaluate_assertion(assertion, response)
        assert result.passed is True

    def test_fails_when_present(self):
        response = AgentResponse(text="contains forbidden content")
        assertion = OutputNotContainsAssertion(value="forbidden")
        result = evaluate_assertion(assertion, response)
        assert result.passed is False

    def test_case_insensitive(self):
        response = AgentResponse(text="Forbidden Content")
        assertion = OutputNotContainsAssertion(value="forbidden", case_sensitive=False)
        assert evaluate_assertion(assertion, response).passed is False

    def test_case_sensitive(self):
        response = AgentResponse(text="Forbidden Content")
        assertion = OutputNotContainsAssertion(value="forbidden", case_sensitive=True)
        assert evaluate_assertion(assertion, response).passed is True


class TestCostUnder:
    def test_passes_when_under(self):
        response = AgentResponse(
            text="",
            token_usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        )
        assertion = CostUnderAssertion(
            max_cost=0.01,
            input_price_per_token=0.00001,
            output_price_per_token=0.00002,
        )
        result = evaluate_assertion(assertion, response)
        assert result.passed is True

    def test_fails_when_over(self):
        response = AgentResponse(
            text="",
            token_usage={
                "prompt_tokens": 10000,
                "completion_tokens": 5000,
                "total_tokens": 15000,
            },
        )
        assertion = CostUnderAssertion(
            max_cost=0.01,
            input_price_per_token=0.00001,
            output_price_per_token=0.00002,
        )
        result = evaluate_assertion(assertion, response)
        assert result.passed is False

    def test_fails_when_no_token_usage(self):
        response = AgentResponse(text="")
        assertion = CostUnderAssertion(max_cost=0.01)
        result = evaluate_assertion(assertion, response)
        assert result.passed is False

    def test_zero_price_defaults(self):
        response = AgentResponse(
            text="",
            token_usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        )
        assertion = CostUnderAssertion(max_cost=0.01)
        result = evaluate_assertion(assertion, response)
        assert result.passed is True  # cost is 0 with no pricing


class TestOutputLengthBetween:
    def test_chars_within_bounds(self):
        response = AgentResponse(text="hello")
        assertion = OutputLengthBetweenAssertion(min_length=1, max_length=10)
        assert evaluate_assertion(assertion, response).passed is True

    def test_chars_too_short(self):
        response = AgentResponse(text="hi")
        assertion = OutputLengthBetweenAssertion(min_length=5)
        assert evaluate_assertion(assertion, response).passed is False

    def test_chars_too_long(self):
        response = AgentResponse(text="hello world this is long")
        assertion = OutputLengthBetweenAssertion(max_length=10)
        assert evaluate_assertion(assertion, response).passed is False

    def test_tokens_within_bounds(self):
        response = AgentResponse(
            text="some text",
            token_usage={"completion_tokens": 50},
        )
        assertion = OutputLengthBetweenAssertion(
            min_length=10, max_length=100, unit="tokens"
        )
        assert evaluate_assertion(assertion, response).passed is True

    def test_tokens_no_usage_fails(self):
        response = AgentResponse(text="some text")
        assertion = OutputLengthBetweenAssertion(
            min_length=1, max_length=100, unit="tokens"
        )
        assert evaluate_assertion(assertion, response).passed is False

    def test_exact_bounds(self):
        response = AgentResponse(text="12345")
        assertion = OutputLengthBetweenAssertion(min_length=5, max_length=5)
        assert evaluate_assertion(assertion, response).passed is True
