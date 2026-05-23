"""
app.py — MarginLab Pricing Lab · Streamlit front-end
Two modes: Quick Audit (owner self-serve) + Consultant View (password-gated)
"""

import os
import io
import shutil
import streamlit as st
import pandas as pd
from pathlib import Path

from engine import (
    run_audit, SettingsInput, ItemInput, AuditResult,
    CATEGORIES, ROLES, CURRENCIES, ROUND_STEPS, ENDINGS,
)
from db import save_submission, get_all_submissions, get_submission_inputs
from pdf_report import generate_pdf, generate_html_report

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
  /* Header */
  .ml-header {
    background: linear-gradient(135deg, #1F3864 0%, #2d5090 100%);
    color: white;
    padding: 20px 28px 14px;
    border-radius: 10px;
    margin-bottom: 24px;
  }
  .ml-header h1 { margin:0; font-size:28px; font-weight:800; letter-spacing:-0.5px; }
  .ml-header p  { margin:4px 0 0; opacity:0.85; font-size:14px; }

  /* Metric cards */
  .metric-card {
    background: white;
    border: 1px solid #e0e6f0;
    border-radius: 10px;
    padding: 18px 20px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(31,56,100,0.06);
  }
  .metric-card .label { font-size:11px; color:#7a8599; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px; }
  .metric-card .value { font-size:30px; font-weight:800; color:#1F3864; }
  .metric-card .sub   { font-size:12px; color:#9aa5b8; margin-top:2px; }

  /* Banner */
  .qa-banner {
    background: #c00000;
    color: white;
    padding: 12px 18px;
    border-radius: 8px;
    font-weight: 600;
    margin-bottom: 16px;
    font-size: 14px;
  }

  /* Confidence badge */
  .badge-HIGH   { background:#d9f2d9; color:#1a5e1a; }
  .badge-MEDIUM { background:#fff2cc; color:#6b4e00; }
  .badge-LOW    { background:#fce4d6; color:#7e2e00; }
  .badge { padding: 3px 10px; border-radius: 5px; font-size: 12px; font-weight: 600; display:inline-block; }

  /* Quadrant / market chips in table */
  .chip { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; display:inline-block; }
  .q-Star       { background:#d9f2d9; color:#1a5e1a; }
  .q-Plowhorse  { background:#d9e1f2; color:#1f3864; }
  .q-Puzzle     { background:#fce4d6; color:#7e2e00; }
  .q-Dog        { background:#fce3e3; color:#7e0000; }
  .m-Above      { background:#fce3e3; color:#7e0000; }
  .m-Within     { background:#d9f2d9; color:#1a5e1a; }
  .m-Below      { background:#fff2cc; color:#6b4e00; }
  .m-No         { background:#f0f0f0; color:#555; }

  /* Action colors */
  .act-raise { color: #006100; font-weight: 700; }
  .act-cut   { color: #c00000; font-weight: 700; }
  .act-hold  { color: #555; font-weight: 700; }

  /* Sensitivity cards */
  .sens-card {
    border: 1px solid #dde3ee;
    border-radius: 8px;
    padding: 14px;
    text-align: center;
    background: white;
  }
  .sens-card.baseline { border: 2px solid #1F3864; }
  .sens-label { font-size:11px; color:#7a8599; margin-bottom:4px; }
  .sens-val   { font-size:22px; font-weight:800; }
  .pos { color: #006100; }
  .neg { color: #c00000; }

  /* Section headers */
  .section-head {
    color: #1F3864;
    font-size: 16px;
    font-weight: 700;
    border-bottom: 2px solid #1F3864;
    padding-bottom: 4px;
    margin: 20px 0 10px;
  }

  /* Mode selector */
  .stSelectbox > div > div { border-radius: 8px; }

  /* Input table row */
  div[data-testid="stHorizontalBlock"] { align-items: flex-end; }

  /* Hide default streamlit chrome */
  footer { display: none !important; }
  #MainMenu { visibility: hidden; }
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

def _chip(text: str, kind: str) -> str:
    css_map = {
        "Star": "q-Star", "Plowhorse": "q-Plowhorse", "Puzzle": "q-Puzzle", "Dog": "q-Dog",
        "Above market": "m-Above", "Within market": "m-Within",
        "Below market": "m-Below", "No comp data": "m-No",
    }
    cls = css_map.get(text, "m-No")
    return f'<span class="chip {cls}">{text}</span>'

def _action_span(action: str) -> str:
    cls = {"Raise": "act-raise", "Cut": "act-cut"}.get(action, "act-hold")
    return f'<span class="{cls}">{action}</span>'


# ── session state init ─────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "mode": "Quick Audit",
        "consultant_auth": False,
        "audit_result": None,
        "audit_currency": "USD",
        "audit_cafe_name": "",
        "email_submitted": False,
        "pending_email": "",
        "num_items": 6,
        "items": [
            {"name": "", "category": "Coffee", "role": "Core",
             "cost": 0.0, "price": 0.0, "monthly_units": 0,
             "comp1": "", "comp2": "", "comp3": ""}
            for _ in range(30)
        ],
        "show_comp": False,
        "settings": {
            "currency": "USD", "round_to": 0.10, "ending": ".00",
            "max_raise": 0.10, "max_cut": -0.05,
            "shr_high": 1.0, "shr_med": 0.5, "shr_low": 0.25,
            "demo_mode": "No",
        },
        "active_tab": "Input",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# ── HEADER ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="ml-header">
  <h1>📊 MarginLab Pricing Lab</h1>
  <p>Economic menu pricing · Powered by Lerner-optimal demand modelling</p>
</div>
""", unsafe_allow_html=True)


# ── MODE SELECTOR ──────────────────────────────────────────────────────────────

col_mode, col_pw, col_spacer = st.columns([2, 2, 5])
with col_mode:
    mode = st.selectbox(
        "Mode", ["Quick Audit", "Consultant View"],
        index=0 if st.session_state.mode == "Quick Audit" else 1,
        label_visibility="collapsed",
    )
    st.session_state.mode = mode

if mode == "Consultant View" and not st.session_state.consultant_auth:
    with col_pw:
        pw = st.text_input("Consultant password", type="password", label_visibility="collapsed",
                           placeholder="Consultant password")
        if pw:
            correct = os.environ.get("CONSULTANT_PASSWORD", "marginlab2024")
            if pw == correct:
                st.session_state.consultant_auth = True
                st.rerun()
            else:
                st.error("Wrong password")

if mode == "Consultant View" and not st.session_state.consultant_auth:
    st.info("Enter the consultant password above to access the full view.")
    st.stop()


# ── TABS ───────────────────────────────────────────────────────────────────────

is_consultant = mode == "Consultant View" and st.session_state.consultant_auth

if is_consultant:
    tabs = st.tabs(["📝 Input", "📊 Results", "🗂 Admin"])
else:
    tabs = st.tabs(["📝 Your Menu", "📊 Results"])

tab_input   = tabs[0]
tab_results = tabs[1]
tab_admin   = tabs[2] if is_consultant else None


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — INPUT
# ══════════════════════════════════════════════════════════════════════════════

with tab_input:
    # ── Settings bar ──────────────────────────────────────────────────────────
    with st.container():
        if is_consultant:
            st.markdown('<div class="section-head">Settings</div>', unsafe_allow_html=True)
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            with sc1:
                cur = st.selectbox("Currency", CURRENCIES,
                    index=CURRENCIES.index(st.session_state.settings["currency"]))
                st.session_state.settings["currency"] = cur
            with sc2:
                rnd_opts = [str(x) for x in ROUND_STEPS]
                rnd_val = str(st.session_state.settings["round_to"])
                rnd_idx = rnd_opts.index(rnd_val) if rnd_val in rnd_opts else 2
                rnd = st.selectbox("Round to", ROUND_STEPS, index=rnd_idx)
                st.session_state.settings["round_to"] = rnd
            with sc3:
                end_idx = ENDINGS.index(st.session_state.settings["ending"])
                ending = st.selectbox("Charm ending", ENDINGS, index=end_idx)
                st.session_state.settings["ending"] = ending
            with sc4:
                demo = st.selectbox("Demo mode", ["No", "Yes"],
                    index=0 if st.session_state.settings["demo_mode"] == "No" else 1)
                st.session_state.settings["demo_mode"] = demo
            with sc5:
                st.write("")

            with st.expander("Guardrails & shrinkage"):
                ga, gb, gc, gd, ge = st.columns(5)
                with ga:
                    mr = st.number_input("Max raise", 0.0, 0.5,
                        st.session_state.settings["max_raise"], 0.01, format="%.2f")
                    st.session_state.settings["max_raise"] = mr
                with gb:
                    mc = st.number_input("Max cut", -0.5, 0.0,
                        st.session_state.settings["max_cut"], 0.01, format="%.2f")
                    st.session_state.settings["max_cut"] = mc
                with gc:
                    sh = st.number_input("Shrink HIGH", 0.0, 1.0,
                        st.session_state.settings["shr_high"], 0.05, format="%.2f")
                    st.session_state.settings["shr_high"] = sh
                with gd:
                    sm = st.number_input("Shrink MED", 0.0, 1.0,
                        st.session_state.settings["shr_med"], 0.05, format="%.2f")
                    st.session_state.settings["shr_med"] = sm
                with ge:
                    sl = st.number_input("Shrink LOW", 0.0, 1.0,
                        st.session_state.settings["shr_low"], 0.05, format="%.2f")
                    st.session_state.settings["shr_low"] = sl
        else:
            # Quick audit — just currency
            qc1, qc2 = st.columns([1, 5])
            with qc1:
                cur = st.selectbox("Currency", CURRENCIES,
                    index=CURRENCIES.index(st.session_state.settings["currency"]))
                st.session_state.settings["currency"] = cur

    currency = st.session_state.settings["currency"]

    # ── Café name (owner mode) ─────────────────────────────────────────────────
    if not is_consultant:
        cafe_name = st.text_input("Your café name (optional)", placeholder="e.g. The Daily Grind")
        st.session_state.audit_cafe_name = cafe_name

    # ── Menu table ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-head">Your Menu</div>', unsafe_allow_html=True)

    if not is_consultant:
        st.caption("Enter your menu items below. You need at least: name, cost, current price, and monthly units sold.")

    # Header row
    h_cols = st.columns([3, 2, 2, 1.5, 1.5, 1.5])
    for col, label in zip(h_cols, ["Item name", "Category", "Role", f"Cost ({currency})", f"Price ({currency})", "Units/mo"]):
        col.markdown(f"**{label}**")

    n_items = st.session_state.num_items
    for i in range(n_items):
        item = st.session_state.items[i]
        c1, c2, c3, c4, c5, c6 = st.columns([3, 2, 2, 1.5, 1.5, 1.5])
        with c1:
            item["name"] = st.text_input(f"name_{i}", value=item["name"],
                label_visibility="collapsed", placeholder=f"Item {i+1}")
        with c2:
            cat_idx = CATEGORIES.index(item["category"]) if item["category"] in CATEGORIES else 0
            item["category"] = st.selectbox(f"cat_{i}", CATEGORIES, index=cat_idx, label_visibility="collapsed")
        with c3:
            role_idx = ROLES.index(item["role"]) if item["role"] in ROLES else 1
            item["role"] = st.selectbox(f"role_{i}", ROLES, index=role_idx, label_visibility="collapsed")
        with c4:
            item["cost"] = st.number_input(f"cost_{i}", min_value=0.0, value=float(item["cost"]),
                step=0.10, format="%.2f", label_visibility="collapsed")
        with c5:
            item["price"] = st.number_input(f"price_{i}", min_value=0.0, value=float(item["price"]),
                step=0.10, format="%.2f", label_visibility="collapsed")
        with c6:
            item["monthly_units"] = st.number_input(f"units_{i}", min_value=0, value=int(item["monthly_units"]),
                step=50, label_visibility="collapsed")
        st.session_state.items[i] = item

    # Add/remove item buttons
    btn_c1, btn_c2, _ = st.columns([1, 1, 7])
    with btn_c1:
        if st.button("＋ Add item") and st.session_state.num_items < 30:
            st.session_state.num_items += 1
            st.rerun()
    with btn_c2:
        if st.button("－ Remove last") and st.session_state.num_items > 1:
            st.session_state.num_items -= 1
            st.rerun()

    # ── Competitor prices (optional expander) ──────────────────────────────────
    with st.expander("🏪 Add competitor prices (optional)"):
        st.caption("Enter prices from up to 3 nearby cafés for the items you want to benchmark. Leave blank to skip.")
        h2cols = st.columns([3, 1.5, 1.5, 1.5])
        h2cols[0].markdown("**Item**")
        h2cols[1].markdown("**Competitor 1**")
        h2cols[2].markdown("**Competitor 2**")
        h2cols[3].markdown("**Competitor 3**")
        for i in range(n_items):
            item = st.session_state.items[i]
            name_disp = item["name"] or f"Item {i+1}"
            cc1, cc2, cc3, cc4 = st.columns([3, 1.5, 1.5, 1.5])
            cc1.write(name_disp)
            item["comp1"] = cc2.text_input(f"cp1_{i}", value=str(item["comp1"]),
                label_visibility="collapsed", placeholder="—")
            item["comp2"] = cc3.text_input(f"cp2_{i}", value=str(item["comp2"]),
                label_visibility="collapsed", placeholder="—")
            item["comp3"] = cc4.text_input(f"cp3_{i}", value=str(item["comp3"]),
                label_visibility="collapsed", placeholder="—")
            st.session_state.items[i] = item

    # ── Run button ─────────────────────────────────────────────────────────────
    st.markdown("---")
    run_col, _ = st.columns([2, 6])
    with run_col:
        run_clicked = st.button("🚀 Run Pricing Audit", type="primary", use_container_width=True)

    if run_clicked:
        # Gather active items (name must be filled)
        items_raw = [st.session_state.items[i] for i in range(n_items)]
        active_items = [it for it in items_raw if it["name"].strip()]

        if not active_items:
            st.error("Please enter at least one item name before running the audit.")
        else:
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
                for it in active_items
            ]

            s = st.session_state.settings
            settings_input = SettingsInput(
                currency=s["currency"],
                round_to=float(s["round_to"]),
                ending=s["ending"],
                max_raise=float(s["max_raise"]),
                max_cut=float(s["max_cut"]),
                shr_high=float(s["shr_high"]),
                shr_med=float(s["shr_med"]),
                shr_low=float(s["shr_low"]),
                demo_mode=s["demo_mode"],
            )

            with st.spinner("Running model… (this takes ~10 seconds)"):
                result, error = run_audit(settings_input, item_inputs)

            if error:
                st.error(f"Audit failed: {error}")
            else:
                st.session_state.audit_result = result
                st.session_state.audit_currency = s["currency"]
                st.session_state.email_submitted = is_consultant  # consultant skips email gate
                st.session_state._pending_items = item_inputs  # keep for DB save

                # Save to DB (consultant saves immediately; owner after email)
                if is_consultant:
                    save_submission(
                        email="consultant",
                        mode="consultant",
                        currency=s["currency"],
                        items=item_inputs,
                        audit=result,
                    )
                st.success("✓ Audit complete! Switch to the Results tab.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — RESULTS
# ══════════════════════════════════════════════════════════════════════════════

with tab_results:
    audit: AuditResult | None = st.session_state.get("audit_result")
    currency = st.session_state.get("audit_currency", "USD")
    cafe_name = st.session_state.get("audit_cafe_name", "")

    if audit is None:
        st.info("Run the audit first (go to the Input tab and click 'Run Pricing Audit').")
        st.stop()

    # ── Email gate (owner mode only) ───────────────────────────────────────────
    if not is_consultant and not st.session_state.email_submitted:
        st.markdown("### Your results are ready! 🎉")
        st.write("Enter your email to unlock the full audit report. We'll also send you a copy.")
        em_col, btn_col = st.columns([3, 1])
        with em_col:
            email_val = st.text_input("Email address", placeholder="you@yourcafe.com",
                                       label_visibility="collapsed")
        with btn_col:
            if st.button("Unlock results", type="primary"):
                if "@" in email_val and "." in email_val:
                    st.session_state.email_submitted = True
                    st.session_state.pending_email = email_val
                    items_for_db = st.session_state.get("_pending_items", [])
                    save_submission(
                        email=email_val,
                        mode="owner",
                        currency=currency,
                        items=items_for_db,
                        audit=audit,
                    )
                    st.rerun()
                else:
                    st.error("Please enter a valid email address.")
        st.stop()

    # ── DATA QUALITY BANNER ────────────────────────────────────────────────────
    if audit.banner:
        st.markdown(f'<div class="qa-banner">⚠ {audit.banner}</div>', unsafe_allow_html=True)

    # ── HEADLINE METRICS ───────────────────────────────────────────────────────
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
          <div class="sub">{currency} · {pct_str} vs baseline</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        conf_bg = {"HIGH": "#d9f2d9", "MEDIUM": "#fff2cc", "LOW": "#fce4d6"}.get(conf, "#f8f8f8")
        conf_tc = {"HIGH": "#1a5e1a", "MEDIUM": "#6b4e00", "LOW": "#7e2e00"}.get(conf, "#333")
        st.markdown(f"""
        <div class="metric-card" style="background:{conf_bg}">
          <div class="label" style="color:{conf_tc}">Confidence</div>
          <div class="value" style="color:{conf_tc}">{conf}</div>
          <div class="sub" style="color:{conf_tc}">overall weighted</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">Items changing</div>
          <div class="value" style="font-size:22px">{audit.changes_count}</div>
          <div class="sub">price recommendations</div>
        </div>""", unsafe_allow_html=True)
    with m4:
        best_name = audit.best_item.replace("Best item: ", "") if audit.best_item else "—"
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">Best opportunity</div>
          <div class="value" style="font-size:18px">{best_name}</div>
          <div class="sub">highest Δ profit</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PER-ITEM TABLE ─────────────────────────────────────────────────────────
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
                f"Δ Profit/mo": f"{dp_sign}{_currency_display(item.delta_profit_mo, currency)}",
                "Quadrant": item.quadrant,
                "Market": item.market,
                "Narrative": item.narrative,
            })
            if is_consultant:
                rows[-1]["Confidence"] = item.confidence
                rows[-1]["Phase"] = item.phase

        df = pd.DataFrame(rows)

        # Render as HTML table with chips
        def render_table(df: pd.DataFrame) -> str:
            headers = "".join(f"<th style='background:#1F3864;color:white;padding:7px 10px;text-align:left;white-space:nowrap'>{c}</th>" for c in df.columns)
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
                        cls = f"badge-{val}" if val in ("HIGH","MEDIUM","LOW") else ""
                        cell = f'<span class="badge {cls}">{val}</span>'
                    elif col == "Narrative":
                        cell = f'<span style="font-size:12px;color:#555">{val}</span>'
                    else:
                        cell = str(val)
                    cells += f"<td style='padding:6px 10px;border-bottom:1px solid #eef0f4;vertical-align:middle'>{cell}</td>"
                body += f"<tr style='background:white'>{cells}</tr>"
            return f"<table style='width:100%;border-collapse:collapse;font-size:13px'><thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table>"

        st.markdown(render_table(df), unsafe_allow_html=True)
    else:
        st.warning("No item results returned. Check that your menu items have names and prices.")

    # ── SENSITIVITY ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-head">Sensitivity Check</div>', unsafe_allow_html=True)

    sc1, sc2, sc3 = st.columns(3)
    def _sens_card(col, label, val, currency, is_base=False):
        base_class = "sens-card baseline" if is_base else "sens-card"
        val_class = "pos" if val >= 0 else "neg"
        sign = "+" if val >= 0 else ""
        col.markdown(f"""
        <div class="{base_class}">
          <div class="sens-label">{label}</div>
          <div class="sens-val {val_class}">{sign}{_currency_display(val, currency)} {currency}</div>
        </div>""", unsafe_allow_html=True)

    _sens_card(sc1, "Conservative (e×1.2)", audit.sens_conservative, currency)
    _sens_card(sc2, "Baseline (e×1.0)", audit.sens_baseline, currency, is_base=True)
    _sens_card(sc3, "Optimistic (e×0.8)", audit.sens_optimistic, currency)

    rob_bg = "#d9f2d9" if "YES" in (audit.sens_robust or "") else "#fce3e3"
    rob_tc = "#1a5e1a" if "YES" in (audit.sens_robust or "") else "#7e0000"
    st.markdown(f"""
    <div style="background:{rob_bg};color:{rob_tc};border-radius:8px;padding:10px 16px;
                margin-top:10px;font-weight:600;font-size:13px">
        Recommendation robust? {audit.sens_robust or "—"}
    </div>""", unsafe_allow_html=True)

    # ── QA SUMMARY (consultant only) ───────────────────────────────────────────
    if is_consultant:
        with st.expander("🔍 QA Summary", expanded=False):
            qa_c1, qa_c2, qa_c3 = st.columns(3)
            ready_bg = "#d9f2d9" if audit.qa_hard_fails == 0 else "#fce3e3"
            ready_tc = "#1a5e1a" if audit.qa_hard_fails == 0 else "#7e0000"
            qa_c1.markdown(f"""
            <div style="background:{ready_bg};color:{ready_tc};border-radius:8px;
                        padding:10px 14px;font-weight:700;text-align:center">
                {audit.qa_ready or ('✓ Ready to deliver' if audit.qa_hard_fails == 0 else '✗ Fix before delivery')}
            </div>""", unsafe_allow_html=True)
            qa_c2.metric("Soft warnings", audit.qa_soft_warns)
            qa_c3.metric("Info observations", audit.qa_info_obs)

    # ── DOWNLOADS ──────────────────────────────────────────────────────────────
    st.markdown('<div class="section-head">Downloads</div>', unsafe_allow_html=True)

    dl1, dl2, dl3, _ = st.columns([1.5, 1.5, 1.5, 4])

    # Excel download
    if audit.excel_path and Path(audit.excel_path).exists():
        with open(audit.excel_path, "rb") as f:
            excel_bytes = f.read()
        with dl1:
            st.download_button(
                "📥 Download Excel",
                data=excel_bytes,
                file_name="MarginLab_Audit.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    # PDF download
    with dl2:
        pdf_bytes = generate_pdf(audit, currency, cafe_name)
        if pdf_bytes:
            st.download_button(
                "📄 Download PDF Report",
                data=pdf_bytes,
                file_name="MarginLab_Audit_Report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            # Fallback: download HTML report
            html_bytes = generate_html_report(audit, currency, cafe_name).encode("utf-8")
            st.download_button(
                "📄 Download HTML Report",
                data=html_bytes,
                file_name="MarginLab_Audit_Report.html",
                mime="text/html",
                use_container_width=True,
            )

    # Re-run button
    with dl3:
        if st.button("🔄 Start new audit", use_container_width=True):
            st.session_state.audit_result = None
            st.session_state.email_submitted = False
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ADMIN (consultant only)
# ══════════════════════════════════════════════════════════════════════════════

if tab_admin is not None:
    with tab_admin:
        st.markdown('<div class="section-head">Submission History</div>', unsafe_allow_html=True)

        rows = get_all_submissions(limit=200)
        if not rows:
            st.info("No submissions yet.")
        else:
            df = pd.DataFrame(rows, columns=[
                "ID", "Date (UTC)", "Email", "Mode", "Currency",
                "Items", "Δ Profit", "Lift %", "Confidence", "Best Item",
                "Hard Fails", "Excel Path",
            ])
            df["Lift %"] = df["Lift %"].apply(lambda x: f"{x*100:.1f}%")
            df["Δ Profit"] = df["Δ Profit"].apply(lambda x: f"{x:,.2f}")

            # Filters
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

            st.dataframe(
                display_df.drop(columns=["Excel Path"]),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown(f"**Total submissions:** {len(rows)}")

            # Download any submission's Excel
            st.markdown("#### Download a submission's Excel")
            sel_id = st.number_input("Submission ID", min_value=1, step=1)
            if st.button("Download"):
                row = get_submission_inputs(int(sel_id))
                if row:
                    _, excel_path = row
                    if excel_path and Path(excel_path).exists():
                        with open(excel_path, "rb") as f:
                            st.download_button(
                                "📥 Excel file",
                                data=f.read(),
                                file_name=f"submission_{sel_id}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                    else:
                        st.warning("Excel file for this submission no longer exists on disk.")
                else:
                    st.error("Submission ID not found.")
