"""
Decision Brain memory storage (SQLite).

Stores:
- analyses: per-page analysis snapshots
- feedback: user feedback on analyses
- weights: calibration weights per (page_type, issue_id)
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "brain_memory.db"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they do not exist."""
    conn = _get_conn()
    try:
        cur = conn.cursor()

        # Analyses table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                url TEXT NOT NULL,
                domain TEXT NOT NULL,
                page_type TEXT NOT NULL,
                ruleset_version TEXT NOT NULL,
                decision_probability REAL,
                top_issues_json TEXT NOT NULL,
                screenshots_json TEXT,
                report_hash TEXT
            )
            """
        )

        # Feedback table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                label TEXT NOT NULL,
                notes TEXT,
                wrong_issues_json TEXT,
                FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
            )
            """
        )

        # Weights table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                updated_at TEXT NOT NULL,
                page_type TEXT NOT NULL,
                issue_id TEXT NOT NULL,
                weight REAL NOT NULL,
                evidence_json TEXT NOT NULL,
                UNIQUE(page_type, issue_id)
            )
            """
        )

        conn.commit()
    finally:
        conn.close()


def _get_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.netloc or url
    except Exception:
        return url


def log_analysis(
    *,
    url: str,
    page_type: str,
    ruleset_version: str,
    top_issues: List[Dict[str, Any]],
    screenshots: Optional[Dict[str, Any]] = None,
    decision_probability: Optional[float] = None,
    report_hash: Optional[str] = None,
) -> int:
    """
    Insert an analysis row and return its ID.

    top_issues is a list of dicts, typically with at least {id, severity}.
    screenshots is a dict like {"desktop_atf": url, "mobile_atf": url}.
    """
    init_db()
    conn = _get_conn()
    try:
        cur = conn.cursor()
        created_at = _utc_iso()
        domain = _get_domain(url)

        cur.execute(
            """
            INSERT INTO analyses (
                created_at,
                url,
                domain,
                page_type,
                ruleset_version,
                decision_probability,
                top_issues_json,
                screenshots_json,
                report_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                url,
                domain,
                page_type,
                ruleset_version,
                decision_probability,
                json.dumps(top_issues or [], ensure_ascii=False),
                json.dumps(screenshots or {}, ensure_ascii=False),
                report_hash,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def insert_feedback(
    *,
    analysis_id: int,
    label: str,
    notes: Optional[str] = None,
    wrong_issues: Optional[List[str]] = None,
) -> int:
    """Insert feedback for a given analysis and return feedback ID."""
    init_db()
    conn = _get_conn()
    try:
        cur = conn.cursor()
        created_at = _utc_iso()
        cur.execute(
            """
            INSERT INTO feedback (
                analysis_id,
                created_at,
                label,
                notes,
                wrong_issues_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                created_at,
                label,
                notes,
                json.dumps(wrong_issues or [], ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def analysis_exists(analysis_id: int) -> bool:
    """Check if an analysis with the given ID exists."""
    init_db()
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM analyses WHERE id = ? LIMIT 1", (analysis_id,))
        row = cur.fetchone()
        return row is not None
    finally:
        conn.close()

def get_issue_weights_for_page_type(page_type: str) -> Dict[str, float]:
    """Return a mapping of issue_id -> weight for a given page_type."""
    init_db()
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT issue_id, weight
            FROM weights
            WHERE page_type = ?
            """,
            (page_type,),
        )
        rows = cur.fetchall()
        return {str(row["issue_id"]): float(row["weight"]) for row in rows}
    finally:
        conn.close()


def calibrate_weights() -> Dict[str, Any]:
    """
    Recompute weights for all (page_type, issue_id) pairs based on analyses + feedback.

    Returns a summary dict with counts.
    """
    init_db()
    conn = _get_conn()
    try:
        cur = conn.cursor()

        # Load all analyses
        cur.execute("SELECT id, page_type, top_issues_json FROM analyses")
        analyses_rows = cur.fetchall()

        # Build suggested counts
        stats: Dict[Tuple[str, str], Dict[str, float]] = {}
        for row in analyses_rows:
            page_type = str(row["page_type"])
            try:
                top_issues = json.loads(row["top_issues_json"] or "[]")
            except json.JSONDecodeError:
                top_issues = []
            issue_ids = [
                str(issue.get("id"))
                for issue in top_issues
                if isinstance(issue, dict) and issue.get("id")
            ]
            for issue_id in issue_ids:
                key = (page_type, issue_id)
                if key not in stats:
                    stats[key] = {
                        "suggested": 0.0,
                        "accurate": 0.0,
                        "wrong": 0.0,
                    }
                stats[key]["suggested"] += 1.0

        # Load feedback joined with analyses
        cur.execute(
            """
            SELECT
                f.label,
                f.wrong_issues_json,
                a.page_type,
                a.top_issues_json
            FROM feedback f
            JOIN analyses a ON f.analysis_id = a.id
            """
        )
        fb_rows = cur.fetchall()

        for row in fb_rows:
            label = (row["label"] or "").lower()
            page_type = str(row["page_type"])
            try:
                top_issues = json.loads(row["top_issues_json"] or "[]")
            except json.JSONDecodeError:
                top_issues = []
            issue_ids = [
                str(issue.get("id"))
                for issue in top_issues
                if isinstance(issue, dict) and issue.get("id")
            ]

            try:
                wrong_list = json.loads(row["wrong_issues_json"] or "[]")
            except json.JSONDecodeError:
                wrong_list = []
            wrong_set = {str(i) for i in wrong_list if i}

            # Accurate / partial feedback applies to all issues in the analysis
            if label in {"accurate", "partial"}:
                delta = 1.0 if label == "accurate" else 0.5
                for issue_id in issue_ids:
                    key = (page_type, issue_id)
                    if key not in stats:
                        stats[key] = {
                            "suggested": 0.0,
                            "accurate": 0.0,
                            "wrong": 0.0,
                        }
                    stats[key]["accurate"] += delta

            # Wrong feedback
            if wrong_set:
                # Explicit wrong issues
                for issue_id in wrong_set:
                    key = (page_type, issue_id)
                    if key not in stats:
                        stats[key] = {
                            "suggested": 0.0,
                            "accurate": 0.0,
                            "wrong": 0.0,
                        }
                    stats[key]["wrong"] += 1.0
            elif label == "wrong":
                # Entire analysis considered wrong
                for issue_id in issue_ids:
                    key = (page_type, issue_id)
                    if key not in stats:
                        stats[key] = {
                            "suggested": 0.0,
                            "accurate": 0.0,
                            "wrong": 0.0,
                        }
                    stats[key]["wrong"] += 1.0

        # Compute weights and upsert
        updated = 0
        now = _utc_iso()
        for (page_type, issue_id), s in stats.items():
            suggested = max(1.0, float(s.get("suggested", 0.0)))
            accurate = float(s.get("accurate", 0.0))
            wrong = float(s.get("wrong", 0.0))

            raw_weight = 1.0 + 0.6 * (accurate - wrong) / suggested
            # Clamp to [0.2, 1.8]
            weight = max(0.2, min(1.8, raw_weight))

            evidence = {
                "suggested_count": suggested,
                "accurate_count": accurate,
                "wrong_count": wrong,
            }

            cur.execute(
                """
                INSERT INTO weights (
                    updated_at,
                    page_type,
                    issue_id,
                    weight,
                    evidence_json
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(page_type, issue_id) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    weight = excluded.weight,
                    evidence_json = excluded.evidence_json
                """,
                (
                    now,
                    page_type,
                    issue_id,
                    weight,
                    json.dumps(evidence, ensure_ascii=False),
                ),
            )
            updated += 1

        conn.commit()

        return {
            "status": "ok",
            "weights_updated": updated,
            "distinct_pairs": len(stats),
        }
    finally:
        conn.close()


