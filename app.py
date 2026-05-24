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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700;9..144,800&family=Geist:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
  /* ════════════════════════════════════════════════════════════════
     MARGINLAB · Design System v3
     Premium-but-warm: ink navy, cream, single ochre accent
     ════════════════════════════════════════════════════════════════ */

  :root {
    --ink:        #0F1A2E;
    --ink-soft:   #1F2A40;
    --ink-mid:    #3D4862;
    --slate:      #6B7588;
    --slate-soft: #9AA3B5;
    --line:       #E5E0D4;
    --line-soft:  #EFEAE0;
    --cream:      #FAF7F2;
    --cream-deep: #F2EDE3;
    --paper:      #FDFCF9;
    --ochre:      #B8935C;
    --ochre-deep: #9A7842;
    --ochre-soft: #E8DCC4;
    --green:      #4A6B4A;
    --green-soft: #DDE6DC;
    --rust:       #9C4A3C;
    --rust-soft:  #F0D9D4;

    --shadow-sm: 0 1px 2px rgba(15, 26, 46, 0.04);
    --shadow:    0 2px 6px rgba(15, 26, 46, 0.06), 0 1px 2px rgba(15, 26, 46, 0.04);
    --shadow-lg: 0 12px 32px rgba(15, 26, 46, 0.08), 0 4px 12px rgba(15, 26, 46, 0.04);
  }

  /* ── App-wide reset ────────────────────────────────────────── */
  .stApp {
    background: var(--cream) !important;
  }

  html, body, [class*="css"], .stMarkdown, p, span, div, button, input, label {
    font-family: "Geist", -apple-system, BlinkMacSystemFont, sans-serif !important;
  }

  /* Streamlit chrome */
  footer { display: none !important; }
  #MainMenu { visibility: hidden !important; }
  header[data-testid="stHeader"] { background: transparent !important; }
  .block-container {
    padding-top: 1rem !important;
    padding-bottom: 4rem !important;
    max-width: 1180px !important;
  }

  /* ── Typography ───────────────────────────────────────────── */
  h1, h2, h3, h4, .serif {
    font-family: "Fraunces", "Times New Roman", Georgia, serif !important;
    font-feature-settings: "ss01", "ss02";
    letter-spacing: -0.02em;
  }
  .mono {
    font-family: "JetBrains Mono", "SF Mono", Menlo, monospace !important;
  }

  /* ────────────────────────────────────────────────────────────
     LANDING PAGE
     ──────────────────────────────────────────────────────────── */

  .landing-wrap {
    max-width: 1080px;
    margin: 0 auto;
    padding: 24px 32px 80px;
  }

  /* Top nav bar */
  .landing-nav {
    display: flex; justify-content: space-between; align-items: center;
    padding: 4px 0 32px;
    border-bottom: 1px solid var(--line);
    margin-bottom: 64px;
  }
  .nav-brand {
    display: flex; align-items: center; gap: 10px;
  }
  .nav-mark {
    width: 28px; height: 28px;
    background: var(--ink); color: var(--cream);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-family: "Fraunces", serif !important;
    font-weight: 700; font-size: 16px;
    font-style: italic;
  }
  .nav-name {
    font-family: "Fraunces", serif !important;
    font-weight: 600; font-size: 18px;
    color: var(--ink);
    letter-spacing: -0.01em;
  }
  .nav-tagline {
    color: var(--slate);
    font-size: 12px;
    letter-spacing: 0.02em;
  }

  /* Hero */
  .landing-hero {
    text-align: left;
    max-width: 760px;
    margin: 0 0 80px;
  }
  .hero-eyebrow {
    display: inline-flex;
    align-items: center; gap: 10px;
    color: var(--ochre-deep);
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 28px;
  }
  .hero-eyebrow::before {
    content: "";
    width: 24px; height: 1px;
    background: var(--ochre);
  }
  .landing-hero h1 {
    font-size: clamp(40px, 6vw, 68px);
    line-height: 1.02;
    font-weight: 500;
    color: var(--ink);
    margin: 0 0 28px;
    letter-spacing: -0.025em;
  }
  .landing-hero h1 em {
    font-style: italic;
    font-weight: 400;
    color: var(--ochre-deep);
  }
  .landing-hero .sub {
    font-size: 19px;
    line-height: 1.55;
    color: var(--ink-mid);
    margin: 0 0 36px;
    max-width: 580px;
    font-family: "Geist", sans-serif !important;
    font-weight: 400;
  }
  .hero-bullets {
    display: flex; gap: 28px;
    font-size: 13px; color: var(--slate);
    margin-top: 24px;
    flex-wrap: wrap;
  }
  .hero-bullets span {
    display: flex; align-items: center; gap: 8px;
  }
  .hero-bullets span::before {
    content: "·"; color: var(--ochre); font-size: 18px;
  }
  .hero-bullets span:first-child::before { content: none; }

  /* CTA buttons — override Streamlit button */
  .stButton > button {
    font-family: "Geist", sans-serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.005em !important;
    border-radius: 8px !important;
    border: 1px solid var(--line) !important;
    background: var(--paper) !important;
    color: var(--ink) !important;
    transition: all 0.18s ease !important;
    padding: 10px 20px !important;
    box-shadow: var(--shadow-sm) !important;
  }
  .stButton > button:hover {
    border-color: var(--ink) !important;
    transform: translateY(-1px);
    box-shadow: var(--shadow) !important;
  }
  .stButton > button[kind="primary"] {
    background: var(--ink) !important;
    color: var(--cream) !important;
    border: 1px solid var(--ink) !important;
    font-weight: 500 !important;
    padding: 14px 28px !important;
    font-size: 15px !important;
    box-shadow: var(--shadow) !important;
  }
  .stButton > button[kind="primary"]:hover {
    background: var(--ink-soft) !important;
    border-color: var(--ink-soft) !important;
    box-shadow: var(--shadow-lg) !important;
  }

  /* How it works */
  .section-divider {
    display: flex; align-items: center; gap: 16px;
    margin: 64px 0 32px;
  }
  .section-divider .label {
    font-family: "Fraunces", serif !important;
    font-style: italic; font-weight: 500;
    color: var(--ink); font-size: 22px;
    letter-spacing: -0.01em;
  }
  .section-divider .line {
    flex: 1; height: 1px; background: var(--line);
  }
  .section-divider .index {
    font-family: "JetBrains Mono", monospace !important;
    color: var(--slate-soft); font-size: 11px;
    letter-spacing: 0.1em;
  }

  .how-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: var(--line);
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
  }
  .how-card {
    background: var(--paper);
    padding: 32px 28px;
    transition: background 0.2s;
  }
  .how-card:hover { background: var(--cream); }
  .how-step {
    font-family: "Fraunces", serif !important;
    font-style: italic; font-weight: 500;
    font-size: 32px;
    color: var(--ochre);
    line-height: 1;
    margin-bottom: 12px;
  }
  .how-card h3 {
    font-size: 18px; font-weight: 600;
    color: var(--ink); margin: 0 0 8px;
    letter-spacing: -0.01em;
  }
  .how-card p {
    font-size: 13.5px; line-height: 1.55;
    color: var(--ink-mid); margin: 0;
  }

  /* Proof panel */
  .proof-panel {
    background: var(--ink);
    color: var(--cream);
    border-radius: 16px;
    padding: 48px;
    margin: 64px 0;
    position: relative;
    overflow: hidden;
  }
  .proof-panel::before {
    content: "";
    position: absolute; top: 0; right: 0;
    width: 280px; height: 280px;
    background: radial-gradient(circle, var(--ochre) 0%, transparent 70%);
    opacity: 0.12;
    transform: translate(40%, -40%);
  }
  .proof-panel .pp-label {
    font-family: "JetBrains Mono", monospace !important;
    font-size: 11px; letter-spacing: 0.14em;
    color: var(--ochre);
    text-transform: uppercase;
    margin-bottom: 16px;
  }
  .proof-panel h2 {
    font-family: "Fraunces", serif !important;
    font-weight: 500; font-size: 32px;
    margin: 0 0 32px;
    letter-spacing: -0.015em;
    color: var(--cream);
  }
  .proof-panel h2 em {
    color: var(--ochre); font-style: italic; font-weight: 400;
  }
  .pp-metrics {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 32px;
    border-top: 1px solid rgba(232, 220, 196, 0.18);
    padding-top: 28px;
  }
  .pp-metric .label {
    font-family: "JetBrains Mono", monospace !important;
    font-size: 10px; letter-spacing: 0.12em;
    color: var(--slate-soft);
    text-transform: uppercase;
    margin-bottom: 6px;
  }
  .pp-metric .val {
    font-family: "Fraunces", serif !important;
    font-weight: 500; font-size: 34px;
    color: var(--cream);
    letter-spacing: -0.02em;
  }
  .pp-metric .val em {
    color: var(--ochre); font-style: italic; font-weight: 400;
  }
  .proof-panel .note {
    margin-top: 24px;
    font-size: 12px; color: var(--slate-soft);
    font-style: italic;
  }

  /* Who block */
  .who-section {
    max-width: 720px;
    margin: 64px auto;
    padding: 0;
  }
  .who-section h2 {
    font-family: "Fraunces", serif !important;
    font-weight: 500; font-size: 28px;
    color: var(--ink); margin: 0 0 20px;
    letter-spacing: -0.015em;
  }
  .who-section h2 em {
    color: var(--ochre-deep); font-style: italic;
  }
  .who-section p {
    font-size: 16px; line-height: 1.65;
    color: var(--ink-mid);
    margin: 0;
  }
  .who-section strong { color: var(--ink); font-weight: 600; }

  /* Bottom CTA strip */
  .cta-strip {
    text-align: center;
    margin: 64px 0 32px;
    padding: 48px;
    background: var(--cream-deep);
    border-radius: 16px;
    border: 1px solid var(--line);
  }
  .cta-strip h3 {
    font-family: "Fraunces", serif !important;
    font-weight: 500; font-size: 26px;
    color: var(--ink); margin: 0 0 8px;
    letter-spacing: -0.015em;
  }
  .cta-strip p {
    font-size: 14px; color: var(--ink-mid);
    margin: 0 0 24px;
  }

  /* Footer */
  .landing-footer {
    margin-top: 60px; padding: 32px 0 16px;
    border-top: 1px solid var(--line);
    text-align: center;
  }
  .landing-footer .row1 {
    font-size: 13px; color: var(--ink-mid);
    margin-bottom: 8px;
  }
  .landing-footer a {
    color: var(--ochre-deep); text-decoration: none;
    border-bottom: 1px solid var(--ochre-soft);
    transition: border-color 0.2s;
  }
  .landing-footer a:hover { border-color: var(--ochre-deep); }
  .landing-footer .row2 {
    font-size: 11px; color: var(--slate-soft);
    margin-top: 12px;
    font-style: italic;
  }

  /* ────────────────────────────────────────────────────────────
     AUDIT FORM
     ──────────────────────────────────────────────────────────── */

  .form-wrap {
    max-width: 880px;
    margin: 0 auto;
    padding: 16px 24px 80px;
  }

  /* App header (consultant + owner audit pages) */
  .ml-header {
    background: var(--ink);
    color: var(--cream);
    border-radius: 14px;
    padding: 28px 32px;
    margin-bottom: 36px;
    position: relative;
    overflow: hidden;
  }
  .ml-header::before {
    content: "";
    position: absolute; top: -40%; right: -10%;
    width: 320px; height: 320px;
    background: radial-gradient(circle, var(--ochre) 0%, transparent 70%);
    opacity: 0.10;
  }
  .ml-header .eyebrow {
    font-family: "JetBrains Mono", monospace !important;
    font-size: 10px; letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--ochre);
    margin-bottom: 8px;
  }
  .ml-header h1 {
    font-family: "Fraunces", serif !important;
    font-weight: 500; font-size: 30px;
    color: var(--cream); margin: 0 0 6px;
    letter-spacing: -0.015em;
  }
  .ml-header h1 em { color: var(--ochre); font-style: italic; font-weight: 400; }
  .ml-header p {
    margin: 0; font-size: 14px; color: var(--slate-soft);
    max-width: 580px;
  }

  /* Form section blocks (1 / 2 / 3) */
  .form-section {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 32px;
    margin-bottom: 24px;
    box-shadow: var(--shadow-sm);
  }
  .form-section-head {
    display: flex; align-items: baseline; gap: 16px;
    margin-bottom: 8px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--line-soft);
  }
  .form-section-num {
    font-family: "Fraunces", serif !important;
    font-style: italic; font-weight: 500;
    font-size: 22px;
    color: var(--ochre);
    line-height: 1;
  }
  .form-section-title {
    font-family: "Fraunces", serif !important;
    font-weight: 500; font-size: 22px;
    color: var(--ink);
    letter-spacing: -0.015em;
    line-height: 1;
  }
  .form-section-desc {
    font-size: 13.5px; color: var(--ink-mid);
    margin: 14px 0 22px;
    line-height: 1.5;
  }

  /* Style Streamlit inputs to match */
  .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
    background: var(--cream) !important;
    border: 1px solid var(--line) !important;
    border-radius: 7px !important;
    color: var(--ink) !important;
    font-family: "Geist", sans-serif !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    transition: border-color 0.18s, box-shadow 0.18s !important;
  }
  .stTextInput input:focus, .stNumberInput input:focus {
    border-color: var(--ochre) !important;
    box-shadow: 0 0 0 3px var(--ochre-soft) !important;
    background: var(--paper) !important;
  }
  .stSelectbox > div > div:focus-within {
    border-color: var(--ochre) !important;
    box-shadow: 0 0 0 3px var(--ochre-soft) !important;
  }

  /* Labels in form */
  .stTextInput label, .stNumberInput label, .stSelectbox label, .stCheckbox label {
    font-family: "Geist", sans-serif !important;
    font-weight: 500 !important;
    font-size: 12.5px !important;
    color: var(--ink-mid) !important;
    letter-spacing: 0.01em;
  }

  /* Menu table headers */
  .menu-table-head {
    display: grid;
    grid-template-columns: 2.5fr 1.5fr 1.5fr 1fr 1fr 1fr;
    gap: 10px;
    padding: 0 4px 10px;
    border-bottom: 1px solid var(--line-soft);
    margin-bottom: 6px;
  }
  .menu-table-head span {
    font-family: "JetBrains Mono", monospace !important;
    font-size: 10px; letter-spacing: 0.12em;
    color: var(--slate);
    text-transform: uppercase;
    font-weight: 500;
  }

  /* Each row has subtle alternating shading via item-row class wrapper */
  div[data-testid="stHorizontalBlock"] {
    align-items: center;
    padding: 6px 0;
  }

  /* Tighten the number input + buttons so they don't dominate */
  .stNumberInput > div > div { gap: 4px !important; }

  /* Checkbox styling */
  .stCheckbox {
    background: var(--cream);
    border: 1px solid var(--line-soft);
    border-radius: 8px;
    padding: 12px 14px;
    margin-top: 8px;
  }
  .stCheckbox label p {
    font-size: 13.5px !important;
    color: var(--ink-mid) !important;
  }

  /* Email field gets distinct treatment in the third section */
  .email-callout {
    background: var(--cream);
    border: 1px solid var(--ochre-soft);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 8px;
  }

  /* Expander (competitor prices) */
  .streamlit-expanderHeader, [data-testid="stExpander"] summary {
    background: var(--cream) !important;
    border: 1px solid var(--line) !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    font-family: "Geist", sans-serif !important;
    font-weight: 500 !important;
    color: var(--ink) !important;
    font-size: 14px !important;
  }

  /* Run button — extra emphasis */
  .submit-row {
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid var(--line-soft);
  }

  /* Success card (owner-after-submit) */
  .owner-success-card {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 56px 40px;
    text-align: center;
    max-width: 600px;
    margin: 24px auto;
    box-shadow: var(--shadow);
    position: relative;
    overflow: hidden;
  }
  .owner-success-card::before {
    content: "";
    position: absolute; top: 0; left: 50%;
    transform: translateX(-50%);
    width: 80px; height: 4px;
    background: var(--ochre);
    border-radius: 0 0 8px 8px;
  }
  .success-icon {
    width: 56px; height: 56px;
    margin: 0 auto 20px;
    background: var(--ochre-soft);
    color: var(--ochre-deep);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: "Fraunces", serif !important;
    font-size: 28px; font-style: italic;
  }
  .owner-success-card h2 {
    font-family: "Fraunces", serif !important;
    font-weight: 500; font-size: 28px;
    color: var(--ink); margin: 0 0 10px;
    letter-spacing: -0.015em;
  }
  .owner-success-card .lede {
    font-size: 15px; color: var(--ink-mid);
    margin: 0 0 32px; line-height: 1.5;
  }
  .owner-success-card .lede strong { color: var(--ink); font-weight: 600; }

  .success-metric {
    background: var(--cream-deep);
    border-radius: 12px;
    padding: 24px;
    margin: 0 auto 24px;
    max-width: 380px;
  }
  .success-metric .label {
    font-family: "JetBrains Mono", monospace !important;
    font-size: 10px; letter-spacing: 0.14em;
    color: var(--ochre-deep); text-transform: uppercase;
    margin-bottom: 8px;
  }
  .success-metric .big-number {
    font-family: "Fraunces", serif !important;
    font-weight: 500; font-size: 48px;
    color: var(--ink);
    letter-spacing: -0.025em;
    line-height: 1;
    margin: 4px 0;
  }
  .success-metric .big-number em { color: var(--ochre-deep); font-style: italic; font-weight: 400; }
  .success-metric .sub {
    font-size: 13px; color: var(--ink-mid);
    margin-top: 4px;
  }

  .owner-success-card .next-note {
    font-size: 13px; color: var(--slate);
    line-height: 1.6;
    margin-top: 20px;
  }
  .owner-success-card .next-note a {
    color: var(--ochre-deep);
    border-bottom: 1px solid var(--ochre-soft);
    text-decoration: none;
  }

  /* ────────────────────────────────────────────────────────────
     CONSULTANT VIEW
     ──────────────────────────────────────────────────────────── */

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid var(--line) !important;
    margin-bottom: 24px;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 12px 16px !important;
    color: var(--slate) !important;
    font-family: "Geist", sans-serif !important;
    font-weight: 500 !important;
    font-size: 13.5px !important;
  }
  .stTabs [aria-selected="true"] {
    color: var(--ink) !important;
    border-bottom: 2px solid var(--ochre) !important;
  }

  /* Results: headline cards */
  .metric-card {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 22px 24px;
    text-align: left;
    box-shadow: var(--shadow-sm);
    transition: box-shadow 0.2s;
  }
  .metric-card:hover { box-shadow: var(--shadow); }
  .metric-card .label {
    font-family: "JetBrains Mono", monospace !important;
    font-size: 10px; letter-spacing: 0.14em;
    color: var(--slate); text-transform: uppercase;
    margin-bottom: 10px;
  }
  .metric-card .value {
    font-family: "Fraunces", serif !important;
    font-weight: 500; font-size: 32px;
    color: var(--ink); line-height: 1;
    letter-spacing: -0.02em;
  }
  .metric-card .value em { color: var(--ochre-deep); font-style: italic; font-weight: 400; }
  .metric-card .sub {
    font-size: 11.5px; color: var(--slate);
    margin-top: 6px;
    font-style: italic;
  }

  .qa-banner {
    background: var(--rust-soft);
    color: var(--rust);
    border-left: 3px solid var(--rust);
    padding: 14px 18px;
    border-radius: 8px;
    font-size: 13.5px;
    margin-bottom: 20px;
    line-height: 1.5;
  }

  /* Chips */
  .chip {
    padding: 3px 9px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 500;
    display: inline-block;
    font-family: "Geist", sans-serif !important;
    letter-spacing: 0.01em;
  }
  .q-Star      { background: var(--green-soft); color: var(--green); }
  .q-Plowhorse { background: #DDE3EE; color: var(--ink); }
  .q-Puzzle    { background: var(--ochre-soft); color: var(--ochre-deep); }
  .q-Dog       { background: var(--rust-soft); color: var(--rust); }
  .m-Above     { background: var(--rust-soft); color: var(--rust); }
  .m-Within    { background: var(--green-soft); color: var(--green); }
  .m-Below     { background: #FAEDD3; color: #6B5320; }
  .m-No        { background: var(--line-soft); color: var(--slate); }

  .act-raise { color: var(--green); font-weight: 600; }
  .act-cut   { color: var(--rust); font-weight: 600; }
  .act-hold  { color: var(--ink-mid); font-weight: 600; }

  /* Section heading inside cards */
  .section-head {
    font-family: "Fraunces", serif !important;
    font-weight: 500; font-size: 18px;
    color: var(--ink); letter-spacing: -0.01em;
    margin: 28px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--line-soft);
    display: flex; align-items: center; justify-content: space-between;
  }
  .section-head::after {
    content: "";
    flex: 1; height: 1px;
    background: var(--line-soft);
    margin-left: 16px;
    display: none;
  }

  /* Honeypot — invisible to humans */
  div[data-testid="stTextInput"]:has(input[aria-label="Leave this empty"]) {
    position: absolute !important;
    left: -9999px !important;
    width: 1px !important;
    height: 1px !important;
    opacity: 0 !important;
  }

  /* Sensitivity cards */
  .sens-card {
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 18px;
    text-align: center;
  }
  .sens-card.baseline {
    border: 1.5px solid var(--ink);
    background: var(--cream);
  }
  .sens-label {
    font-family: "JetBrains Mono", monospace !important;
    font-size: 10px; letter-spacing: 0.12em;
    color: var(--slate); text-transform: uppercase;
    margin-bottom: 8px;
  }
  .sens-val {
    font-family: "Fraunces", serif !important;
    font-weight: 500; font-size: 24px;
    letter-spacing: -0.02em;
  }
  .sens-val.pos { color: var(--green); }
  .sens-val.neg { color: var(--rust); }

  /* ── Mobile ─────────────────────────────────────────────── */
  @media (max-width: 720px) {
    .landing-wrap { padding: 16px 18px 60px; }
    .landing-hero h1 { font-size: 38px; }
    .landing-hero .sub { font-size: 16px; }
    .how-grid { grid-template-columns: 1fr; }
    .pp-metrics { grid-template-columns: 1fr; gap: 20px; }
    .proof-panel { padding: 32px 24px; }
    .proof-panel h2 { font-size: 26px; }
    .form-wrap { padding: 8px 14px 60px; }
    .form-section { padding: 24px 18px; }
    .menu-table-head { display: none; }
    .ml-header { padding: 22px 22px; }
    .ml-header h1 { font-size: 24px; }
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

    # Wrapper opening + nav + hero
    st.markdown("""
    <div class="landing-wrap">
      <div class="landing-nav">
        <div class="nav-brand">
          <div class="nav-mark">M</div>
          <div>
            <div class="nav-name">MarginLab</div>
            <div class="nav-tagline">Pricing Lab</div>
          </div>
        </div>
        <div class="nav-tagline" style="font-style:italic">Built for café operators</div>
      </div>

      <div class="landing-hero">
        <div class="hero-eyebrow">A free pricing audit · No login</div>
        <h1>Pricing your menu, the way a <em>consultant</em> would do it.</h1>
        <p class="sub">A 5-minute audit grounded in Lerner-optimal economics, menu-engineering theory,
        and confidence-weighted shrinkage. You enter your menu — we email you a PDF report with item-by-item recommendations.</p>
        <div class="hero-bullets">
          <span>Free</span>
          <span>No login required</span>
          <span>Report in your inbox</span>
          <span>~30 seconds to run</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Primary CTA (positioned right under hero)
    cta_col1, cta_col2 = st.columns([1, 5])
    with cta_col1:
        if st.button("Start your free audit", type="primary", use_container_width=True):
            track("cta_start_audit_click")
            st.session_state.view = "owner_audit"
            st.rerun()

    # How it works
    st.markdown("""
    <div class="landing-wrap" style="padding-top:0;padding-bottom:0">
      <div class="section-divider">
        <span class="index">01</span>
        <span class="label">How it works</span>
        <span class="line"></span>
      </div>

      <div class="how-grid">
        <div class="how-card">
          <div class="how-step">i.</div>
          <h3>Enter your menu</h3>
          <p>Items, costs, current prices, monthly units. Takes about 5 minutes for a typical café.</p>
        </div>
        <div class="how-card">
          <div class="how-step">ii.</div>
          <h3>The model runs</h3>
          <p>A 13-sheet Excel engine computes the profit-maximizing price for each item — guarded by role caps, market context, and confidence-weighted shrinkage.</p>
        </div>
        <div class="how-card">
          <div class="how-step">iii.</div>
          <h3>PDF in your inbox</h3>
          <p>Item-by-item recommendations, sensitivity analysis, and a sequencing plan. Forward it to your accountant.</p>
        </div>
      </div>

      <div class="proof-panel">
        <div class="pp-label">Example output · 6-item café menu</div>
        <h2>The kind of clarity you get back — but <em>personalized</em> to your menu.</h2>
        <div class="pp-metrics">
          <div class="pp-metric">
            <div class="label">Monthly Δ profit</div>
            <div class="val"><em>+$372</em></div>
          </div>
          <div class="pp-metric">
            <div class="label">Lift versus baseline</div>
            <div class="val"><em>+1.4%</em></div>
          </div>
          <div class="pp-metric">
            <div class="label">Items to change</div>
            <div class="val">5 of 6</div>
          </div>
        </div>
        <p class="note">Real audits are personalized to your specific menu, category mix, and (optionally) competitor context.</p>
      </div>

      <div class="section-divider">
        <span class="index">02</span>
        <span class="label">Who built this</span>
        <span class="line"></span>
      </div>

      <div class="who-section">
        <h2>An independent consultant who <em>obsesses</em> over menu economics.</h2>
        <p>
          MarginLab is built and run by <strong>Felix Richard</strong>, an independent consultant
          focused on pricing for food and beverage operators. The model behind this audit combines
          Lerner-optimal markup theory, menu-engineering quadrants, and demand-calibrated
          elasticities — packaged into something a café owner can act on the same day.
        </p>
      </div>

      <div class="cta-strip">
        <h3>Ready to see your numbers?</h3>
        <p>Free, takes five minutes, no account required.</p>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # Bottom CTA
    cta_col1, cta_col2, cta_col3 = st.columns([2, 2, 2])
    with cta_col2:
        if st.button("Get my free audit", type="primary", use_container_width=True, key="cta_bottom"):
            track("cta_bottom_click")
            st.session_state.view = "owner_audit"
            st.rerun()

    # Footer
    st.markdown("""
    <div class="landing-wrap" style="padding-top:0">
      <div class="landing-footer">
        <div class="row1">
          © MarginLab · <a href="mailto:felixrichard1208@gmail.com">felixrichard1208@gmail.com</a>
        </div>
        <div class="row1" style="font-size:12px;color:var(--slate)">
          We only use your email to send your audit report and follow-ups. We never share it.
        </div>
        <div class="row2">
          <a href="?view=consultant" style="font-size:11px">Consultant access →</a>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# OWNER AUDIT VIEW (Quick Audit)
# ══════════════════════════════════════════════════════════════════════════════

def render_owner_audit():
    """Owner-facing audit form — three labeled section cards, PDF-only delivery."""
    # Wrap whole form
    st.markdown('<div class="form-wrap">', unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div class="ml-header">
      <div class="eyebrow">Pricing Audit · Free</div>
      <h1>Tell us about <em>your menu</em>.</h1>
      <p>Enter your items below. We'll run the model and email your PDF report in about thirty seconds.</p>
    </div>
    """, unsafe_allow_html=True)

    # Back button
    if st.button("← Back to home", key="owner_back"):
        st.session_state.view = "landing"
        st.session_state.audit_result = None
        st.session_state.email_submitted = False
        st.rerun()

    # If audit already run and email submitted, show success state
    if st.session_state.audit_result is not None and st.session_state.email_submitted:
        render_owner_success()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # ── SECTION 1: About your café ─────────────────────────────────
    st.markdown("""
    <div class="form-section">
      <div class="form-section-head">
        <span class="form-section-num">i.</span>
        <span class="form-section-title">About your café</span>
      </div>
      <p class="form-section-desc">Your café name is optional and only used to personalize the PDF report.</p>
    </div>
    """, unsafe_allow_html=True)

    s1_c1, s1_c2 = st.columns([3, 1])
    with s1_c1:
        cafe_name = st.text_input(
            "Café name",
            value=st.session_state.audit_cafe_name,
            placeholder="e.g. The Daily Grind",
            label_visibility="visible",
        )
        st.session_state.audit_cafe_name = cafe_name
    with s1_c2:
        cur = st.selectbox(
            "Currency", CURRENCIES,
            index=CURRENCIES.index(st.session_state.settings["currency"]),
        )
        st.session_state.settings["currency"] = cur
    currency = cur

    # ── SECTION 2: Your menu ───────────────────────────────────────
    st.markdown("""
    <div class="form-section">
      <div class="form-section-head">
        <span class="form-section-num">ii.</span>
        <span class="form-section-title">Your menu</span>
      </div>
      <p class="form-section-desc">Add at least one item. We need name, cost, current price, and rough monthly units sold.
      You can add up to thirty items.</p>
    </div>
    """, unsafe_allow_html=True)

    # Menu table headers (visible on desktop, hidden on mobile via CSS)
    st.markdown(f"""
    <div class="menu-table-head">
      <span>Item name</span>
      <span>Category</span>
      <span>Role</span>
      <span>Cost · {currency}</span>
      <span>Price · {currency}</span>
      <span>Units / month</span>
    </div>
    """, unsafe_allow_html=True)

    _render_menu_table(currency, headerless=True)

    # Add/remove row
    btn_c1, btn_c2, _ = st.columns([1, 1, 5])
    with btn_c1:
        if st.button("Add another item", key="owner_add") and st.session_state.num_items < 30:
            st.session_state.num_items += 1
            st.rerun()
    with btn_c2:
        if st.button("Remove last", key="owner_rem") and st.session_state.num_items > 1:
            st.session_state.num_items -= 1
            st.rerun()

    # Competitor expander
    with st.expander("Add competitor prices (optional)"):
        st.caption("Enter prices from up to three nearby cafés for items where market context matters. Leave blank to skip.")
        _render_competitor_table()

    # ── SECTION 3: Send the audit ──────────────────────────────────
    st.markdown("""
    <div class="form-section">
      <div class="form-section-head">
        <span class="form-section-num">iii.</span>
        <span class="form-section-title">Send the audit</span>
      </div>
      <p class="form-section-desc">Your full PDF report — with item-by-item recommendations, sensitivity analysis,
      and a sequencing plan — will be in your inbox within a minute.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="email-callout">', unsafe_allow_html=True)
    email_val = st.text_input(
        "Email address",
        placeholder="you@yourcafe.com",
        key="owner_email_input",
    )
    st.session_state.audit_owner_email = email_val
    st.markdown('</div>', unsafe_allow_html=True)

    # Newsletter opt-in (styled checkbox)
    newsletter = st.checkbox(
        "Send me Felix's monthly pricing insights (unsubscribe anytime)",
        value=st.session_state.newsletter_opt_in,
    )
    st.session_state.newsletter_opt_in = newsletter

    # Honeypot — bot trap (invisible)
    honeypot = st.text_input(
        "Leave this empty",
        value="",
        key="_honeypot_field",
        label_visibility="collapsed",
    )

    # Submit button
    st.markdown('<div class="submit-row"></div>', unsafe_allow_html=True)
    run_col, _ = st.columns([2, 4])
    with run_col:
        run_clicked = st.button(
            "Email me my audit  →",
            type="primary",
            use_container_width=True,
            key="owner_run",
        )

    if run_clicked:
        # Honeypot — silent no-op
        if honeypot.strip():
            st.success("Submitted! Check your inbox.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        # Email validation
        ok, reason = validate_email(email_val)
        if not ok:
            st.error(reason)
            st.markdown('</div>', unsafe_allow_html=True)
            return

        # Rate limit
        ip = get_ip()
        allowed, _ = check_and_record(ip, max_per_hour=5)
        if not allowed:
            st.error("You've reached the audit limit for this hour. Please try again later, or email felixrichard1208@gmail.com if you need more.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        # Gather items
        items_raw = [st.session_state.menu_items[i] for i in range(st.session_state.num_items)]
        active = [it for it in items_raw if it.get("name", "").strip()]
        if not active:
            st.error("Please enter at least one menu item before submitting.")
            st.markdown('</div>', unsafe_allow_html=True)
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

        track("form_completed", {"item_count": len(item_inputs), "currency": s["currency"]})

        with st.spinner("Running the model and sending your report…"):
            result, error = run_audit(settings_input, item_inputs)
            if error:
                st.error(f"Something went wrong: {error}")
                st.markdown('</div>', unsafe_allow_html=True)
                return

            st.session_state.audit_result = result
            st.session_state.audit_currency = s["currency"]
            st.session_state.email_submitted = True

            save_submission(
                email=email_val, mode="owner", currency=s["currency"],
                items=item_inputs, audit=result,
                cafe_name=cafe_name, newsletter_opt_in=newsletter,
            )

            track("email_submitted", {"item_count": len(item_inputs)})
            identify(email_val, {"cafe_name": cafe_name,
                                  "newsletter_opt_in": newsletter})

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
                    schedule_followups(owner_email=email_val, cafe_name=cafe_name)
                except Exception:
                    pass

        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # close form-wrap

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
      <div class="success-icon">✓</div>
      <h2>Your audit is on its way.</h2>
      <p class="lede">
        We just emailed your full PDF report to <strong>{email}</strong>.<br>
        Check your inbox in the next minute or two.
      </p>

      <div class="success-metric">
        <div class="label">Estimated lift for {display_cafe}</div>
        <div class="big-number"><em>{lift_str}</em></div>
        <div class="sub">{pct_str} vs current pricing · monthly</div>
      </div>

      <p class="next-note">
        The full per-item breakdown, sensitivity analysis, and sequencing plan are in the PDF.<br>
        Don't see it? Check your spam folder, or email
        <a href="mailto:felixrichard1208@gmail.com">felixrichard1208@gmail.com</a>.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Reset / new audit
    rc1, rc2, rc3 = st.columns([2, 2, 2])
    with rc2:
        if st.button("Run another audit", use_container_width=True, key="owner_again"):
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
    st.markdown('<div class="form-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="ml-header">
      <div class="eyebrow">Restricted</div>
      <h1>Consultant <em>access</em>.</h1>
      <p>Enter your password to access the full audit interface, results, and lead history.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="form-section">', unsafe_allow_html=True)
    pw = st.text_input("Password", type="password", placeholder="Consultant password")
    pwc1, pwc2 = st.columns([1, 1])
    with pwc1:
        if st.button("Sign in", type="primary", use_container_width=True):
            correct = os.environ.get("CONSULTANT_PASSWORD")
            if correct is None:
                try:
                    correct = st.secrets["CONSULTANT_PASSWORD"]
                except (KeyError, FileNotFoundError, Exception):
                    correct = "marginlab2024"
            if pw and pw == correct:
                st.session_state.consultant_auth = True
                st.rerun()
            elif pw:
                st.error("Wrong password.")
    with pwc2:
        if st.button("← Back to home", use_container_width=True):
            st.session_state.view = "landing"
            st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)
    return False


def render_consultant():
    if not _check_consultant_password():
        return

    st.markdown('<div class="form-wrap" style="max-width:1180px">', unsafe_allow_html=True)
    st.markdown("""
    <div class="ml-header">
      <div class="eyebrow">Consultant view · Internal</div>
      <h1>Audit on a <em>client's behalf</em>.</h1>
      <p>Run an audit, view results, download Excel or PDF, and browse the lead history.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("← Back to home", key="cons_back"):
        st.session_state.view = "landing"
        st.session_state.audit_result = None
        st.rerun()

    tabs = st.tabs(["Input", "Results", "Admin"])

    with tabs[0]:
        _consultant_input_tab()
    with tabs[1]:
        _consultant_results_tab()
    with tabs[2]:
        _consultant_admin_tab()

    st.markdown('</div>', unsafe_allow_html=True)


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
          <div class="value"><em>{lift_str}</em></div>
          <div class="sub">{currency} · {pct_str}</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        bg = {"HIGH": "#DDE6DC", "MEDIUM": "#E8DCC4", "LOW": "#F0D9D4"}.get(conf, "#EFEAE0")
        tc = {"HIGH": "#4A6B4A", "MEDIUM": "#9A7842", "LOW": "#9C4A3C"}.get(conf, "#3D4862")
        st.markdown(f"""
        <div class="metric-card" style="background:{bg}">
          <div class="label" style="color:{tc};opacity:0.85">Confidence</div>
          <div class="value" style="color:{tc}">{conf}</div>
          <div class="sub" style="color:{tc};opacity:0.85">weighted</div>
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
        base_class = "sens-card baseline" if is_base else "sens-card"
        val_class = "pos" if val >= 0 else "neg"
        sign = "+" if val >= 0 else ""
        col.markdown(f"""
        <div class="{base_class}">
          <div class="sens-label">{label}</div>
          <div class="sens-val {val_class}">{sign}{_currency_display(val, currency)} {currency}</div>
        </div>""", unsafe_allow_html=True)

    rob_bg = "#DDE6DC" if "YES" in (audit.sens_robust or "") else "#F0D9D4"
    rob_tc = "#4A6B4A" if "YES" in (audit.sens_robust or "") else "#9C4A3C"
    st.markdown(f"""
    <div style="background:{rob_bg};color:{rob_tc};border-radius:8px;padding:10px 16px;
                margin-top:12px;font-weight:500;font-size:13px">
      Recommendation robust? <em style="font-family:Fraunces,serif;font-style:italic">{audit.sens_robust or "—"}</em>
    </div>""", unsafe_allow_html=True)

    # QA
    with st.expander("QA Summary"):
        qc1, qc2, qc3 = st.columns(3)
        ready_bg = "#DDE6DC" if audit.qa_hard_fails == 0 else "#F0D9D4"
        ready_tc = "#4A6B4A" if audit.qa_hard_fails == 0 else "#9C4A3C"
        qc1.markdown(f"""
        <div style="background:{ready_bg};color:{ready_tc};border-radius:8px;
                    padding:10px;font-weight:600;text-align:center">
          {audit.qa_ready or ('Ready' if audit.qa_hard_fails == 0 else 'Fix first')}
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

def _render_menu_table(currency, key_prefix="", headerless=False):
    if not headerless:
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
        f"<th style='background:#0F1A2E;color:#FAF7F2;padding:9px 10px;text-align:left;white-space:nowrap;"
        f"font-family:JetBrains Mono,monospace;font-weight:500;font-size:10px;letter-spacing:0.14em;text-transform:uppercase'>{c}</th>"
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
                # match the new ochre/green/rust soft palette
                colors = {
                    "HIGH":   "background:#DDE6DC;color:#4A6B4A",
                    "MEDIUM": "background:#E8DCC4;color:#9A7842",
                    "LOW":    "background:#F0D9D4;color:#9C4A3C",
                }
                style = colors.get(str(val), "background:#EFEAE0;color:#6B7588")
                cell = f'<span class="chip" style="{style}">{val}</span>'
            elif col == "Narrative":
                cell = f'<span style="font-size:12px;color:#3D4862;line-height:1.5">{val}</span>'
            else:
                cell = f'<span style="color:#0F1A2E">{val}</span>'
            cells += f"<td style='padding:8px 10px;border-bottom:1px solid #EFEAE0;vertical-align:middle'>{cell}</td>"
        body += f"<tr style='background:#FDFCF9'>{cells}</tr>"
    return (
        f"<table style='width:100%;border-collapse:collapse;font-size:13px;"
        f"border:1px solid #E5E0D4;border-radius:10px;overflow:hidden'>"
        f"<thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table>"
    )


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
