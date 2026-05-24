"""
analytics.py — PostHog event tracking with silent no-op fallback.

Reads POSTHOG_KEY (and optional POSTHOG_HOST) from Streamlit secrets or env vars.
If not configured, all track() calls silently do nothing.
"""

import os
import uuid
from datetime import datetime

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    from posthog import Posthog
    HAS_POSTHOG = True
except ImportError:
    HAS_POSTHOG = False


_client = None
_initialized = False


def _get_secret(name: str) -> str | None:
    if HAS_STREAMLIT:
        try:
            return st.secrets[name]
        except (KeyError, FileNotFoundError, Exception):
            pass
    return os.environ.get(name)


def _init():
    global _client, _initialized
    if _initialized:
        return
    _initialized = True
    if not HAS_POSTHOG:
        return
    key = _get_secret("POSTHOG_KEY")
    if not key:
        return
    host = _get_secret("POSTHOG_HOST") or "https://us.i.posthog.com"
    try:
        _client = Posthog(project_api_key=key, host=host, sync_mode=False)
    except Exception:
        _client = None


def _get_distinct_id() -> str:
    """Stable anonymous ID per session via st.session_state."""
    if not HAS_STREAMLIT:
        return "anonymous"
    if "_posthog_id" not in st.session_state:
        st.session_state["_posthog_id"] = f"anon_{uuid.uuid4().hex[:12]}"
    return st.session_state["_posthog_id"]


def track(event_name: str, properties: dict | None = None):
    """Fire an event. Silent no-op if PostHog not configured."""
    _init()
    if _client is None:
        return
    try:
        _client.capture(
            distinct_id=_get_distinct_id(),
            event=event_name,
            properties={**(properties or {}), "timestamp_utc": datetime.utcnow().isoformat()},
        )
    except Exception:
        pass  # never break the app over analytics


def identify(email: str, properties: dict | None = None):
    """Associate the current anonymous ID with an email."""
    _init()
    if _client is None or not email:
        return
    try:
        # Use the email as the new distinct_id; alias the anon ID to it
        anon = _get_distinct_id()
        _client.alias(previous_id=anon, distinct_id=email)
        if properties:
            _client.set(distinct_id=email, properties=properties)
    except Exception:
        pass
