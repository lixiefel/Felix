"""
email_send.py — Email delivery via Resend free tier (100/day, 3000/month)

Two emails per submission:
  1. Consultant notification → felixrichard1208@gmail.com (full data + lead alert)
  2. Owner confirmation → the email they entered (thank-you + PDF attached)

Reads RESEND_API_KEY from Streamlit secrets or env var. Silently no-ops if not set,
so the app keeps working even without email configured.
"""

import os
import base64
import json
from datetime import datetime

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    import resend
    HAS_RESEND = True
except ImportError:
    HAS_RESEND = False


# ── config ─────────────────────────────────────────────────────────────────────

CONSULTANT_EMAIL = "felixrichard1208@gmail.com"

# Resend lets you send FROM onboarding@resend.dev without any domain setup.
# Once Felix verifies a domain (e.g. marginlab.io), change this to no-reply@marginlab.io
FROM_ADDRESS = "MarginLab <onboarding@resend.dev>"


def _get_api_key() -> str | None:
    """Look in Streamlit secrets first, then env var."""
    if HAS_STREAMLIT:
        try:
            return st.secrets["RESEND_API_KEY"]
        except (KeyError, FileNotFoundError, Exception):
            pass
    return os.environ.get("RESEND_API_KEY")


def _is_configured() -> bool:
    return HAS_RESEND and bool(_get_api_key())


# ── email body builders ────────────────────────────────────────────────────────

def _fmt_currency(v, currency="USD"):
    if currency in ("IDR", "JPY", "VND"):
        return f"{v:,.0f}"
    return f"{v:,.2f}"


def _build_consultant_html(*, owner_email, currency, items, audit, app_url):
    """Email Felix gets — full data, lead alert tone."""
    lift_sign = "+" if audit.monthly_lift >= 0 else ""
    lift_str = f"{lift_sign}{_fmt_currency(audit.monthly_lift, currency)} {currency}"
    pct_str = f"{'+' if audit.lift_pct >= 0 else ''}{audit.lift_pct*100:.1f}%"

    items_rows = ""
    for it in items:
        items_rows += f"""
        <tr>
          <td style="padding:6px 10px;border-bottom:1px solid #eee">{it.name}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee">{it.category}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee">{it.role}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:right">{_fmt_currency(it.cost, currency)}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:right">{_fmt_currency(it.price, currency)}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:right">{it.monthly_units:,}</td>
        </tr>"""

    rec_rows = ""
    for r in audit.items:
        sign = "+" if r.delta_profit_mo >= 0 else ""
        rec_rows += f"""
        <tr>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;font-weight:600">{r.name}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee">{r.action}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:right">{_fmt_currency(r.price_from, currency)} → {_fmt_currency(r.price_to, currency)}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:right">{sign}{_fmt_currency(r.delta_profit_mo, currency)}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee">{r.quadrant}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee">{r.confidence}</td>
        </tr>"""

    banner_block = ""
    if audit.banner:
        banner_block = f'<div style="background:#c00000;color:white;padding:12px;border-radius:6px;margin:16px 0;font-weight:600">⚠ {audit.banner}</div>'

    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;color:#222;max-width:800px;margin:0 auto;padding:20px">
  <div style="background:#1F3864;color:white;padding:16px 20px;border-radius:8px">
    <h2 style="margin:0;font-size:20px">🆕 New MarginLab Submission</h2>
    <p style="margin:4px 0 0;opacity:0.85;font-size:13px">Generated {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</p>
  </div>

  <h3 style="color:#1F3864;border-bottom:2px solid #1F3864;padding-bottom:4px;margin-top:24px">Lead</h3>
  <table style="font-size:14px">
    <tr><td style="padding:4px 12px 4px 0;color:#666">Email</td><td><strong>{owner_email or "(not provided)"}</strong></td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#666">Currency</td><td>{currency}</td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#666">Items submitted</td><td>{len(items)}</td></tr>
  </table>

  {banner_block}

  <h3 style="color:#1F3864;border-bottom:2px solid #1F3864;padding-bottom:4px;margin-top:24px">Headline Results</h3>
  <table style="font-size:14px;width:100%">
    <tr>
      <td style="padding:10px 16px;background:#f4f6f9;border-radius:6px;width:33%">
        <div style="font-size:11px;color:#666;text-transform:uppercase">Monthly Δ Profit</div>
        <div style="font-size:22px;font-weight:700;color:#1F3864">{lift_str}</div>
      </td>
      <td style="width:1%"></td>
      <td style="padding:10px 16px;background:#f4f6f9;border-radius:6px;width:33%">
        <div style="font-size:11px;color:#666;text-transform:uppercase">Lift %</div>
        <div style="font-size:22px;font-weight:700;color:#1F3864">{pct_str}</div>
      </td>
      <td style="width:1%"></td>
      <td style="padding:10px 16px;background:#f4f6f9;border-radius:6px;width:33%">
        <div style="font-size:11px;color:#666;text-transform:uppercase">Confidence</div>
        <div style="font-size:22px;font-weight:700;color:#1F3864">{audit.confidence}</div>
      </td>
    </tr>
  </table>

  <p style="font-size:13px;color:#555;margin-top:12px">
    <strong>Best opportunity:</strong> {audit.best_item}<br>
    <strong>QA Hard fails:</strong> {audit.qa_hard_fails} · Soft warnings: {audit.qa_soft_warns} · Info: {audit.qa_info_obs}
  </p>

  <h3 style="color:#1F3864;border-bottom:2px solid #1F3864;padding-bottom:4px;margin-top:24px">Per-Item Recommendations</h3>
  <table style="width:100%;border-collapse:collapse;font-size:12px">
    <thead><tr style="background:#1F3864;color:white">
      <th style="padding:8px 10px;text-align:left">Item</th>
      <th style="padding:8px 10px;text-align:left">Action</th>
      <th style="padding:8px 10px;text-align:right">Price</th>
      <th style="padding:8px 10px;text-align:right">Δ Profit/mo</th>
      <th style="padding:8px 10px;text-align:left">Quadrant</th>
      <th style="padding:8px 10px;text-align:left">Conf</th>
    </tr></thead>
    <tbody>{rec_rows}</tbody>
  </table>

  <h3 style="color:#1F3864;border-bottom:2px solid #1F3864;padding-bottom:4px;margin-top:24px">Submitted Inputs</h3>
  <table style="width:100%;border-collapse:collapse;font-size:12px">
    <thead><tr style="background:#1F3864;color:white">
      <th style="padding:8px 10px;text-align:left">Item</th>
      <th style="padding:8px 10px;text-align:left">Category</th>
      <th style="padding:8px 10px;text-align:left">Role</th>
      <th style="padding:8px 10px;text-align:right">Cost</th>
      <th style="padding:8px 10px;text-align:right">Price</th>
      <th style="padding:8px 10px;text-align:right">Units/mo</th>
    </tr></thead>
    <tbody>{items_rows}</tbody>
  </table>

  <p style="font-size:13px;color:#555;margin-top:24px">
    Full Excel attached. Or open in the app's Admin tab: <a href="{app_url}" style="color:#1F3864">{app_url}</a>
  </p>

  <div style="margin-top:24px;padding-top:12px;border-top:1px solid #ddd;font-size:11px;color:#999">
    MarginLab Pricing Lab · automated lead notification
  </div>
</body>
</html>"""


def _build_owner_html(*, owner_email, cafe_name, currency, audit):
    """Email the owner gets — friendly thank-you with PDF attached."""
    lift_sign = "+" if audit.monthly_lift >= 0 else ""
    lift_str = f"{lift_sign}{_fmt_currency(audit.monthly_lift, currency)} {currency}"
    pct_str = f"{'+' if audit.lift_pct >= 0 else ''}{audit.lift_pct*100:.1f}%"
    name_part = cafe_name if cafe_name else "your café"

    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;color:#222;max-width:600px;margin:0 auto;padding:20px">
  <div style="background:#1F3864;color:white;padding:20px;border-radius:8px;text-align:center">
    <h1 style="margin:0;font-size:24px">Your MarginLab Pricing Audit</h1>
    <p style="margin:6px 0 0;opacity:0.85;font-size:14px">for {name_part}</p>
  </div>

  <p style="margin-top:24px;font-size:15px">Hi,</p>

  <p style="font-size:15px;line-height:1.5">
    Thanks for running a MarginLab pricing audit. Your full report is attached as a PDF
    — open it on your phone, your laptop, or forward it to your accountant.
  </p>

  <div style="background:#f4f6f9;border-radius:8px;padding:20px;text-align:center;margin:24px 0">
    <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:0.5px">Potential monthly profit gain</div>
    <div style="font-size:32px;font-weight:800;color:#1F3864;margin-top:4px">{lift_str}</div>
    <div style="font-size:13px;color:#666;margin-top:2px">{pct_str} versus your current pricing</div>
  </div>

  <p style="font-size:14px;line-height:1.6;color:#444">
    These recommendations come from a profit-maximizing pricing model that accounts for
    each item's role on your menu, your category, and demand sensitivity.
    The PDF shows the full breakdown — item by item, with quadrant classification
    (Star / Plowhorse / Puzzle / Dog) and a plain-language narrative for each move.
  </p>

  <p style="font-size:14px;line-height:1.6;color:#444">
    <strong>Want help implementing this?</strong> Reply to this email — I'd be happy to walk you through
    the recommendations and help you sequence the changes.
  </p>

  <p style="font-size:14px;margin-top:24px">
    — Felix · MarginLab
  </p>

  <div style="margin-top:32px;padding-top:14px;border-top:1px solid #ddd;font-size:11px;color:#999;text-align:center">
    You received this because you ran a free pricing audit at MarginLab.<br>
    Powered by Lerner-optimal pricing economics.
  </div>
</body>
</html>"""


# ── send functions ─────────────────────────────────────────────────────────────

def send_consultant_notification(*, owner_email, currency, items, audit, app_url, excel_path=None):
    """Send full submission data to Felix. Returns (ok, error_message)."""
    if not _is_configured():
        return False, "Resend not configured (RESEND_API_KEY missing)"

    resend.api_key = _get_api_key()

    attachments = []
    if excel_path:
        try:
            with open(excel_path, "rb") as f:
                excel_b64 = base64.b64encode(f.read()).decode("ascii")
            attachments.append({
                "filename": "MarginLab_Audit.xlsx",
                "content": excel_b64,
            })
        except Exception:
            pass  # attachment optional

    subject = f"🆕 MarginLab lead: {owner_email or 'consultant test'} · {audit.confidence} conf · {audit.monthly_lift:+,.0f} {currency}/mo"

    try:
        resp = resend.Emails.send({
            "from": FROM_ADDRESS,
            "to": [CONSULTANT_EMAIL],
            "subject": subject,
            "html": _build_consultant_html(
                owner_email=owner_email,
                currency=currency,
                items=items,
                audit=audit,
                app_url=app_url,
            ),
            "attachments": attachments,
        })
        return True, ""
    except Exception as e:
        return False, str(e)


def send_owner_confirmation(*, owner_email, cafe_name, currency, audit, pdf_bytes=None):
    """Send thank-you with PDF attached to the owner. Returns (ok, error_message)."""
    if not _is_configured():
        return False, "Resend not configured"
    if not owner_email or "@" not in owner_email:
        return False, "Invalid owner email"

    resend.api_key = _get_api_key()

    attachments = []
    if pdf_bytes:
        try:
            pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
            attachments.append({
                "filename": "MarginLab_Audit_Report.pdf",
                "content": pdf_b64,
            })
        except Exception:
            pass

    subject = f"Your MarginLab pricing audit · {audit.monthly_lift:+,.0f} {currency}/mo opportunity"

    try:
        resp = resend.Emails.send({
            "from": FROM_ADDRESS,
            "to": [owner_email],
            "subject": subject,
            "html": _build_owner_html(
                owner_email=owner_email,
                cafe_name=cafe_name,
                currency=currency,
                audit=audit,
            ),
            "attachments": attachments,
        })
        return True, ""
    except Exception as e:
        return False, str(e)


def send_both(*, owner_email, cafe_name, currency, items, audit, app_url, excel_path=None, pdf_bytes=None):
    """Convenience wrapper that fires both emails. Returns dict of results."""
    return {
        "consultant": send_consultant_notification(
            owner_email=owner_email, currency=currency, items=items,
            audit=audit, app_url=app_url, excel_path=excel_path,
        ),
        "owner": send_owner_confirmation(
            owner_email=owner_email, cafe_name=cafe_name, currency=currency,
            audit=audit, pdf_bytes=pdf_bytes,
        ) if owner_email else (False, "No owner email"),
    }
