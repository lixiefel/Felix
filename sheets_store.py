"""
sheets_store.py — Google Sheets persistence with SQLite fallback.

If GOOGLE_SHEETS_CREDS_JSON and GOOGLE_SHEETS_ID are set in Streamlit secrets:
  - Submissions are appended as rows in the configured sheet
  - get_all_submissions() reads from the sheet
Otherwise:
  - Falls back to the SQLite-based db.py (which wipes on each Streamlit redeploy)

Sheet schema (row 1 is header):
  timestamp | email | cafe_name | mode | currency | item_count |
  monthly_lift | lift_pct | confidence | best_item | hard_fails |
  newsletter_opt_in | followup_1_sent | followup_2_sent | raw_inputs_json |
  excel_path
"""

import os
import json
from datetime import datetime
from pathlib import Path

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

# Fall back to original SQLite layer
from db import (
    init_db as _sqlite_init,
    save_submission as _sqlite_save,
    get_all_submissions as _sqlite_get_all,
    get_submission_inputs as _sqlite_get_inputs,
)


SHEET_HEADERS = [
    "timestamp", "email", "cafe_name", "mode", "currency", "item_count",
    "monthly_lift", "lift_pct", "confidence", "best_item", "hard_fails",
    "newsletter_opt_in", "followup_1_sent", "followup_2_sent",
    "raw_inputs_json", "excel_path",
]


_client = None
_worksheet = None
_init_attempted = False


def _get_secret(name: str):
    if HAS_STREAMLIT:
        try:
            return st.secrets[name]
        except (KeyError, FileNotFoundError, Exception):
            pass
    return os.environ.get(name)


def _init_sheets() -> bool:
    """Try to initialize Google Sheets. Returns True on success."""
    global _client, _worksheet, _init_attempted
    if _init_attempted:
        return _worksheet is not None
    _init_attempted = True

    if not HAS_GSPREAD:
        return False

    creds_raw = _get_secret("GOOGLE_SHEETS_CREDS_JSON")
    sheet_id = _get_secret("GOOGLE_SHEETS_ID")
    if not creds_raw or not sheet_id:
        return False

    try:
        if isinstance(creds_raw, str):
            creds_dict = json.loads(creds_raw)
        else:
            creds_dict = dict(creds_raw)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        _client = gspread.authorize(creds)
        sh = _client.open_by_key(sheet_id)
        _worksheet = sh.sheet1

        # Ensure header row exists
        existing = _worksheet.row_values(1)
        if existing != SHEET_HEADERS:
            if not existing:
                _worksheet.append_row(SHEET_HEADERS)
            # If headers exist but mismatch, leave them — don't risk data loss
        return True
    except Exception:
        _worksheet = None
        return False


def is_sheets_active() -> bool:
    return _init_sheets()


def save_submission(*, email, mode, currency, items, audit,
                    cafe_name="", newsletter_opt_in=False):
    """
    Save a submission. Uses Google Sheets if configured, else SQLite fallback.
    """
    # Always also save to SQLite as a safety net
    try:
        _sqlite_save(email=email, mode=mode, currency=currency,
                     items=items, audit=audit)
    except Exception:
        pass

    if not _init_sheets():
        return

    # Append to sheet
    inputs = {
        "settings": {"currency": currency},
        "items": [
            {"name": it.name, "category": it.category, "role": it.role,
             "cost": it.cost, "price": it.price, "monthly_units": it.monthly_units}
            for it in items
        ]
    }
    row = [
        datetime.utcnow().isoformat(),
        email or "",
        cafe_name or "",
        mode,
        currency,
        len(items),
        round(audit.monthly_lift, 2),
        round(audit.lift_pct, 4),
        audit.confidence or "",
        audit.best_item or "",
        audit.qa_hard_fails,
        "yes" if newsletter_opt_in else "no",
        "",  # followup_1_sent — fills in later when sent
        "",  # followup_2_sent
        json.dumps(inputs),
        audit.excel_path or "",
    ]
    try:
        _worksheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception:
        # If sheets save fails, SQLite already has it
        pass


def get_all_submissions(limit: int = 200):
    """Return list of rows. Same shape as db.get_all_submissions when possible."""
    if _init_sheets():
        try:
            records = _worksheet.get_all_records()
            # Convert to the (id, created_at, email, mode, currency, item_count,
            #                 monthly_lift, lift_pct, confidence, best_item, hard_fails, excel_path)
            # shape that the Admin tab expects.
            out = []
            for i, r in enumerate(records[-limit:][::-1], start=1):
                out.append((
                    i,
                    r.get("timestamp", ""),
                    r.get("email", ""),
                    r.get("mode", ""),
                    r.get("currency", ""),
                    int(r.get("item_count", 0) or 0),
                    float(r.get("monthly_lift", 0) or 0),
                    float(r.get("lift_pct", 0) or 0),
                    r.get("confidence", ""),
                    r.get("best_item", ""),
                    int(r.get("hard_fails", 0) or 0),
                    r.get("excel_path", ""),
                ))
            return out
        except Exception:
            pass
    # Fallback
    return _sqlite_get_all(limit=limit)


def get_submission_inputs(submission_id):
    return _sqlite_get_inputs(submission_id)


def get_pending_followups():
    """
    Return list of dicts with submissions that need a follow-up sent.
    Each dict: {row_index, email, cafe_name, timestamp, followup_1_sent, followup_2_sent}

    Only works with Google Sheets backend.
    """
    if not _init_sheets():
        return []
    try:
        records = _worksheet.get_all_records()
        out = []
        for idx, r in enumerate(records, start=2):  # row 1 = header
            if r.get("mode") != "owner":
                continue  # don't follow up on consultant-mode runs
            email = r.get("email", "")
            if not email or "@" not in email:
                continue
            out.append({
                "row_index": idx,
                "email": email,
                "cafe_name": r.get("cafe_name", ""),
                "timestamp": r.get("timestamp", ""),
                "followup_1_sent": r.get("followup_1_sent", ""),
                "followup_2_sent": r.get("followup_2_sent", ""),
            })
        return out
    except Exception:
        return []


def mark_followup_sent(row_index: int, which: int):
    """Mark followup_1_sent or followup_2_sent for a given sheet row."""
    if not _init_sheets():
        return
    try:
        col = "M" if which == 1 else "N"  # M = col 13, N = col 14
        _worksheet.update_acell(f"{col}{row_index}", datetime.utcnow().isoformat())
    except Exception:
        pass
