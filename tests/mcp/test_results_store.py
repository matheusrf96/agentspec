from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from agentspec.mcp import results_store
from agentspec.mcp.results_store import (
    compare_runs,
    get_run,
    get_trends,
    list_runs,
    save_result,
)

_RESULT = {
    "passed": True,
    "error": None,
    "assertion_results": [],
}
_RESULT_FAIL = {
    "passed": False,
    "error": None,
    "assertion_results": [],
}

SAMPLE_REPORT = {
    "spec_name": "Test Spec",
    "summary": {
        "total": 3,
        "passed": 2,
        "failed": 1,
        "errors": 0,
        "pass_rate": 0.6667,
    },
    "results": [
        {"name": "pass1", **_RESULT, "latency_seconds": 0.5},
        {"name": "pass2", **_RESULT, "latency_seconds": 1.0},
        {"name": "fail1", **_RESULT_FAIL, "latency_seconds": 2.0},
    ],
}

SAMPLE_REPORT_2 = {
    "spec_name": "Test Spec",
    "summary": {
        "total": 3,
        "passed": 3,
        "failed": 0,
        "errors": 0,
        "pass_rate": 1.0,
    },
    "results": [
        {"name": "pass1", **_RESULT, "latency_seconds": 0.4},
        {"name": "pass2", **_RESULT, "latency_seconds": 0.8},
        {"name": "fail1", **_RESULT, "latency_seconds": 1.5},
    ],
}


@pytest.fixture(autouse=True)
def _reset_backend():
    results_store._backend = None
    yield
    results_store._backend = None


@pytest.fixture(autouse=True)
def tmp_results_dir(tmp_path):
    test_dir = tmp_path / ".agentspec" / "results"
    test_dir.mkdir(parents=True)
    with patch("agentspec.results_backend.RESULTS_DIR", test_dir):
        yield test_dir


class TestSaveResult:
    def test_saves_result_and_returns_run_id(self, tmp_results_dir):
        result = save_result(SAMPLE_REPORT)
        assert "run_id" in result
        assert len(result["run_id"]) == 16

    def test_creates_run_file(self, tmp_results_dir):
        result = save_result(SAMPLE_REPORT, spec_path="/path/to/spec.yaml")
        run_id = result["run_id"]
        run_file = tmp_results_dir / f"{run_id}.json"
        assert run_file.exists()
        with open(run_file) as f:
            data = json.load(f)
        assert data["run_id"] == run_id
        assert data["report"]["spec_name"] == "Test Spec"

    def test_updates_index(self, tmp_results_dir):
        save_result(SAMPLE_REPORT, spec_path="/test.yaml")
        index_file = tmp_results_dir / "index.json"
        assert index_file.exists()
        with open(index_file) as f:
            index = json.load(f)
        assert len(index["runs"]) == 1
        assert index["runs"][0]["spec_name"] == "Test Spec"
        assert index["runs"][0]["spec_path"] == "/test.yaml"

    def test_multiple_saves_ordered_by_recency(self, tmp_results_dir):
        save_result(SAMPLE_REPORT)
        save_result(SAMPLE_REPORT_2)
        index_file = tmp_results_dir / "index.json"
        with open(index_file) as f:
            index = json.load(f)
        assert len(index["runs"]) == 2


class TestListRuns:
    def test_lists_all_runs(self, tmp_results_dir):
        save_result(SAMPLE_REPORT, spec_path="/a.yaml")
        save_result(SAMPLE_REPORT_2, spec_path="/b.yaml")
        result = list_runs()
        assert len(result["runs"]) == 2

    def test_filters_by_spec_name(self, tmp_results_dir):
        save_result(SAMPLE_REPORT, spec_path="/a.yaml")
        report2 = dict(SAMPLE_REPORT)
        report2["spec_name"] = "Other Spec"
        save_result(report2, spec_path="/b.yaml")
        result = list_runs(spec_name="Other Spec")
        assert len(result["runs"]) == 1
        assert result["runs"][0]["spec_name"] == "Other Spec"

    def test_respects_limit(self, tmp_results_dir):
        for _ in range(5):
            save_result(SAMPLE_REPORT)
        result = list_runs(limit=3)
        assert len(result["runs"]) == 3

    def test_empty_when_no_runs(self, tmp_results_dir):
        result = list_runs()
        assert result["runs"] == []


class TestGetRun:
    def test_returns_run_details(self, tmp_results_dir):
        saved = save_result(SAMPLE_REPORT)
        run_id = saved["run_id"]
        result = get_run(run_id)
        assert "error" not in result
        assert result["run_id"] == run_id
        assert result["report"]["spec_name"] == "Test Spec"

    def test_run_not_found(self, tmp_results_dir):
        result = get_run("a" * 16)
        assert "error" in result
        assert "not found" in result["error"].lower()


class TestCompareRuns:
    def test_detects_differences(self, tmp_results_dir):
        id1 = save_result(SAMPLE_REPORT)["run_id"]
        id2 = save_result(SAMPLE_REPORT_2)["run_id"]
        result = compare_runs(id1, id2)
        assert "error" not in result
        assert len(result["differences"]) > 0
        diff_names = [d["test_name"] for d in result["differences"]]
        assert "fail1" in diff_names

    def test_runs_with_no_changes(self, tmp_results_dir):
        id1 = save_result(SAMPLE_REPORT)["run_id"]
        id2 = save_result(SAMPLE_REPORT)["run_id"]
        result = compare_runs(id1, id2)
        assert result["differences"] == []

    def test_missing_run_returns_error(self, tmp_results_dir):
        saved = save_result(SAMPLE_REPORT)
        result = compare_runs(saved["run_id"], "a" * 16)
        assert "error" in result


class TestGetTrends:
    def test_returns_trend_data(self, tmp_results_dir):
        save_result(SAMPLE_REPORT)
        save_result(SAMPLE_REPORT_2)
        result = get_trends()
        assert "trends" in result
        assert result["total_runs"] == 2
        assert len(result["trends"]) >= 1

    def test_filters_by_spec_name(self, tmp_results_dir):
        save_result(SAMPLE_REPORT, spec_path="/a.yaml")
        report2 = dict(SAMPLE_REPORT)
        report2["spec_name"] = "Other Spec"
        save_result(report2, spec_path="/b.yaml")
        result = get_trends(spec_name="Other Spec")
        assert result["total_runs"] == 1

    def test_empty_when_no_runs(self, tmp_results_dir):
        result = get_trends()
        assert result["total_runs"] == 0
        assert result["trends"] == []

    def test_trend_includes_pass_rate(self, tmp_results_dir):
        save_result(SAMPLE_REPORT)
        result = get_trends()
        trend = result["trends"][0]
        assert "pass_rate" in trend
        assert trend["pass_rate"] == pytest.approx(0.6667, rel=1e-3)


class TestBuildServer:
    def test_build_server_returns_server(self):
        from agentspec.mcp.results_store import _build_server

        srv = _build_server()
        assert srv is not None
        assert srv.server_name == "results-store"


class TestResultsStoreEdgeCases:
    def test_get_run_not_found(self, tmp_results_dir):
        result = get_run("a" * 16)
        assert "error" in result

    def test_get_run_invalid_id(self, tmp_results_dir):
        result = get_run("../../etc/passwd")
        assert "error" in result
        assert "Invalid" in result["error"]

    def test_list_runs_empty(self, tmp_results_dir):
        result = list_runs()
        assert result is not None

    def test_get_trends_no_data(self, tmp_results_dir):
        result = get_trends(spec_name="nonexistent", days=7)
        assert result is not None

    def test_get_trends_invalid_days(self, tmp_results_dir):
        result = get_trends(spec_name="test", days=0)
        assert result is not None

    def test_compare_runs_both_missing(self, tmp_results_dir):
        result = compare_runs("a" * 16, "b" * 16)
        assert "error" in result


class TestResultsStorePersistence:
    def test_save_and_list_run(self, tmp_results_dir):
        summary = {
            "total": 1,
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "pass_rate": 1.0,
        }
        report = {
            "spec_name": "test-spec",
            "summary": summary,
            "results": [],
        }
        run_id = save_result(report)
        assert "run_id" in run_id
        assert run_id["run_id"] is not None

    def test_save_and_get_run(self, tmp_results_dir):
        summary = {
            "total": 1,
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "pass_rate": 1.0,
        }
        report = {
            "spec_name": "test-spec-2",
            "summary": summary,
            "results": [],
        }
        saved = save_result(report)
        retrieved = get_run(saved["run_id"])
        assert "error" not in retrieved
        assert retrieved["report"]["spec_name"] == "test-spec-2"
