from __future__ import annotations

import enum
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field


class AssertionType(str, enum.Enum):
    TOOL_CALLED = "tool_called"
    OUTPUT_CONTAINS = "output_contains"
    OUTPUT_CONTAINS_ANY = "output_contains_any"
    OUTPUT_MATCHES = "output_matches"
    LATENCY_UNDER = "latency_under"
    OUTPUT_JSON_SCHEMA = "output_json_schema"
    TOOL_CALL_COUNT = "tool_call_count"
    OUTPUT_NOT_CONTAINS = "output_not_contains"
    COST_UNDER = "cost_under"
    OUTPUT_LENGTH_BETWEEN = "output_length_between"


class ToolCalledAssertion(BaseModel):
    type: Literal[AssertionType.TOOL_CALLED] = AssertionType.TOOL_CALLED
    tool_name: str
    args: Optional[dict] = None


class OutputContainsAssertion(BaseModel):
    type: Literal[AssertionType.OUTPUT_CONTAINS] = AssertionType.OUTPUT_CONTAINS
    value: str
    case_sensitive: bool = True


class OutputContainsAnyAssertion(BaseModel):
    type: Literal[AssertionType.OUTPUT_CONTAINS_ANY] = AssertionType.OUTPUT_CONTAINS_ANY
    values: list[str]
    match: Literal["any", "all"] = "any"


class OutputMatchesAssertion(BaseModel):
    type: Literal[AssertionType.OUTPUT_MATCHES] = AssertionType.OUTPUT_MATCHES
    pattern: str


class LatencyUnderAssertion(BaseModel):
    type: Literal[AssertionType.LATENCY_UNDER] = AssertionType.LATENCY_UNDER
    max_seconds: float = Field(gt=0)


class OutputJsonSchemaAssertion(BaseModel):
    type: Literal[AssertionType.OUTPUT_JSON_SCHEMA] = AssertionType.OUTPUT_JSON_SCHEMA
    json_schema: dict = Field(alias="schema")

    model_config = {"populate_by_name": True}


class ToolCallCountAssertion(BaseModel):
    type: Literal[AssertionType.TOOL_CALL_COUNT] = AssertionType.TOOL_CALL_COUNT
    exact: Optional[int] = None
    min_count: Optional[int] = Field(default=None, ge=0)
    max_count: Optional[int] = Field(default=None, ge=0)


class OutputNotContainsAssertion(BaseModel):
    type: Literal[AssertionType.OUTPUT_NOT_CONTAINS] = AssertionType.OUTPUT_NOT_CONTAINS
    value: str
    case_sensitive: bool = True


class CostUnderAssertion(BaseModel):
    type: Literal[AssertionType.COST_UNDER] = AssertionType.COST_UNDER
    max_cost: float = Field(gt=0)
    input_price_per_token: Optional[float] = None
    output_price_per_token: Optional[float] = None


class OutputLengthBetweenAssertion(BaseModel):
    type: Literal[AssertionType.OUTPUT_LENGTH_BETWEEN] = (
        AssertionType.OUTPUT_LENGTH_BETWEEN
    )  # noqa: E501
    min_length: Optional[int] = Field(default=None, ge=0)
    max_length: Optional[int] = Field(default=None, ge=0)
    unit: Literal["chars", "tokens"] = "chars"


Assertion = (
    ToolCalledAssertion
    | OutputContainsAssertion
    | OutputContainsAnyAssertion
    | OutputMatchesAssertion
    | LatencyUnderAssertion
    | OutputJsonSchemaAssertion
    | ToolCallCountAssertion
    | OutputNotContainsAssertion
    | CostUnderAssertion
    | OutputLengthBetweenAssertion
)


class ConversationEntry(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    tool_calls: Optional[list[dict]] = None


class MockTool(BaseModel):
    name: str
    description: Optional[str] = None
    response: str


class CannedResponse(BaseModel):
    prompt_contains: str
    output: str = ""
    tool_calls: Optional[list[dict]] = None


class Fixtures(BaseModel):
    conversation_history: list[ConversationEntry] = Field(default_factory=list)
    mock_tools: list[MockTool] = Field(default_factory=list)
    canned_responses: list[CannedResponse] = Field(default_factory=list)


class TestCase(BaseModel):
    name: str
    prompt: str
    assertions: list[Assertion] = Field(default_factory=list)
    context: Optional[dict] = None


class Spec(BaseModel):
    name: str
    description: Optional[str] = None
    model: str = "deepseek-v4-pro"
    system_prompt: Optional[str] = None
    tests: list[TestCase] = Field(default_factory=list)
    fixtures: Optional[Fixtures] = None

    @classmethod
    def _include_constructor(cls, loader: yaml.SafeLoader, node: yaml.Node) -> list:
        path = str(loader.construct_scalar(node))  # type: ignore[arg-type]
        stream = loader.stream
        base = (
            Path(stream.name).parent  # type: ignore[attr-defined]
            if stream is not None and hasattr(stream, "name")
            else Path.cwd()
        )  # noqa: E501
        resolved = (base / path).resolve()
        with open(resolved) as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("tests", data.get("test_cases", []))
        return []

    @classmethod
    def from_yaml(cls, path: str) -> Spec:
        yaml.SafeLoader.add_constructor("!include", cls._include_constructor)
        with open(path) as f:
            data = yaml.safe_load(f)
        if "tests" in data:
            flat = []
            for item in data["tests"]:
                if isinstance(item, list):
                    flat.extend(item)
                else:
                    flat.append(item)
            data["tests"] = flat
        return cls.model_validate(data)

    @classmethod
    def from_yaml_string(cls, content: str) -> Spec:
        data = yaml.safe_load(content)
        return cls.model_validate(data)
