"""
email_validate.py — Deliverability check for collected emails.
Combines: regex shape + throwaway-domain blocklist + (optional) MX record check.
Fails open if dnspython unavailable.
"""

import re

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

# Common throwaway / test domains. Add more as you spot them in submissions.
THROWAWAY_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "throwawaymail.com", "yopmail.com", "trashmail.com", "fakeinbox.com",
    "getairmail.com", "sharklasers.com", "dispostable.com", "maildrop.cc",
    "mvrht.com", "spam4.me", "tempinbox.com", "tempr.email",
    # Test / dev addresses we want to reject:
    "example.com", "test.com", "test.test", "a.com", "asdf.com",
}

# Obvious test usernames
SUSPICIOUS_LOCAL_PARTS = {"test", "asdf", "abc", "a", "x", "fake", "noreply"}


def _has_mx_record(domain: str) -> bool | None:
    """Return True/False if checkable, None if dnspython missing (fail open)."""
    try:
        import dns.resolver
    except ImportError:
        return None
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=3.0)
        return len(list(answers)) > 0
    except Exception:
        return False


def validate_email(email: str) -> tuple[bool, str]:
    """
    Returns (ok, reason).
    `reason` is "" on success, else a short user-friendly message.
    """
    if not email or not isinstance(email, str):
        return False, "Please enter an email address."

    email = email.strip().lower()

    # Shape check
    if not EMAIL_RE.match(email):
        return False, "That doesn't look like a valid email address."

    local_part, domain = email.split("@", 1)

    # Local-part heuristics
    if local_part in SUSPICIOUS_LOCAL_PARTS:
        return False, "Please use a real email address — that one looks like a test."
    if len(local_part) < 2:
        return False, "Email username is too short."

    # Throwaway domain block
    if domain in THROWAWAY_DOMAINS:
        return False, "Please use a real email address (no throwaway services)."

    # Optional MX check (fail open if dnspython not installed)
    mx_ok = _has_mx_record(domain)
    if mx_ok is False:
        return False, "We couldn't find a mail server for that domain. Please double-check."

    return True, ""
