"""
rate_limit.py — Per-IP audit rate limiting.

Tracks audit submissions per IP. Persists in SQLite (separate from main submissions DB).
Default: 5 audits per hour per IP. Configurable.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "rate_limit.db"


def _conn():
    con = sqlite3.connect(str(DB_PATH))
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            ip          TEXT NOT NULL,
            ts          TEXT NOT NULL
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_ip_ts ON audit_events(ip, ts)")
    return con


def check_and_record(ip: str, max_per_hour: int = 5) -> tuple[bool, int]:
    """
    Returns (allowed, current_count_in_window).
    If allowed, the new event is recorded.
    If not allowed, no event is recorded.
    """
    if not ip:
        return True, 0  # can't rate-limit unknown IPs; allow

    cutoff = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    with _conn() as con:
        # Cleanup old events to keep DB tiny
        con.execute("DELETE FROM audit_events WHERE ts < ?",
                    ((datetime.utcnow() - timedelta(hours=2)).isoformat(),))
        cur = con.execute(
            "SELECT COUNT(*) FROM audit_events WHERE ip = ? AND ts >= ?",
            (ip, cutoff),
        )
        count = cur.fetchone()[0]

        if count >= max_per_hour:
            return False, count

        # Record this event
        con.execute(
            "INSERT INTO audit_events (ip, ts) VALUES (?, ?)",
            (ip, datetime.utcnow().isoformat()),
        )
        return True, count + 1


def get_ip() -> str:
    """Best-effort IP detection. Streamlit doesn't expose this cleanly."""
    try:
        # Streamlit >= 1.30 has a private API for this
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers() or {}
        # Behind proxy on Streamlit Cloud, real IP is in X-Forwarded-For
        forwarded = headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return headers.get("Host", "unknown")
    except Exception:
        return "unknown"
