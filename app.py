"""
app.py — MarginLab Pricing Lab v2

Routes:
  - Landing page (default for unauthenticated visitors)
  - Owner audit (Quick Audit) → PDF-only delivery via email
  - Consultant view (password-gated) → full access, both downloads, admin

V2 changes:
  - Landing page with hero / how-it-works / who-built / CTA
  - Owner mode never shows Excel download, never shows full results on screen
  - Email validated with regex + MX check + throwaway blocklist
  - Rate limiting (5/hour per IP) + honeypot anti-bot field
  - Sheets-backed persistence with SQLite fallback
  - PostHog analytics (silent if not configured)
  - Mobile-friendly CSS (vertical cards on narrow screens)
  - Newsletter opt-in checkbox
"""

import os
import streamlit as st
import pandas as pd
from pathlib import Path

from engine import (
    run_audit, SettingsInput, ItemInput, AuditResult,
    CATEGORIES, ROLES, CURRENCIES, ROUND_STEPS, ENDINGS,
)
from sheets_store import save_submission, get_all_submissions, get_submission_inputs, is_sheets_active
from pdf_report import generate_pdf, generate_html_report
from email_send import (
    send_consultant_notification, send_owner_confirmation,
    schedule_followups, _is_configured as _email_configured,
    _calendly_url,
)
from email_validate import validate_email
from rate_limit import check_and_record, get_ip
from lite_excel import export_lite_excel
from analytics import track, identify


# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MarginLab · Pricing Audit",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Global ─────────────────────────────────────────────── */
  html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, Arial, sans-serif;
  }
  footer { display: none !important; }
  #MainMenu { visibility: hidden; }

  /* ── App header (consultant + owner audit) ────────────────── */
  .ml-header {
    background: linear-gradient(135deg, #1F3864 0%, #2d5090 100%);
    color: white;
    padding: 18px 24px 12px;
    border-radius: 10px;
    margin-bottom: 20px;
  }
  .ml-header h1 { margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; }
  .ml-header p  { margin: 4px 0 0; opacity: 0.85; font-size: 13px; }

  /* ── Landing hero ─────────────────────────────────────────── */
  .landing-hero {
    text-align: center;
    padding: 60px 20px 30px;
    max-width: 720px;
    margin: 0 auto;
  }
  .landing-hero .eyebrow {
    color: #1F3864;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 12px;
  }
  .landing-hero h1 {
    font-size: 48px;
    font-weight: 800;
    color: #1A1A2E;
    letter-spacing: -1.5px;
    line-height: 1.1;
    margin: 0 0 16px;
  }
  .landing-hero h1 .accent { color: #1F3864; }
  .landing-hero p.sub {
    font-size: 18px;
    color: #545B6E;
    line-height: 1.5;
    margin: 0 0 32px;
  }
  /* Big CTA button styling targeted at the streamlit primary button */
  .stButton > button[kind="primary"] {
    background: #1F3864 !important;
    color: white !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    padding: 12px 32px !important;
    border-radius: 8px !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(31,56,100,0.25) !important;
  }
  .stButton > button[kind="primary"]:hover {
    background: #2d5090 !important;
    box-shadow: 0 6px 20px rgba(31,56,100,0.35) !important;
  }

  /* ── How it works section ────────────────────────────────── */
  .how-section {
    max-width: 960px;
    margin: 40px auto;
    padding: 0 20px;
  }
  .how-section h2 {
    text-align: center;
    color: #1A1A2E;
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 32px;
    letter-spacing: -0.5px;
  }
  .how-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
  }
  .how-card {
    background: white;
    border: 1px solid #e0e6f0;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
  }
  .how-card .step-num {
    width: 36px; height: 36px;
    background: #1F3864; color: white;
    border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 16px; margin-bottom: 12px;
  }
  .how-card h3 { margin: 4px 0 6px; font-size: 16px; color: #1A1A2E; }
  .how-card p  { margin: 0; font-size: 13px; color: #6b7280; line-height: 1.5; }

  /* ── Example/proof block ────────────────────────────────── */
  .proof-section {
    max-width: 800px;
    margin: 40px auto;
    padding: 32px;
    background: #f4f6f9;
    border-radius: 12px;
    text-align: center;
  }
  .proof-section .metric-row {
    display: flex; justify-content: center; gap: 32px;
    margin: 16px 0 8px;
    flex-wrap: wrap;
  }
  .proof-metric .label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }
  .proof-metric .value { font-size: 28px; font-weight: 800; color: #1F3864; }
  .proof-section p.note { font-size: 12px; color: #6b7280; margin-top: 8px; font-style: italic; }

  /* ── Who block ──────────────────────────────────────────── */
  .who-section {
    max-width: 720px; margin: 40px auto; padding: 0 20px;
    text-align: center; color: #545B6E; font-size: 15px; line-height: 1.6;
  }
  .who-section h2 {
    color: #1A1A2E; font-size: 22px; margin-bottom: 12px; font-weight: 700;
  }

  /* ── Footer ─────────────────────────────────────────────── */
  .landing-footer {
    margin-top: 60px; padding: 24px 20px 12px;
    border-top: 1px solid #e0e6f0;
    text-align: center;
    color: #9aa5b8;
    font-size: 12px;
  }

  /* ── Metric cards (results page, consultant only) ────────── */
  .metric-card {
    background: white;
    border: 1px solid #e0e6f0;
    border-radius: 10px;
    padding: 16px 18px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(31,56,100,0.06);
  }
  .metric-card .label { font-size: 10px; color: #7a8599; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
  .metric-card .value { font-size: 26px; font-weight: 800; color: #1F3864; }
  .metric-card .sub   { font-size: 11px; color: #9aa5b8; margin-top: 2px; }

  .qa-banner {
    background: #c00000; color: white;
    padding: 12px 18px; border-radius: 8px; font-weight: 600;
    margin-bottom: 16px; font-size: 14px;
  }

  .chip { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; display: inline-block; }
  .q-Star { background: #d9f2d9; color: #1a5e1a; }
  .q-Plowhorse { background: #d9e1f2; color: #1f3864; }
  .q-Puzzle { background: #fce4d6; color: #7e2e00; }
  .q-Dog { background: #fce3e3; color: #7e0000; }
  .m-Above { background: #fce3e3; color: #7e0000; }
  .m-Within { background: #d9f2d9; color: #1a5e1a; }
  .m-Below { background: #fff2cc; color: #6b4e00; }
  .m-No { background: #f0f0f0; color: #555; }

  .act-raise { color: #006100; font-weight: 700; }
  .act-cut { color: #c00000; font-weight: 700; }
  .act-hold { color: #555; font-weight: 700; }

  .section-head {
    color: #1F3864; font-size: 15px; font-weight: 700;
    border-bottom: 2px solid #1F3864; padding-bottom: 4px;
    margin: 20px 0 10px;
  }

  /* Headline card on owner success page */
  .owner-success-card {
    background: white;
    border: 1px solid #e0e6f0;
    border-radius: 12px;
    padding: 32px;
    text-align: center;
    max-width: 560px;
    margin: 24px auto;
    box-shadow: 0 4px 14px rgba(31,56,100,0.08);
  }
  .owner-success-card .big-number {
    font-size: 48px; font-weight: 800; color: #1F3864;
    letter-spacing: -1px; margin: 12px 0;
  }
  .owner-success-card .label {
    font-size: 12px; color: #7a8599; text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  /* Honeypot — invisible to humans, visible to bots */
  .honeypot {
    position: absolute !important;
    left: -9999px !important;
    width: 1px !important;
    height: 1px !important;
    opacity: 0 !important;
  }

  /* ── Mobile responsive ──────────────────────────────────── */
  @media (max-width: 640px) {
    .landing-hero { padding: 32px 16px 20px; }
    .landing-hero h1 { font-size: 32px; }
    .landing-hero p.sub { font-size: 16px; }
    .how-grid { grid-template-columns: 1fr; }
    .proof-section .metric-row { flex-direction: column; gap: 16px; }
    .owner-success-card .big-number { font-size: 36px; }
    /* Stack any 4-col header into 1-col on mobile */
    div[data-testid="column"] { width: 100% !important; }
  }
</style>
""", unsafe_allow_html=True)


# ── helpers ────────────────────────────────────────────────────────────────────

def _pct_display(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{v*100:.1f}%"


def _currency_display(v: float, currency: str) -> str:
    if currency in ("IDR", "JPY", "VND"):
        return f"{v:,.0f}"
    return f"{v:,.2f}"


def _blank_item():
    return {"name": "", "category": "Coffee", "role": "Core",
            "cost": 0.0, "price": 0.0, "monthly_units": 0,
            "comp1": "", "comp2": "", "comp3": ""}


# ── session state init ────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "view": "landing",          # landing | owner_audit | consultant
        "consultant_auth": False,
        "audit_result": None,
        "audit_currency": "USD",
        "audit_cafe_name": "",
        "audit_owner_email": "",    # filled in when owner submits
        "email_submitted": False,
        "num_items": 6,
        "menu_items": [_blank_item() for _ in range(30)],
        "settings": {
            "currency": "USD", "round_to": 0.10, "ending": ".00",
            "max_raise": 0.10, "max_cut": -0.05,
            "shr_high": 1.0, "shr_med": 0.5, "shr_low": 0.25,
            "demo_mode": "No",
        },
        "newsletter_opt_in": True,
        "landing_tracked": False,
        "form_started_tracked": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # Defensive: ensure menu_items is exactly 30 entries
    if not isinstance(st.session_state.menu_items, list) or len(st.session_state.menu_items) < 30:
        existing = list(st.session_state.menu_items) if isinstance(st.session_state.menu_items, list) else []
        st.session_state.menu_items = existing + [_blank_item() for _ in range(30 - len(existing))]


_init_state()


# ══════════════════════════════════════════════════════════════════════════════
# LANDING PAGE
# ══════════════════════════════════════════════════════════════════════════════

def render_landing():
    if not st.session_state.landing_tracked:
        track("landing_view")
        st.session_state.landing_tracked = True

    # Hero
    st.markdown("""
    <div class="landing-hero">
      <div class="eyebrow">MarginLab Pricing Lab</div>
      <h1>Profit-maximizing menu pricing<br>for <span class="accent">cafés</span>.</h1>
      <p class="sub">A free 15-minute audit using Lerner economics and demand calibration.
      No login. No spam. PDF report in your inbox.</p>
    </div>
    """, unsafe_allow_html=True)

    # CTA button
    cta_col1, cta_col2, cta_col3 = st.columns([2, 1, 2])
    with cta_col2:
        if st.button("Start your free audit →", type="primary", use_container_width=True):
            track("cta_start_audit_click")
            st.session_state.view = "owner_audit"
            st.rerun()

    # How it works
    st.markdown("""
    <div class="how-section">
      <h2>How it works</h2>
      <div class="how-grid">
        <div class="how-card">
          <div class="step-num">1</div>
          <h3>Enter your menu</h3>
          <p>Items, costs, current prices, monthly units. Takes about 5 minutes for a typical café.</p>
        </div>
        <div class="how-card">
          <div class="step-num">2</div>
          <h3>The model runs</h3>
          <p>A 13-sheet Excel engine computes the profit-maximizing price for each item — guarded by role caps, market context, and confidence-weighted shrinkage.</p>
        </div>
        <div class="how-card">
          <div class="step-num">3</div>
          <h3>PDF in your inbox</h3>
          <p>Item-by-item recommendations, sensitivity analysis, and a sequencing plan. Forward it to your accountant.</p>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Proof / example
    st.markdown("""
    <div class="proof-section">
      <div style="font-size:11px;color:#6b7280;letter-spacing:0.5px;text-transform:uppercase;font-weight:600">
        Example output for a 6-item café menu
      </div>
      <div class="metric-row">
        <div class="proof-metric">
          <div class="label">Monthly Δ profit</div>
          <div class="value">+$372</div>
        </div>
        <div class="proof-metric">
          <div class="label">Lift</div>
          <div class="value">+1.4%</div>
        </div>
        <div class="proof-metric">
          <div class="label">Items to change</div>
          <div class="value">5 of 6</div>
        </div>
      </div>
      <p class="note">Real audits are personalized to your specific menu and category mix.</p>
    </div>
    """, unsafe_allow_html=True)

    # Who built this
    st.markdown("""
    <div class="who-section">
      <h2>Who built this</h2>
      <p>
        MarginLab is built and run by <strong>Felix Richard</strong>, an independent consultant
        focused on pricing for food and beverage operators. The model behind it combines
        Lerner-optimal markup theory, menu-engineering quadrants, and demand-calibrated
        elasticities — packaged into something a café owner can act on the same day.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Bottom CTA
    cta_col1, cta_col2, cta_col3 = st.columns([2, 1, 2])
    with cta_col2:
        if st.button("Get my free audit", type="primary", use_container_width=True, key="cta_bottom"):
            track("cta_bottom_click")
            st.session_state.view = "owner_audit"
            st.rerun()

    # Footer
    st.markdown(f"""
    <div class="landing-footer">
      © MarginLab · Contact: <a href="mailto:felixrichard1208@gmail.com" style="color:#1F3864">felixrichard1208@gmail.com</a><br>
      We only use your email to send your audit report and follow-ups. We never share it.
      <br><br>
      <a href="?view=consultant" style="color:#9aa5b8;font-size:11px">Consultant access</a>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# OWNER AUDIT VIEW (Quick Audit)
# ══════════════════════════════════════════════════════════════════════════════

def render_owner_audit():
    # Header
    st.markdown("""
    <div class="ml-header">
      <h1>📊 MarginLab Pricing Audit</h1>
      <p>Enter your menu below. We'll email your PDF report in about 30 seconds.</p>
    </div>
    """, unsafe_allow_html=True)

    # Back button
    if st.button("← Back to home"):
        st.session_state.view = "landing"
        st.session_state.audit_result = None
        st.session_state.email_submitted = False
        st.rerun()

    # If audit already run and email already submitted, show success state
    if st.session_state.audit_result is not None and st.session_state.email_submitted:
        render_owner_success()
        return

    currency = st.session_state.settings["currency"]
    cafe_name = st.text_input("Your café name (optional)",
                              value=st.session_state.audit_cafe_name,
                              placeholder="e.g. The Daily Grind")
    st.session_state.audit_cafe_name = cafe_name

    # Currency
    qc1, qc2 = st.columns([1, 5])
    with qc1:
        cur = st.selectbox(
            "Currency", CURRENCIES,
            index=CURRENCIES.index(st.session_state.settings["currency"]),
        )
        st.session_state.settings["currency"] = cur
    currency = cur

    # Menu table
    st.markdown('<div class="section-head">Your Menu</div>', unsafe_allow_html=True)
    st.caption("Enter your menu items. You need at least: name, cost, current price, and monthly units sold.")

    _render_menu_table(currency)

    # Add/remove buttons
    btn_c1, btn_c2, _ = st.columns([1, 1, 7])
    with btn_c1:
        if st.button("＋ Add item") and st.session_state.num_items < 30:
            st.session_state.num_items += 1
            st.rerun()
    with btn_c2:
        if st.button("－ Remove last") and st.session_state.num_items > 1:
            st.session_state.num_items -= 1
            st.rerun()

    # Competitor expander
    with st.expander("🏪 Add competitor prices (optional)"):
        st.caption("Enter prices from up to 3 nearby cafés for items where market context matters. Leave blank to skip.")
        _render_competitor_table()

    # Newsletter opt-in
    newsletter = st.checkbox(
        "Send me Felix's monthly pricing insights newsletter (unsubscribe anytime)",
        value=st.session_state.newsletter_opt_in,
    )
    st.session_state.newsletter_opt_in = newsletter

    # Honeypot — bot trap (real users never see this)
    honeypot = st.text_input(
        "Leave this empty",
        value="",
        key="_honeypot_field",
        label_visibility="collapsed",
    )
    st.markdown("""
    <style>
      div[data-testid="stTextInput"]:has(input[aria-label="Leave this empty"]) {
        position: absolute !important; left: -9999px !important;
      }
    </style>
    """, unsafe_allow_html=True)

    # Email gate BEFORE running the audit (so we have it for delivery)
    st.markdown('<div class="section-head">Your Email</div>', unsafe_allow_html=True)
    st.caption("We'll send your PDF report to this address.")
    email_val = st.text_input("Email address", placeholder="you@yourcafe.com", key="owner_email_input")
    st.session_state.audit_owner_email = email_val

    # Run button
    st.markdown("---")
    run_col, _ = st.columns([2, 6])
    with run_col:
        run_clicked = st.button("📩 Email me my audit", type="primary",
                                use_container_width=True, key="owner_run")

    if run_clicked:
        # Honeypot check
        if honeypot.strip():
            # Silently no-op (bot trap)
            st.success("Submitted! Check your inbox.")
            return

        # Validate email
        ok, reason = validate_email(email_val)
        if not ok:
            st.error(reason)
            return

        # Rate limit
        ip = get_ip()
        allowed, _ = check_and_record(ip, max_per_hour=5)
        if not allowed:
            st.error("You've reached the audit limit for this hour. Please try again later or email felixrichard1208@gmail.com if you need more.")
            return

        # Collect items
        items_raw = [st.session_state.menu_items[i] for i in range(st.session_state.num_items)]
        active = [it for it in items_raw if it.get("name", "").strip()]
        if not active:
            st.error("Please enter at least one menu item.")
            return

        def _parse_comp(v):
            try:
                f = float(str(v).replace(",", "."))
                return f if f > 0 else None
            except (ValueError, TypeError):
                return None

        item_inputs = [
            ItemInput(
                name=it["name"].strip(),
                category=it["category"],
                role=it["role"],
                cost=float(it["cost"]),
                price=float(it["price"]),
                monthly_units=int(it["monthly_units"]),
                comp1=_parse_comp(it["comp1"]),
                comp2=_parse_comp(it["comp2"]),
                comp3=_parse_comp(it["comp3"]),
            )
            for it in active
        ]

        s = st.session_state.settings
        settings_input = SettingsInput(
            currency=s["currency"], round_to=float(s["round_to"]),
            ending=s["ending"], max_raise=float(s["max_raise"]),
            max_cut=float(s["max_cut"]), shr_high=float(s["shr_high"]),
            shr_med=float(s["shr_med"]), shr_low=float(s["shr_low"]),
            demo_mode=s["demo_mode"],
        )

        track("form_completed", {"item_count": len(item_inputs), "currency": s["currency"]})

        with st.spinner("Running the model and sending your report…"):
            result, error = run_audit(settings_input, item_inputs)
            if error:
                st.error(f"Something went wrong: {error}")
                return

            st.session_state.audit_result = result
            st.session_state.audit_currency = s["currency"]
            st.session_state.email_submitted = True

            # Persist
            save_submission(
                email=email_val, mode="owner", currency=s["currency"],
                items=item_inputs, audit=result,
                cafe_name=cafe_name, newsletter_opt_in=newsletter,
            )

            # Track + identify
            track("email_submitted", {"item_count": len(item_inputs)})
            identify(email_val, {"cafe_name": cafe_name,
                                  "newsletter_opt_in": newsletter})

            # Send emails
            if _email_configured():
                try:
                    pdf_bytes = generate_pdf(
                        result, s["currency"], cafe_name,
                        calendly_url=_calendly_url(),
                    )
                    send_consultant_notification(
                        owner_email=email_val, currency=s["currency"],
                        items=item_inputs, audit=result,
                        app_url=os.environ.get("APP_URL", "https://share.streamlit.io"),
                        excel_path=result.excel_path,
                        cafe_name=cafe_name,
                    )
                    send_owner_confirmation(
                        owner_email=email_val, cafe_name=cafe_name,
                        currency=s["currency"], audit=result,
                        pdf_bytes=pdf_bytes,
                    )
                    # Schedule follow-ups
                    schedule_followups(owner_email=email_val, cafe_name=cafe_name)
                except Exception:
                    pass  # never block flow on email failure

        st.rerun()


def render_owner_success():
    audit = st.session_state.audit_result
    currency = st.session_state.audit_currency
    cafe_name = st.session_state.audit_cafe_name
    email = st.session_state.audit_owner_email

    lift_sign = "+" if audit.monthly_lift >= 0 else ""
    lift_str = f"{lift_sign}{_currency_display(audit.monthly_lift, currency)} {currency}"
    pct_str = _pct_display(audit.lift_pct)
    display_cafe = cafe_name if cafe_name else "your café"

    st.markdown(f"""
    <div class="owner-success-card">
      <div style="font-size:36px;margin-bottom:8px">✓</div>
      <h2 style="margin:0 0 8px;color:#1A1A2E;font-size:24px;font-weight:700">
        Your audit is on its way
      </h2>
      <p style="color:#6b7280;font-size:14px;margin:0 0 24px">
        We just emailed your full PDF report to <strong>{email}</strong>. Check your inbox in the next minute or two.
      </p>

      <div class="label">Estimated potential lift for {display_cafe}</div>
      <div class="big-number">{lift_str}</div>
      <div style="color:#6b7280;font-size:13px">{pct_str} versus your current pricing · monthly</div>

      <p style="margin-top:24px;font-size:13px;color:#6b7280;line-height:1.6">
        The full per-item breakdown, sensitivity analysis, and a sequencing plan are in your PDF.<br>
        Don't see it? Check spam, or email <a href="mailto:felixrichard1208@gmail.com" style="color:#1F3864">felixrichard1208@gmail.com</a>.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Reset / new audit
    rc1, rc2, rc3 = st.columns([2, 1, 2])
    with rc2:
        if st.button("Run another audit", use_container_width=True):
            st.session_state.audit_result = None
            st.session_state.email_submitted = False
            st.session_state.audit_owner_email = ""
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# CONSULTANT VIEW
# ══════════════════════════════════════════════════════════════════════════════

def _check_consultant_password() -> bool:
    if st.session_state.consultant_auth:
        return True
    st.markdown('<div class="ml-header"><h1>🔒 Consultant Access</h1></div>', unsafe_allow_html=True)
    pw = st.text_input("Password", type="password", placeholder="Consultant password")
    if st.button("Sign in"):
        correct = os.environ.get("CONSULTANT_PASSWORD")
        if correct is None:
            try:
                correct = st.secrets["CONSULTANT_PASSWORD"]
            except (KeyError, FileNotFoundError, Exception):
                correct = "marginlab2024"  # fallback for local dev
        if pw and pw == correct:
            st.session_state.consultant_auth = True
            st.rerun()
        elif pw:
            st.error("Wrong password.")
    if st.button("← Back to home"):
        st.session_state.view = "landing"
        st.rerun()
    return False


def render_consultant():
    if not _check_consultant_password():
        return

    st.markdown("""
    <div class="ml-header">
      <h1>📊 MarginLab · Consultant View</h1>
      <p>Run audits on behalf of a client · access lead history · download Excel and PDF</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("← Back to home", key="cons_back"):
        st.session_state.view = "landing"
        st.session_state.audit_result = None
        st.rerun()

    tabs = st.tabs(["📝 Input", "📊 Results", "🗂 Admin"])

    with tabs[0]:
        _consultant_input_tab()
    with tabs[1]:
        _consultant_results_tab()
    with tabs[2]:
        _consultant_admin_tab()


def _consultant_input_tab():
    st.markdown('<div class="section-head">Settings</div>', unsafe_allow_html=True)
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    with sc1:
        cur = st.selectbox("Currency", CURRENCIES,
            index=CURRENCIES.index(st.session_state.settings["currency"]),
            key="cons_cur")
        st.session_state.settings["currency"] = cur
    with sc2:
        rnd_idx = ROUND_STEPS.index(st.session_state.settings["round_to"]) if st.session_state.settings["round_to"] in ROUND_STEPS else 2
        rnd = st.selectbox("Round to", ROUND_STEPS, index=rnd_idx, key="cons_rnd")
        st.session_state.settings["round_to"] = rnd
    with sc3:
        end_idx = ENDINGS.index(st.session_state.settings["ending"])
        ending = st.selectbox("Charm ending", ENDINGS, index=end_idx, key="cons_end")
        st.session_state.settings["ending"] = ending
    with sc4:
        demo = st.selectbox("Demo mode", ["No", "Yes"],
            index=0 if st.session_state.settings["demo_mode"] == "No" else 1,
            key="cons_demo")
        st.session_state.settings["demo_mode"] = demo
    with sc5:
        st.write("")

    with st.expander("Guardrails & shrinkage"):
        ga, gb, gc, gd, ge = st.columns(5)
        with ga:
            mr = st.number_input("Max raise", 0.0, 0.5,
                st.session_state.settings["max_raise"], 0.01, format="%.2f", key="cons_mr")
            st.session_state.settings["max_raise"] = mr
        with gb:
            mc = st.number_input("Max cut", -0.5, 0.0,
                st.session_state.settings["max_cut"], 0.01, format="%.2f", key="cons_mc")
            st.session_state.settings["max_cut"] = mc
        with gc:
            sh = st.number_input("Shrink HIGH", 0.0, 1.0,
                st.session_state.settings["shr_high"], 0.05, format="%.2f", key="cons_sh")
            st.session_state.settings["shr_high"] = sh
        with gd:
            sm = st.number_input("Shrink MED", 0.0, 1.0,
                st.session_state.settings["shr_med"], 0.05, format="%.2f", key="cons_sm")
            st.session_state.settings["shr_med"] = sm
        with ge:
            sl = st.number_input("Shrink LOW", 0.0, 1.0,
                st.session_state.settings["shr_low"], 0.05, format="%.2f", key="cons_sl")
            st.session_state.settings["shr_low"] = sl

    currency = st.session_state.settings["currency"]

    cafe = st.text_input("Café name", value=st.session_state.audit_cafe_name,
                         placeholder="e.g. The Daily Grind", key="cons_cafe")
    st.session_state.audit_cafe_name = cafe

    st.markdown('<div class="section-head">Menu</div>', unsafe_allow_html=True)
    _render_menu_table(currency, key_prefix="cons_")

    btn_c1, btn_c2, _ = st.columns([1, 1, 7])
    with btn_c1:
        if st.button("＋ Add item", key="cons_add") and st.session_state.num_items < 30:
            st.session_state.num_items += 1
            st.rerun()
    with btn_c2:
        if st.button("－ Remove last", key="cons_rem") and st.session_state.num_items > 1:
            st.session_state.num_items -= 1
            st.rerun()

    with st.expander("🏪 Competitor prices (optional)"):
        _render_competitor_table(key_prefix="cons_")

    st.markdown("---")
    run_col, _ = st.columns([2, 6])
    with run_col:
        run_clicked = st.button("🚀 Run audit", type="primary",
                                use_container_width=True, key="cons_run")

    if run_clicked:
        items_raw = [st.session_state.menu_items[i] for i in range(st.session_state.num_items)]
        active = [it for it in items_raw if it.get("name", "").strip()]
        if not active:
            st.error("Please enter at least one menu item.")
            return

        def _parse_comp(v):
            try:
                f = float(str(v).replace(",", "."))
                return f if f > 0 else None
            except (ValueError, TypeError):
                return None

        item_inputs = [
            ItemInput(
                name=it["name"].strip(),
                category=it["category"], role=it["role"],
                cost=float(it["cost"]), price=float(it["price"]),
                monthly_units=int(it["monthly_units"]),
                comp1=_parse_comp(it["comp1"]),
                comp2=_parse_comp(it["comp2"]),
                comp3=_parse_comp(it["comp3"]),
            )
            for it in active
        ]
        s = st.session_state.settings
        settings_input = SettingsInput(
            currency=s["currency"], round_to=float(s["round_to"]),
            ending=s["ending"], max_raise=float(s["max_raise"]),
            max_cut=float(s["max_cut"]), shr_high=float(s["shr_high"]),
            shr_med=float(s["shr_med"]), shr_low=float(s["shr_low"]),
            demo_mode=s["demo_mode"],
        )

        with st.spinner("Running model…"):
            result, error = run_audit(settings_input, item_inputs)
            if error:
                st.error(f"Audit failed: {error}")
                return
            st.session_state.audit_result = result
            st.session_state.audit_currency = s["currency"]
            save_submission(
                email="consultant", mode="consultant",
                currency=s["currency"], items=item_inputs, audit=result,
                cafe_name=cafe, newsletter_opt_in=False,
            )
            if _email_configured():
                try:
                    send_consultant_notification(
                        owner_email="(consultant test run)",
                        currency=s["currency"], items=item_inputs,
                        audit=result,
                        app_url=os.environ.get("APP_URL", "https://share.streamlit.io"),
                        excel_path=result.excel_path,
                        cafe_name=cafe,
                    )
                except Exception:
                    pass
            st.success("✓ Audit complete. Switch to the Results tab.")


def _consultant_results_tab():
    audit: AuditResult | None = st.session_state.get("audit_result")
    currency = st.session_state.get("audit_currency", "USD")
    cafe_name = st.session_state.get("audit_cafe_name", "")

    if audit is None:
        st.info("Run the audit first (Input tab).")
        return

    if audit.banner:
        st.markdown(f'<div class="qa-banner">⚠ {audit.banner}</div>', unsafe_allow_html=True)

    # Headline metrics
    lift_sign = "+" if audit.monthly_lift >= 0 else ""
    lift_str = f"{lift_sign}{_currency_display(audit.monthly_lift, currency)}"
    pct_str = _pct_display(audit.lift_pct)
    conf = audit.confidence

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">Monthly Δ Profit</div>
          <div class="value">{lift_str}</div>
          <div class="sub">{currency} · {pct_str}</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        bg = {"HIGH": "#d9f2d9", "MEDIUM": "#fff2cc", "LOW": "#fce4d6"}.get(conf, "#f8f8f8")
        tc = {"HIGH": "#1a5e1a", "MEDIUM": "#6b4e00", "LOW": "#7e2e00"}.get(conf, "#333")
        st.markdown(f"""
        <div class="metric-card" style="background:{bg}">
          <div class="label" style="color:{tc}">Confidence</div>
          <div class="value" style="color:{tc}">{conf}</div>
          <div class="sub" style="color:{tc}">weighted</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">Items changing</div>
          <div class="value" style="font-size:20px">{audit.changes_count}</div>
          <div class="sub">recommendations</div>
        </div>""", unsafe_allow_html=True)
    with m4:
        best = audit.best_item.replace("Best item: ", "") if audit.best_item else "—"
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">Best item</div>
          <div class="value" style="font-size:16px">{best}</div>
          <div class="sub">highest Δ profit</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Per-item table
    st.markdown('<div class="section-head">Per-Item Recommendations</div>', unsafe_allow_html=True)
    if audit.items:
        rows = []
        for item in audit.items:
            dp_sign = "+" if item.delta_profit_mo >= 0 else ""
            rows.append({
                "Item": item.name,
                "Action": item.action,
                f"From ({currency})": _currency_display(item.price_from, currency),
                f"To ({currency})": _currency_display(item.price_to, currency),
                "Δ%": _pct_display(item.delta_pct),
                "Δ Profit/mo": f"{dp_sign}{_currency_display(item.delta_profit_mo, currency)}",
                "Quadrant": item.quadrant,
                "Market": item.market,
                "Confidence": item.confidence,
                "Narrative": item.narrative,
            })
        df = pd.DataFrame(rows)
        st.markdown(_render_results_table(df), unsafe_allow_html=True)

    # Sensitivity
    st.markdown('<div class="section-head">Sensitivity</div>', unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns(3)
    for col, (label, val, is_base) in zip(
        [sc1, sc2, sc3],
        [("Conservative (e×1.2)", audit.sens_conservative, False),
         ("Baseline (e×1.0)", audit.sens_baseline, True),
         ("Optimistic (e×0.8)", audit.sens_optimistic, False)]):
        border = "2px solid #1F3864" if is_base else "1px solid #dde3ee"
        color = "#006100" if val >= 0 else "#c00000"
        sign = "+" if val >= 0 else ""
        col.markdown(f"""
        <div style="border:{border};border-radius:8px;padding:14px;text-align:center;background:white">
          <div style="font-size:11px;color:#7a8599">{label}</div>
          <div style="font-size:22px;font-weight:800;color:{color}">{sign}{_currency_display(val, currency)} {currency}</div>
        </div>""", unsafe_allow_html=True)

    rob_bg = "#d9f2d9" if "YES" in (audit.sens_robust or "") else "#fce3e3"
    rob_tc = "#1a5e1a" if "YES" in (audit.sens_robust or "") else "#7e0000"
    st.markdown(f"""
    <div style="background:{rob_bg};color:{rob_tc};border-radius:8px;padding:10px 16px;
                margin-top:10px;font-weight:600;font-size:13px">
      Recommendation robust? {audit.sens_robust or "—"}
    </div>""", unsafe_allow_html=True)

    # QA
    with st.expander("🔍 QA Summary"):
        qc1, qc2, qc3 = st.columns(3)
        ready_bg = "#d9f2d9" if audit.qa_hard_fails == 0 else "#fce3e3"
        ready_tc = "#1a5e1a" if audit.qa_hard_fails == 0 else "#7e0000"
        qc1.markdown(f"""
        <div style="background:{ready_bg};color:{ready_tc};border-radius:8px;
                    padding:10px;font-weight:700;text-align:center">
          {audit.qa_ready or ('✓ Ready' if audit.qa_hard_fails == 0 else '✗ Fix first')}
        </div>""", unsafe_allow_html=True)
        qc2.metric("Soft warnings", audit.qa_soft_warns)
        qc3.metric("Info", audit.qa_info_obs)

    # Downloads
    st.markdown('<div class="section-head">Downloads</div>', unsafe_allow_html=True)
    dl1, dl2, dl3, _ = st.columns([1.5, 1.5, 1.5, 4])

    if audit.excel_path and Path(audit.excel_path).exists():
        with open(audit.excel_path, "rb") as f:
            excel_bytes = f.read()
        with dl1:
            st.download_button(
                "📥 Excel (full)",
                data=excel_bytes,
                file_name=f"MarginLab_{cafe_name or 'Audit'}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with dl2:
            # Lite Excel
            try:
                from tempfile import NamedTemporaryFile
                lite_pw = None
                try:
                    lite_pw = st.secrets["EXCEL_LITE_PASSWORD"]
                except Exception:
                    lite_pw = os.environ.get("EXCEL_LITE_PASSWORD")
                with NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
                    lite_path = tf.name
                export_lite_excel(audit.excel_path, lite_path, protection_password=lite_pw)
                with open(lite_path, "rb") as f:
                    lite_bytes = f.read()
                st.download_button(
                    "📦 Excel (lite, locked)",
                    data=lite_bytes,
                    file_name=f"MarginLab_{cafe_name or 'Audit'}_lite.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    help="Hides all model sheets except OWNER_INPUTS and OWNER_RESULTS. For paid clients.",
                )
            except Exception as e:
                st.caption(f"Lite Excel: error ({e})")

    with dl3:
        pdf_bytes = generate_pdf(audit, currency, cafe_name,
                                  calendly_url=_calendly_url())
        if pdf_bytes:
            st.download_button(
                "📄 PDF report",
                data=pdf_bytes,
                file_name=f"MarginLab_{cafe_name or 'Audit'}_Report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            html_bytes = generate_html_report(audit, currency, cafe_name).encode("utf-8")
            st.download_button(
                "📄 HTML report",
                data=html_bytes,
                file_name=f"MarginLab_{cafe_name or 'Audit'}.html",
                mime="text/html",
                use_container_width=True,
            )


def _consultant_admin_tab():
    st.markdown('<div class="section-head">Submission History</div>', unsafe_allow_html=True)
    sheets_on = is_sheets_active()
    if sheets_on:
        st.success("📊 Google Sheets persistence is active")
    else:
        st.info("ℹ️ Using SQLite fallback (data wipes on redeploy). Configure Google Sheets in secrets for permanent storage.")

    rows = get_all_submissions(limit=200)
    if not rows:
        st.info("No submissions yet.")
        return

    df = pd.DataFrame(rows, columns=[
        "ID", "Date (UTC)", "Email", "Mode", "Currency",
        "Items", "Δ Profit", "Lift %", "Confidence", "Best Item",
        "Hard Fails", "Excel Path",
    ])
    df["Lift %"] = df["Lift %"].apply(lambda x: f"{x*100:.1f}%" if isinstance(x, (int, float)) else x)
    df["Δ Profit"] = df["Δ Profit"].apply(lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else x)

    fc1, fc2, _ = st.columns([2, 2, 5])
    with fc1:
        mode_filter = st.selectbox("Filter by mode", ["All", "owner", "consultant"])
    with fc2:
        conf_filter = st.selectbox("Filter by confidence", ["All", "HIGH", "MEDIUM", "LOW"])

    display_df = df.copy()
    if mode_filter != "All":
        display_df = display_df[display_df["Mode"] == mode_filter]
    if conf_filter != "All":
        display_df = display_df[display_df["Confidence"] == conf_filter]

    st.dataframe(display_df.drop(columns=["Excel Path"]), use_container_width=True, hide_index=True)
    st.caption(f"Total submissions: {len(rows)}")


# ── shared widgets ────────────────────────────────────────────────────────────

def _render_menu_table(currency, key_prefix=""):
    h_cols = st.columns([3, 2, 2, 1.5, 1.5, 1.5])
    for col, label in zip(h_cols, ["Item name", "Category", "Role",
                                    f"Cost ({currency})", f"Price ({currency})", "Units/mo"]):
        col.markdown(f"**{label}**")

    n_items = st.session_state.num_items
    for i in range(n_items):
        try:
            item = st.session_state.menu_items[i]
            if not isinstance(item, dict):
                raise ValueError("not a dict")
        except (IndexError, ValueError, TypeError, KeyError):
            cur = list(st.session_state.menu_items) if isinstance(st.session_state.menu_items, list) else []
            while len(cur) < 30:
                cur.append(_blank_item())
            st.session_state.menu_items = cur
            item = st.session_state.menu_items[i]

        c1, c2, c3, c4, c5, c6 = st.columns([3, 2, 2, 1.5, 1.5, 1.5])
        with c1:
            new_val = st.text_input(f"{key_prefix}name_{i}", value=item["name"],
                label_visibility="collapsed", placeholder=f"Item {i+1}")
            if new_val != item["name"] and not st.session_state.form_started_tracked:
                track("form_started")
                st.session_state.form_started_tracked = True
            item["name"] = new_val
        with c2:
            cat_idx = CATEGORIES.index(item["category"]) if item["category"] in CATEGORIES else 0
            item["category"] = st.selectbox(f"{key_prefix}cat_{i}", CATEGORIES,
                index=cat_idx, label_visibility="collapsed")
        with c3:
            role_idx = ROLES.index(item["role"]) if item["role"] in ROLES else 1
            item["role"] = st.selectbox(f"{key_prefix}role_{i}", ROLES,
                index=role_idx, label_visibility="collapsed")
        with c4:
            item["cost"] = st.number_input(f"{key_prefix}cost_{i}", min_value=0.0,
                value=float(item["cost"]), step=0.10, format="%.2f",
                label_visibility="collapsed")
        with c5:
            item["price"] = st.number_input(f"{key_prefix}price_{i}", min_value=0.0,
                value=float(item["price"]), step=0.10, format="%.2f",
                label_visibility="collapsed")
        with c6:
            item["monthly_units"] = st.number_input(f"{key_prefix}units_{i}",
                min_value=0, value=int(item["monthly_units"]), step=50,
                label_visibility="collapsed")
        st.session_state.menu_items[i] = item


def _render_competitor_table(key_prefix=""):
    h = st.columns([3, 1.5, 1.5, 1.5])
    h[0].markdown("**Item**")
    h[1].markdown("**Competitor 1**")
    h[2].markdown("**Competitor 2**")
    h[3].markdown("**Competitor 3**")
    n_items = st.session_state.num_items
    for i in range(n_items):
        try:
            item = st.session_state.menu_items[i]
            if not isinstance(item, dict):
                raise ValueError("not a dict")
        except (IndexError, ValueError, TypeError, KeyError):
            cur = list(st.session_state.menu_items) if isinstance(st.session_state.menu_items, list) else []
            while len(cur) < 30:
                cur.append(_blank_item())
            st.session_state.menu_items = cur
            item = st.session_state.menu_items[i]

        c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1.5])
        c1.write(item["name"] or f"Item {i+1}")
        item["comp1"] = c2.text_input(f"{key_prefix}cp1_{i}", value=str(item["comp1"]),
            label_visibility="collapsed", placeholder="—")
        item["comp2"] = c3.text_input(f"{key_prefix}cp2_{i}", value=str(item["comp2"]),
            label_visibility="collapsed", placeholder="—")
        item["comp3"] = c4.text_input(f"{key_prefix}cp3_{i}", value=str(item["comp3"]),
            label_visibility="collapsed", placeholder="—")
        st.session_state.menu_items[i] = item


def _render_results_table(df: pd.DataFrame) -> str:
    headers = "".join(
        f"<th style='background:#1F3864;color:white;padding:7px 10px;text-align:left;white-space:nowrap'>{c}</th>"
        for c in df.columns
    )
    body = ""
    for _, row in df.iterrows():
        cells = ""
        for col, val in row.items():
            if col == "Action":
                cls = {"Raise": "act-raise", "Cut": "act-cut"}.get(str(val), "act-hold")
                cell = f'<span class="{cls}">{val}</span>'
            elif col == "Quadrant":
                cls = {"Star":"q-Star","Plowhorse":"q-Plowhorse","Puzzle":"q-Puzzle","Dog":"q-Dog"}.get(str(val),"m-No")
                cell = f'<span class="chip {cls}">{val}</span>'
            elif col == "Market":
                cls = {"Above market":"m-Above","Within market":"m-Within","Below market":"m-Below"}.get(str(val),"m-No")
                cell = f'<span class="chip {cls}">{val}</span>'
            elif col == "Confidence":
                colors = {"HIGH":"#d9f2d9;color:#1a5e1a","MEDIUM":"#fff2cc;color:#6b4e00","LOW":"#fce4d6;color:#7e2e00"}
                bg = colors.get(str(val), "#f0f0f0;color:#555")
                cell = f'<span class="chip" style="background:{bg}">{val}</span>'
            elif col == "Narrative":
                cell = f'<span style="font-size:12px;color:#555">{val}</span>'
            else:
                cell = str(val)
            cells += f"<td style='padding:6px 10px;border-bottom:1px solid #eef0f4;vertical-align:middle'>{cell}</td>"
        body += f"<tr style='background:white'>{cells}</tr>"
    return f"<table style='width:100%;border-collapse:collapse;font-size:13px'><thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table>"


# ══════════════════════════════════════════════════════════════════════════════
# ROUTING
# ══════════════════════════════════════════════════════════════════════════════

# Query param override (e.g. ?view=consultant)
try:
    qp = st.query_params
    if "view" in qp:
        requested = qp["view"]
        if requested in ("landing", "owner_audit", "consultant"):
            st.session_state.view = requested
except Exception:
    pass


view = st.session_state.view
if view == "landing":
    render_landing()
elif view == "owner_audit":
    render_owner_audit()
elif view == "consultant":
    render_consultant()
else:
    st.session_state.view = "landing"
    st.rerun()
