from __future__ import annotations

from unittest.mock import patch

import pytest

from agentspec.mcp.results_store import prune_runs, save_result

SAMPLE_REPORT = {
    "spec_name": "Test Spec",
    "summary": {"total": 3, "passed": 2, "failed": 1, "errors": 0, "pass_rate": 0.6667},
    "results": [
        {"name": "t1", "passed": True, "error": None, "latency_seconds": 0.5, "assertion_results": []},  # noqa: E501
        {"name": "t2", "passed": True, "error": None, "latency_seconds": 1.0, "assertion_results": []},  # noqa: E501
        {"name": "t3", "passed": False, "error": None, "latency_seconds": 2.0, "assertion_results": []},  # noqa: E501
    ],
}


@pytest.fixture(autouse=True)
def tmp_results_dir(tmp_path):
    test_dir = tmp_path / ".agentspec" / "results"
    test_dir.mkdir(parents=True)
    with patch("agentspec.mcp.results_store.RESULTS_DIR", test_dir):
        with patch("agentspec.mcp.results_store.INDEX_FILE", test_dir / "index.json"):
            yield test_dir


class TestPruneRuns:
    def test_prune_removes_old_runs(self, tmp_results_dir):
        for _ in range(10):
            save_result(SAMPLE_REPORT)
        result = prune_runs(keep=3)
        assert result["removed"] == 7
        assert result["remaining"] == 3

    def test_prune_nothing_when_under_limit(self, tmp_results_dir):
        for _ in range(3):
            save_result(SAMPLE_REPORT)
        result = prune_runs(keep=10)
        assert result["removed"] == 0
        assert result["remaining"] == 3

    def test_prune_removes_run_files(self, tmp_results_dir):
        run_ids = []
        for _ in range(5):
            r = save_result(SAMPLE_REPORT)
            run_ids.append(r["run_id"])
        prune_runs(keep=2)
        for rid in run_ids[:3]:
            run_file = tmp_results_dir / f"{rid}.json"
            assert not run_file.exists(), f"Run file {rid}.json should have been removed"  # noqa: E501
        for rid in run_ids[3:]:
            run_file = tmp_results_dir / f"{rid}.json"
            assert run_file.exists(), f"Run file {rid}.json should still exist"

    def test_prune_with_spec_filter(self, tmp_results_dir):
        for _ in range(5):
            save_result(SAMPLE_REPORT)
        report2 = dict(SAMPLE_REPORT)
        report2["spec_name"] = "Other Spec"
        save_result(report2)
        result = prune_runs(keep=2, spec_name="Test Spec")
        assert result["removed"] == 3  # 5 - 2 = 3 removed from Test Spec
        assert result["remaining"] == 3  # 2 kept + 1 Other Spec

    def test_prune_empty(self, tmp_results_dir):
        result = prune_runs(keep=10)
        assert result["removed"] == 0
        assert result["remaining"] == 0
