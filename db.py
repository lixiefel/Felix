"""
db.py — SQLite persistence for MarginLab submissions
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "submissions.db"


def _conn():
    return sqlite3.connect(str(DB_PATH))


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT NOT NULL,
                email       TEXT,
                mode        TEXT,
                currency    TEXT,
                item_count  INTEGER,
                inputs_json TEXT,
                monthly_lift REAL,
                lift_pct    REAL,
                confidence  TEXT,
                best_item   TEXT,
                hard_fails  INTEGER,
                excel_path  TEXT
            )
        """)


def save_submission(*, email, mode, currency, items, audit):
    init_db()
    inputs = {
        "settings": {"currency": currency},
        "items": [
            {"name": it.name, "category": it.category, "role": it.role,
             "cost": it.cost, "price": it.price, "monthly_units": it.monthly_units}
            for it in items
        ]
    }
    with _conn() as con:
        con.execute("""
            INSERT INTO submissions
              (created_at, email, mode, currency, item_count, inputs_json,
               monthly_lift, lift_pct, confidence, best_item, hard_fails, excel_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            email or "",
            mode,
            currency,
            len(items),
            json.dumps(inputs),
            audit.monthly_lift,
            audit.lift_pct,
            audit.confidence,
            audit.best_item,
            audit.qa_hard_fails,
            audit.excel_path,
        ))


def get_all_submissions(limit=200):
    init_db()
    with _conn() as con:
        rows = con.execute("""
            SELECT id, created_at, email, mode, currency, item_count,
                   monthly_lift, lift_pct, confidence, best_item, hard_fails, excel_path
            FROM submissions ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
    return rows


def get_submission_inputs(submission_id):
    init_db()
    with _conn() as con:
        row = con.execute(
            "SELECT inputs_json, excel_path FROM submissions WHERE id = ?",
            (submission_id,)
        ).fetchone()
    return row
