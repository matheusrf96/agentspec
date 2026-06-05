from __future__ import annotations

import json
import sqlite3
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path.home() / ".agentspec" / "results"


class ResultsBackend(ABC):
    @abstractmethod
    def save_result(self, report: dict, spec_path: str | None = None) -> dict:
        ...

    @abstractmethod
    def list_runs(
        self, limit: int | None = None, spec_name: str | None = None
    ) -> dict:
        ...

    @abstractmethod
    def get_run(self, run_id: str) -> dict:
        ...

    @abstractmethod
    def compare_runs(self, id1: str, id2: str) -> dict:
        ...

    @abstractmethod
    def get_trends(
        self, spec_name: str | None = None, days: int | None = None
    ) -> dict:
        ...

    @abstractmethod
    def prune_runs(self, keep: int = 50, spec_name: str | None = None) -> dict:
        ...


class JsonFileBackend(ResultsBackend):
    """Store results as individual JSON files with an index."""

    def __init__(self):
        self._results_dir = RESULTS_DIR
        self._index_file = self._results_dir / "index.json"

    def _ensure_dir(self) -> None:
        self._results_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> dict:
        self._ensure_dir()
        if self._index_file.exists():
            try:
                with open(self._index_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"runs": []}

    def _save_index(self, index: dict) -> None:
        self._ensure_dir()
        with open(self._index_file, "w") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def _iso_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_result(self, report: dict, spec_path: str | None = None) -> dict:
        run_id = uuid.uuid4().hex[:12]
        timestamp = self._iso_now()
        summary = report.get("summary", {})
        entry = {
            "run_id": run_id,
            "spec_name": report.get("spec_name", "unknown"),
            "spec_path": spec_path,
            "timestamp": timestamp,
            "pass_rate": summary.get("pass_rate", 0.0),
            "total": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "errors": summary.get("errors", 0),
        }
        index = self._load_index()
        index["runs"].insert(0, entry)
        self._save_index(index)

        run_file = self._results_dir / f"{run_id}.json"
        with open(run_file, "w") as f:
            payload = {"run_id": run_id, "timestamp": timestamp, "report": report}
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

        return {"run_id": run_id}

    def list_runs(
        self, limit: int | None = None, spec_name: str | None = None
    ) -> dict:
        index = self._load_index()
        runs = index.get("runs", [])
        if spec_name:
            runs = [r for r in runs if r.get("spec_name") == spec_name]
        if limit is not None and limit > 0:
            runs = runs[:limit]
        return {"runs": runs}

    def get_run(self, run_id: str) -> dict:
        run_file = self._results_dir / f"{run_id}.json"
        if not run_file.exists():
            return {"error": f"Run not found: {run_id}"}
        try:
            with open(run_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            return {"error": f"Failed to read run: {exc}"}

    def compare_runs(self, id1: str, id2: str) -> dict:
        run1 = self.get_run(id1)
        run2 = self.get_run(id2)
        if "error" in run1:
            return {"error": run1["error"]}
        if "error" in run2:
            return {"error": run2["error"]}

        report1 = run1.get("report", {})
        report2 = run2.get("report", {})

        results1 = {r["name"]: r for r in report1.get("results", [])}
        results2 = {r["name"]: r for r in report2.get("results", [])}

        all_names = set(results1) | set(results2)
        differences = []

        def _status(r: dict | None) -> str:
            if r is None:
                return "missing"
            if r.get("error"):
                return "error"
            return "pass" if r.get("passed") else "fail"

        for name in sorted(all_names):
            r1 = results1.get(name)
            r2 = results2.get(name)
            status_before = _status(r1)
            status_after = _status(r2)
            if status_before != status_after:
                differences.append(
                    {
                        "test_name": name,
                        "status_before": status_before,
                        "status_after": status_after,
                    }
                )

        return {
            "run1": {"run_id": id1, "timestamp": run1.get("timestamp")},
            "run2": {"run_id": id2, "timestamp": run2.get("timestamp")},
            "differences": differences,
            "summary1": report1.get("summary"),
            "summary2": report2.get("summary"),
        }

    def get_trends(
        self, spec_name: str | None = None, days: int | None = None
    ) -> dict:
        from datetime import timedelta

        index = self._load_index()
        runs = index.get("runs", [])

        if spec_name:
            runs = [r for r in runs if r.get("spec_name") == spec_name]

        if days is not None and days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            runs = (
                [r for r in runs if _parse_iso(r.get("timestamp", "")) >= cutoff]
                if runs
                else []
            )

        periods: dict[str, dict] = {}
        for run in runs:
            ts = run.get("timestamp", "")
            day = ts[:10] if ts else "unknown"
            if day not in periods:
                periods[day] = {
                    "date": day,
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "errors": 0,
                }
            periods[day]["total"] += run.get("total", 0)
            periods[day]["passed"] += run.get("passed", 0)
            periods[day]["failed"] += run.get("failed", 0)
            periods[day]["errors"] += run.get("errors", 0)

        trend_data = []
        for day in sorted(periods):
            p = periods[day]
            pass_rate = p["passed"] / p["total"] if p["total"] > 0 else 0.0
            trend_data.append(
                {
                    "date": day,
                    "total": p["total"],
                    "passed": p["passed"],
                    "failed": p["failed"],
                    "errors": p["errors"],
                    "pass_rate": round(pass_rate, 4),
                }
            )

        return {"trends": trend_data, "total_runs": len(runs)}

    def prune_runs(self, keep: int = 50, spec_name: str | None = None) -> dict:
        index = self._load_index()
        runs = index.get("runs", [])

        if spec_name:
            filtered = [r for r in runs if r.get("spec_name") == spec_name]
            others = [r for r in runs if r.get("spec_name") != spec_name]
        else:
            filtered = list(runs)
            others = []

        if len(filtered) <= keep:
            return {"removed": 0, "remaining": len(runs)}

        to_keep = filtered[:keep]
        to_remove = filtered[keep:]

        removed_ids = {r["run_id"] for r in to_remove}
        for rid in removed_ids:
            run_file = RESULTS_DIR / f"{rid}.json"
            if run_file.exists():
                run_file.unlink()

        index["runs"] = others + to_keep
        self._save_index(index)

        return {"removed": len(to_remove), "remaining": len(index["runs"])}


class SqliteBackend(ResultsBackend):
    """Store results in a SQLite database."""

    def __init__(self):
        self._results_dir = RESULTS_DIR
        self._init_db()

    def _conn(self):
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._results_dir / "results.db"))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    spec_name TEXT NOT NULL,
                    spec_path TEXT,
                    timestamp TEXT NOT NULL,
                    pass_rate REAL NOT NULL DEFAULT 0.0,
                    total INTEGER NOT NULL DEFAULT 0,
                    passed INTEGER NOT NULL DEFAULT 0,
                    failed INTEGER NOT NULL DEFAULT 0,
                    errors INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS reports (
                    run_id TEXT PRIMARY KEY,
                    report TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                CREATE INDEX IF NOT EXISTS idx_runs_spec_name ON runs(spec_name);
                CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs(timestamp);
            """)

    def _iso_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_result(self, report: dict, spec_path: str | None = None) -> dict:
        run_id = uuid.uuid4().hex[:12]
        timestamp = self._iso_now()
        summary = report.get("summary", {})

        with self._conn() as conn:
            conn.execute(
                """INSERT INTO runs (run_id, spec_name, spec_path, timestamp,
                   pass_rate, total, passed, failed, errors)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    report.get("spec_name", "unknown"),
                    spec_path,
                    timestamp,
                    summary.get("pass_rate", 0.0),
                    summary.get("total", 0),
                    summary.get("passed", 0),
                    summary.get("failed", 0),
                    summary.get("errors", 0),
                ),
            )
            conn.execute(
                "INSERT INTO reports (run_id, report) VALUES (?, ?)",
                (run_id, json.dumps(report, default=str)),
            )

        return {"run_id": run_id}

    def list_runs(
        self, limit: int | None = None, spec_name: str | None = None
    ) -> dict:
        with self._conn() as conn:
            query = (
                "SELECT run_id, spec_name, spec_path, timestamp,"
                " pass_rate, total, passed, failed, errors FROM runs"
            )
            params: list = []
            if spec_name:
                query += " WHERE spec_name = ?"
                params.append(spec_name)
            query += " ORDER BY timestamp DESC"
            if limit is not None and limit > 0:
                query += " LIMIT ?"
                params.append(limit)

            rows = conn.execute(query, params).fetchall()
            runs = [dict(r) for r in rows]
        return {"runs": runs}

    def get_run(self, run_id: str) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                (
                    "SELECT r.run_id, ru.timestamp, r.report"
                    " FROM reports r JOIN runs ru ON r.run_id = ru.run_id"
                    " WHERE r.run_id = ?"
                ),
                (run_id,),
            ).fetchone()
        if row is None:
            return {"error": f"Run not found: {run_id}"}
        data = dict(row)
        data["report"] = json.loads(data["report"])
        return data

    def compare_runs(self, id1: str, id2: str) -> dict:
        run1 = self.get_run(id1)
        run2 = self.get_run(id2)
        if "error" in run1:
            return {"error": run1["error"]}
        if "error" in run2:
            return {"error": run2["error"]}

        report1 = run1.get("report", {})
        report2 = run2.get("report", {})

        results1 = {r["name"]: r for r in report1.get("results", [])}
        results2 = {r["name"]: r for r in report2.get("results", [])}

        all_names = set(results1) | set(results2)
        differences = []

        def _status(r: dict | None) -> str:
            if r is None:
                return "missing"
            if r.get("error"):
                return "error"
            return "pass" if r.get("passed") else "fail"

        for name in sorted(all_names):
            r1 = results1.get(name)
            r2 = results2.get(name)
            status_before = _status(r1)
            status_after = _status(r2)
            if status_before != status_after:
                differences.append(
                    {
                        "test_name": name,
                        "status_before": status_before,
                        "status_after": status_after,
                    }
                )

        # Get run metadata
        with self._conn() as conn:
            row1 = conn.execute(
                "SELECT timestamp FROM runs WHERE run_id = ?", (id1,)
            ).fetchone()
            row2 = conn.execute(
                "SELECT timestamp FROM runs WHERE run_id = ?", (id2,)
            ).fetchone()

        return {
            "run1": {"run_id": id1, "timestamp": row1["timestamp"] if row1 else None},
            "run2": {"run_id": id2, "timestamp": row2["timestamp"] if row2 else None},
            "differences": differences,
            "summary1": report1.get("summary"),
            "summary2": report2.get("summary"),
        }

    def get_trends(
        self, spec_name: str | None = None, days: int | None = None
    ) -> dict:
        from datetime import timedelta

        with self._conn() as conn:
            query = (
                "SELECT timestamp, total, passed, failed, errors FROM runs"
            )
            params: list = []
            conditions = []
            if spec_name:
                conditions.append("spec_name = ?")
                params.append(spec_name)
            if days is not None and days > 0:
                cutoff = datetime.now(timezone.utc) - timedelta(days=days)
                conditions.append("timestamp >= ?")
                params.append(cutoff.isoformat())
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            rows = conn.execute(query, params).fetchall()

        periods: dict[str, dict] = {}
        for row in rows:
            ts = row["timestamp"]
            day = ts[:10] if ts else "unknown"
            if day not in periods:
                periods[day] = {
                    "date": day,
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "errors": 0,
                }
            periods[day]["total"] += row["total"]
            periods[day]["passed"] += row["passed"]
            periods[day]["failed"] += row["failed"]
            periods[day]["errors"] += row["errors"]

        trend_data = []
        for day in sorted(periods):
            p = periods[day]
            pass_rate = p["passed"] / p["total"] if p["total"] > 0 else 0.0
            trend_data.append(
                {
                    "date": day,
                    "total": p["total"],
                    "passed": p["passed"],
                    "failed": p["failed"],
                    "errors": p["errors"],
                    "pass_rate": round(pass_rate, 4),
                }
            )

        return {"trends": trend_data, "total_runs": len(rows)}

    def prune_runs(self, keep: int = 50, spec_name: str | None = None) -> dict:
        with self._conn() as conn:
            if spec_name:
                all_runs = conn.execute(
                    (
                        "SELECT run_id FROM runs"
                        " WHERE spec_name = ? ORDER BY timestamp DESC"
                    ),
                    (spec_name,),
                ).fetchall()
                other_count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM runs WHERE spec_name != ?",
                    (spec_name,),
                ).fetchone()["cnt"]
            else:
                all_runs = conn.execute(
                    "SELECT run_id FROM runs ORDER BY timestamp DESC"
                ).fetchall()
                other_count = 0

            if len(all_runs) <= keep:
                return {"removed": 0, "remaining": len(all_runs) + other_count}

            to_remove = all_runs[keep:]
            removed_ids = [r["run_id"] for r in to_remove]

            placeholders = ",".join("?" for _ in removed_ids)
            conn.execute(
                f"DELETE FROM reports WHERE run_id IN ({placeholders})",
                removed_ids,
            )
            conn.execute(
                f"DELETE FROM runs WHERE run_id IN ({placeholders})",
                removed_ids,
            )

            remaining = conn.execute(
                "SELECT COUNT(*) as cnt FROM runs"
            ).fetchone()["cnt"]

        return {"removed": len(removed_ids), "remaining": remaining}


def _parse_iso(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc)
