from __future__ import annotations

from unittest.mock import patch

import pytest

from agentspec.results_backend import JsonFileBackend, SqliteBackend

SAMPLE_REPORT = {
    "spec_name": "Test Spec",
    "summary": {"total": 3, "passed": 2, "failed": 1, "errors": 0, "pass_rate": 0.6667},
    "results": [
        {
            "name": "pass1",
            "passed": True,
            "error": None,
            "latency_seconds": 0.5,
            "assertion_results": [],
        },  # noqa: E501
        {
            "name": "pass2",
            "passed": True,
            "error": None,
            "latency_seconds": 1.0,
            "assertion_results": [],
        },  # noqa: E501
        {
            "name": "fail1",
            "passed": False,
            "error": None,
            "latency_seconds": 2.0,
            "assertion_results": [],
        },  # noqa: E501
    ],
}

SAMPLE_REPORT_2 = {
    "spec_name": "Test Spec",
    "summary": {"total": 3, "passed": 3, "failed": 0, "errors": 0, "pass_rate": 1.0},
    "results": [
        {
            "name": "pass1",
            "passed": True,
            "error": None,
            "latency_seconds": 0.4,
            "assertion_results": [],
        },  # noqa: E501
        {
            "name": "pass2",
            "passed": True,
            "error": None,
            "latency_seconds": 0.8,
            "assertion_results": [],
        },  # noqa: E501
        {
            "name": "fail1",
            "passed": True,
            "error": None,
            "latency_seconds": 1.5,
            "assertion_results": [],
        },  # noqa: E501
    ],
}


class TestJsonFileBackend:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        test_dir = tmp_path / ".agentspec" / "results"
        test_dir.mkdir(parents=True)
        with patch("agentspec.results_backend.RESULTS_DIR", test_dir):
            self.backend = JsonFileBackend()
            yield

    def test_save_and_get_run(self):
        saved = self.backend.save_result(SAMPLE_REPORT)
        assert "run_id" in saved
        result = self.backend.get_run(saved["run_id"])
        assert "error" not in result
        assert result["report"]["spec_name"] == "Test Spec"

    def test_list_runs(self):
        self.backend.save_result(SAMPLE_REPORT)
        self.backend.save_result(SAMPLE_REPORT_2)
        runs = self.backend.list_runs()
        assert len(runs["runs"]) == 2

    def test_compare_runs(self):
        id1 = self.backend.save_result(SAMPLE_REPORT)["run_id"]
        id2 = self.backend.save_result(SAMPLE_REPORT_2)["run_id"]
        result = self.backend.compare_runs(id1, id2)
        assert "error" not in result
        assert len(result["differences"]) > 0

    def test_get_trends(self):
        self.backend.save_result(SAMPLE_REPORT)
        result = self.backend.get_trends()
        assert "trends" in result
        assert result["total_runs"] == 1

    def test_prune_runs(self):
        for _ in range(5):
            self.backend.save_result(SAMPLE_REPORT)
        result = self.backend.prune_runs(keep=2)
        assert result["removed"] == 3
        assert result["remaining"] == 2

    def test_run_not_found(self):
        result = self.backend.get_run("nonexistent")
        assert "error" in result

    def test_list_runs_empty(self):
        result = self.backend.list_runs()
        assert result["runs"] == []

    def test_filter_by_spec_name(self):
        self.backend.save_result(SAMPLE_REPORT)
        report2 = dict(SAMPLE_REPORT)
        report2["spec_name"] = "Other"
        self.backend.save_result(report2)
        result = self.backend.list_runs(spec_name="Other")
        assert len(result["runs"]) == 1
        assert result["runs"][0]["spec_name"] == "Other"


class TestSqliteBackend:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        test_dir = tmp_path / ".agentspec" / "results"
        test_dir.mkdir(parents=True)
        with patch("agentspec.results_backend.RESULTS_DIR", test_dir):
            self.backend = SqliteBackend()
            yield

    def test_save_and_get_run(self):
        saved = self.backend.save_result(SAMPLE_REPORT)
        assert "run_id" in saved
        result = self.backend.get_run(saved["run_id"])
        assert "error" not in result
        assert result["report"]["spec_name"] == "Test Spec"

    def test_list_runs(self):
        self.backend.save_result(SAMPLE_REPORT)
        self.backend.save_result(SAMPLE_REPORT_2)
        runs = self.backend.list_runs()
        assert len(runs["runs"]) == 2

    def test_compare_runs(self):
        id1 = self.backend.save_result(SAMPLE_REPORT)["run_id"]
        id2 = self.backend.save_result(SAMPLE_REPORT_2)["run_id"]
        result = self.backend.compare_runs(id1, id2)
        assert "error" not in result
        assert len(result["differences"]) > 0

    def test_get_trends(self):
        self.backend.save_result(SAMPLE_REPORT)
        result = self.backend.get_trends()
        assert "trends" in result
        assert result["total_runs"] == 1

    def test_prune_runs(self):
        for _ in range(5):
            self.backend.save_result(SAMPLE_REPORT)
        result = self.backend.prune_runs(keep=2)
        assert result["removed"] == 3
        assert result["remaining"] == 2

    def test_run_not_found(self):
        result = self.backend.get_run("nonexistent")
        assert "error" in result

    def test_list_runs_empty(self):
        result = self.backend.list_runs()
        assert result["runs"] == []

    def test_filter_by_spec_name(self):
        self.backend.save_result(SAMPLE_REPORT)
        report2 = dict(SAMPLE_REPORT)
        report2["spec_name"] = "Other"
        self.backend.save_result(report2)
        result = self.backend.list_runs(spec_name="Other")
        assert len(result["runs"]) == 1
        assert result["runs"][0]["spec_name"] == "Other"

    def test_save_with_spec_path(self):
        saved = self.backend.save_result(SAMPLE_REPORT, spec_path="/test.yaml")
        result = self.backend.get_run(saved["run_id"])
        assert "error" not in result

    def test_compare_missing_runs(self):
        result = self.backend.compare_runs("id1", "id2")
        assert "error" in result

    def test_prune_with_spec_filter(self):
        for _ in range(5):
            self.backend.save_result(SAMPLE_REPORT)
        report2 = dict(SAMPLE_REPORT)
        report2["spec_name"] = "Other"
        self.backend.save_result(report2)
        result = self.backend.prune_runs(keep=2, spec_name="Test Spec")
        assert result["removed"] == 3
        assert result["remaining"] == 3

    def test_get_trends_with_filter(self):
        self.backend.save_result(SAMPLE_REPORT)
        result = self.backend.get_trends(spec_name="Nonexistent")
        assert result["total_runs"] == 0
        assert result["trends"] == []

    def test_list_runs_limit(self):
        for _ in range(5):
            self.backend.save_result(SAMPLE_REPORT)
        result = self.backend.list_runs(limit=3)
        assert len(result["runs"]) == 3
