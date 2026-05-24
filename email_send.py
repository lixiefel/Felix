"""
email_send.py — Email delivery via Resend (v2).

- Owner thank-you with PDF attached
- Consultant lead-alert with Excel attached
- Follow-up sequence: 2-day and 7-day post-audit (via Resend scheduled send)
- Reads CALENDLY_URL, CONSULTANT_NOTIFY_EMAIL, RESEND_FROM from secrets
- Silent no-op when Resend not configured
"""

import os
import base64
from datetime import datetime, timedelta

from i18n import t

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


DEFAULT_CONSULTANT_EMAIL = "felixrichard1208@gmail.com"
DEFAULT_CONSULTANT_NAME = "Felix Richard"
DEFAULT_CALENDLY_URL = "https://calendly.com/marginlab-felix"
DEFAULT_FROM_ADDRESS = "MarginLab <onboarding@resend.dev>"


def _get_secret(name: str, default=None):
    if HAS_STREAMLIT:
        try:
            return st.secrets[name]
        except (KeyError, FileNotFoundError, Exception):
            pass
    return os.environ.get(name, default)


def _get_api_key():
    return _get_secret("RESEND_API_KEY")


def _consultant_email():
    return _get_secret("CONSULTANT_NOTIFY_EMAIL", DEFAULT_CONSULTANT_EMAIL)


def _from_address():
    return _get_secret("RESEND_FROM", DEFAULT_FROM_ADDRESS)


def _calendly_url():
    return _get_secret("CALENDLY_URL", DEFAULT_CALENDLY_URL)


def _is_configured() -> bool:
    return HAS_RESEND and bool(_get_api_key())


def _fmt_currency(v, currency="USD"):
    if currency in ("IDR", "JPY", "VND"):
        return f"{v:,.0f}"
    return f"{v:,.2f}"


def _build_consultant_html(*, owner_email, cafe_name, currency, items, audit, app_url):
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
    <tr><td style="padding:4px 12px 4px 0;color:#666">Café</td><td><strong>{cafe_name or "(not provided)"}</strong></td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#666">Email</td><td><strong>{owner_email or "(not provided)"}</strong></td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#666">Currency</td><td>{currency}</td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#666">Items submitted</td><td>{len(items)}</td></tr>
  </table>

  {banner_block}

  <h3 style="color:#1F3864;border-bottom:2px solid #1F3864;padding-bottom:4px;margin-top:24px">Headline</h3>
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
    <strong>QA:</strong> {audit.qa_hard_fails} hard · {audit.qa_soft_warns} soft · {audit.qa_info_obs} info
  </p>

  <h3 style="color:#1F3864;border-bottom:2px solid #1F3864;padding-bottom:4px;margin-top:24px">Recommendations</h3>
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
    Full Excel attached. Admin tab: <a href="{app_url}" style="color:#1F3864">{app_url}</a>
  </p>

  <div style="margin-top:24px;padding-top:12px;border-top:1px solid #ddd;font-size:11px;color:#999">
    MarginLab Pricing Lab · automated lead notification
  </div>
</body>
</html>"""


def _build_owner_html(*, cafe_name, currency, audit, calendly_url, lang="en"):
    lift_sign = "+" if audit.monthly_lift >= 0 else ""
    lift_str = f"{lift_sign}{_fmt_currency(audit.monthly_lift, currency)} {currency}"
    pct_str = f"{'+' if audit.lift_pct >= 0 else ''}{audit.lift_pct*100:.1f}%"
    default_cafe = t("success_default_cafe", lang)
    name_part = cafe_name.strip() if cafe_name and cafe_name.strip() else default_cafe

    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;color:#222;max-width:600px;margin:0 auto;padding:20px">
  <div style="background:#0F1A2E;color:#FAF7F2;padding:20px;border-radius:8px;text-align:center">
    <h1 style="margin:0;font-size:24px">{t("email_owner_h1", lang)}</h1>
    <p style="margin:6px 0 0;opacity:0.85;font-size:14px">{t("email_owner_for", lang)} {name_part}</p>
  </div>

  <p style="margin-top:24px;font-size:15px">{t("email_owner_hi", lang)}</p>

  <p style="font-size:15px;line-height:1.5">
    {t("email_owner_p1", lang)}
  </p>

  <div style="background:#F2EDE3;border-radius:8px;padding:20px;text-align:center;margin:24px 0">
    <div style="font-size:11px;color:#9A7842;text-transform:uppercase;letter-spacing:0.5px">{t("email_owner_metric", lang)}</div>
    <div style="font-size:32px;font-weight:800;color:#0F1A2E;margin-top:4px">{lift_str}</div>
    <div style="font-size:13px;color:#666;margin-top:2px">{pct_str} {t("email_owner_metric_sub", lang)}</div>
  </div>

  <p style="font-size:14px;line-height:1.6;color:#444">
    {t("email_owner_p2", lang)}
  </p>

  <p style="font-size:14px;line-height:1.6;color:#444">
    {t("email_owner_p3", lang)} <a href="{calendly_url}" style="color:#0F1A2E">{calendly_url}</a>
  </p>

  <p style="font-size:14px;margin-top:24px">{t("email_owner_signoff", lang)}</p>

  <div style="margin-top:32px;padding-top:14px;border-top:1px solid #ddd;font-size:11px;color:#999;text-align:center">
    {t("email_owner_footer", lang)}
  </div>
</body>
</html>"""


def _build_followup1_html(*, cafe_name, calendly_url, lang="en"):
    name_part = cafe_name.strip() if cafe_name and cafe_name.strip() else ("there" if lang == "en" else "halo")
    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;color:#222;max-width:600px;margin:0 auto;padding:20px">
  <p style="font-size:15px">{t("email_f1_greeting", lang).format(name=name_part)}</p>

  <p style="font-size:15px;line-height:1.6">
    {t("email_f1_p1", lang)}
  </p>

  <p style="font-size:15px;line-height:1.6">
    {t("email_f1_p2", lang)}
  </p>

  <p style="font-size:15px;line-height:1.6">
    {t("email_f1_p3", lang)}<br>
    <a href="{calendly_url}" style="color:#0F1A2E;font-weight:600">{calendly_url}</a>
  </p>

  <p style="font-size:15px;margin-top:20px">— Felix</p>

  <div style="margin-top:32px;padding-top:14px;border-top:1px solid #ddd;font-size:11px;color:#999;text-align:center">
    MarginLab Pricing Lab
  </div>
</body>
</html>"""


def _build_followup2_html(*, cafe_name, lang="en"):
    name_part = cafe_name.strip() if cafe_name and cafe_name.strip() else ("there" if lang == "en" else "halo")
    return f"""
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;color:#222;max-width:600px;margin:0 auto;padding:20px">
  <p style="font-size:15px">{t("email_f1_greeting", lang).format(name=name_part)}</p>

  <p style="font-size:15px;line-height:1.6">{t("email_f2_p1", lang)}</p>

  <p style="font-size:15px;line-height:1.6">
    {t("email_f2_p2", lang)}
  </p>

  <p style="font-size:15px;line-height:1.6">
    {t("email_f2_p3", lang)}
  </p>

  <p style="font-size:15px;margin-top:20px">— Felix</p>

  <div style="margin-top:32px;padding-top:14px;border-top:1px solid #ddd;font-size:11px;color:#999;text-align:center">
    MarginLab Pricing Lab
  </div>
</body>
</html>"""


def _send_with_resend(*, to_email, subject, html, attachments=None,
                      scheduled_at=None) -> tuple[bool, str]:
    if not _is_configured():
        return False, "Resend not configured (RESEND_API_KEY missing)"

    resend.api_key = _get_api_key()
    payload = {
        "from": _from_address(),
        "to": [to_email],
        "subject": subject,
        "html": html,
    }
    if attachments:
        payload["attachments"] = attachments
    if scheduled_at:
        payload["scheduled_at"] = scheduled_at

    try:
        resend.Emails.send(payload)
        return True, ""
    except Exception as e:
        return False, str(e)


def send_consultant_notification(*, owner_email, currency, items, audit, app_url,
                                 excel_path=None, cafe_name=""):
    attachments = []
    if excel_path:
        try:
            with open(excel_path, "rb") as f:
                attachments.append({
                    "filename": "MarginLab_Audit.xlsx",
                    "content": base64.b64encode(f.read()).decode("ascii"),
                })
        except Exception:
            pass

    subject = f"🆕 MarginLab lead: {owner_email or 'consultant test'} · {audit.confidence} · {audit.monthly_lift:+,.0f} {currency}/mo"
    html = _build_consultant_html(
        owner_email=owner_email, cafe_name=cafe_name, currency=currency,
        items=items, audit=audit, app_url=app_url,
    )
    return _send_with_resend(
        to_email=_consultant_email(), subject=subject, html=html,
        attachments=attachments,
    )


def send_owner_confirmation(*, owner_email, cafe_name, currency, audit, pdf_bytes=None, lang="en"):
    if not owner_email or "@" not in owner_email:
        return False, "Invalid owner email"

    attachments = []
    if pdf_bytes:
        try:
            attachments.append({
                "filename": "MarginLab_Audit_Report.pdf",
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            })
        except Exception:
            pass

    subject = f"{t('email_owner_subject', lang)} · {audit.monthly_lift:+,.0f} {currency}/mo"
    html = _build_owner_html(
        cafe_name=cafe_name, currency=currency, audit=audit,
        calendly_url=_calendly_url(), lang=lang,
    )
    return _send_with_resend(
        to_email=owner_email, subject=subject, html=html, attachments=attachments,
    )


def schedule_followups(*, owner_email, cafe_name, lang="en") -> dict:
    """
    Schedule the two follow-up emails via Resend's `scheduled_at`.
    Returns dict {1: (ok, err), 2: (ok, err)}.
    """
    results = {1: (False, "not configured"), 2: (False, "not configured")}
    if not owner_email or "@" not in owner_email:
        return {1: (False, "Invalid email"), 2: (False, "Invalid email")}

    cal = _calendly_url()
    default_name = "there" if lang == "en" else "halo"
    name_first_word = (cafe_name.split()[0] if cafe_name and cafe_name.split() else default_name)

    send_at_1 = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    results[1] = _send_with_resend(
        to_email=owner_email,
        subject=t("email_f1_subject", lang).format(name=name_first_word),
        html=_build_followup1_html(cafe_name=cafe_name, calendly_url=cal, lang=lang),
        scheduled_at=send_at_1,
    )

    send_at_2 = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    results[2] = _send_with_resend(
        to_email=owner_email,
        subject=t("email_f2_subject", lang),
        html=_build_followup2_html(cafe_name=cafe_name, lang=lang),
        scheduled_at=send_at_2,
    )

    return results
