import json

from agentspec.adapters.base import AgentResponse, ToolCall
from agentspec.assertions import evaluate_assertion
from agentspec.spec import (
    LatencyUnderAssertion,
    OutputContainsAnyAssertion,
    OutputContainsAssertion,
    OutputJsonSchemaAssertion,
    OutputMatchesAssertion,
    ToolCalledAssertion,
)


def test_tool_called_passes():
    response = AgentResponse(
        text="",
        tool_calls=[ToolCall(name="get_stock_price", args='{"symbol": "AAPL"}')],
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
        tool_calls=[ToolCall(name="get_stock_price", args='{"symbol": "AAPL"}')],
    )
    assertion = ToolCalledAssertion(
        tool_name="get_stock_price", args={"symbol": "AAPL"}
    )
    result = evaluate_assertion(assertion, response)
    assert result.passed is True


def test_tool_called_with_args_mismatch():
    response = AgentResponse(
        text="",
        tool_calls=[ToolCall(name="get_stock_price", args='{"symbol": "MSFT"}')],
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
        json_schema={
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
        json_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }
    )
    result = evaluate_assertion(assertion, response)
    assert result.passed is False
