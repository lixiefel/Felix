"""
pdf_report.py — Generates a clean consulting-grade PDF from an AuditResult.

V2 improvements:
- Café name is the dominant header
- Footer is a watermark with confidentiality + recipient
- "Next steps" section at bottom with Calendly CTA
- Tested for 1, 6, 15, 30 items (multi-page when needed)
- "Prepared by Felix Richard" personalization
"""

from datetime import datetime
from engine import AuditResult


# ── color palettes ────────────────────────────────────────────────────────────
QUADRANT_COLORS = {
    "Star": "#d9f2d9", "Plowhorse": "#d9e1f2",
    "Puzzle": "#fce4d6", "Dog": "#fce3e3",
}
QUADRANT_TEXT = {
    "Star": "#1a5e1a", "Plowhorse": "#1f3864",
    "Puzzle": "#7e2e00", "Dog": "#7e0000",
}
MARKET_COLORS = {
    "Above market": "#fce3e3", "Below market": "#fff2cc",
    "Within market": "#d9f2d9", "No comp data": "#f0f0f0",
}
CONF_COLORS = {"HIGH": "#d9f2d9", "MEDIUM": "#fff2cc", "LOW": "#fce4d6"}
CONF_TEXT   = {"HIGH": "#1a5e1a", "MEDIUM": "#6b4e00", "LOW": "#7e2e00"}


def _fmt_currency(v, currency="USD"):
    if currency in ("IDR", "JPY", "VND"):
        return f"{v:,.0f}"
    return f"{v:,.2f}"


def _fmt_pct(v):
    sign = "+" if v >= 0 else ""
    return f"{sign}{v*100:.1f}%"


def build_pdf_html(
    audit: AuditResult,
    currency: str = "USD",
    cafe_name: str = "",
    consultant_name: str = "Felix Richard",
    consultant_email: str = "felixrichard1208@gmail.com",
    calendly_url: str = "https://calendly.com/marginlab-felix",
) -> str:
    """Build full HTML for the audit PDF. Returns a printable HTML string."""
    date_str = datetime.utcnow().strftime("%B %d, %Y")
    display_cafe = cafe_name.strip() if cafe_name and cafe_name.strip() else "Your Café"
    watermark_text = f"Confidential analysis prepared for {display_cafe} by MarginLab · Not for redistribution · {date_str}"

    # ── Banner block ──────────────────────────────────────────────────────────
    banner_html = ""
    if audit.banner:
        banner_html = f"""
        <div style="background:#c00000;color:white;padding:10px 16px;border-radius:6px;
                    margin-bottom:18px;font-weight:600;font-size:12px">
          ⚠ {audit.banner}
        </div>"""

    # ── Headline cards ────────────────────────────────────────────────────────
    conf_bg = CONF_COLORS.get(audit.confidence, "#f0f0f0")
    conf_tc = CONF_TEXT.get(audit.confidence, "#333")
    lift_sign = "+" if audit.monthly_lift >= 0 else ""
    lift_display = f"{lift_sign}{_fmt_currency(audit.monthly_lift, currency)}"
    pct_display = _fmt_pct(audit.lift_pct)

    headline_html = f"""
    <table style="width:100%;border-collapse:separate;border-spacing:8px 0;margin-bottom:20px">
      <tr>
        <td style="width:34%;background:#1f3864;color:white;border-radius:8px;padding:14px;vertical-align:top">
          <div style="font-size:10px;opacity:0.8;letter-spacing:0.5px;text-transform:uppercase">MONTHLY Δ PROFIT</div>
          <div style="font-size:24px;font-weight:800;margin-top:4px">{lift_display} {currency}</div>
          <div style="font-size:12px;opacity:0.85;margin-top:2px">{pct_display} vs baseline</div>
        </td>
        <td style="width:33%;background:{conf_bg};border-radius:8px;padding:14px;vertical-align:top">
          <div style="font-size:10px;color:{conf_tc};opacity:0.8;letter-spacing:0.5px;text-transform:uppercase">CONFIDENCE</div>
          <div style="font-size:24px;font-weight:800;margin-top:4px;color:{conf_tc}">{audit.confidence}</div>
          <div style="font-size:11px;color:{conf_tc};opacity:0.85;margin-top:2px">overall (weighted)</div>
        </td>
        <td style="width:33%;background:#f8f9fa;border-radius:8px;padding:14px;vertical-align:top">
          <div style="font-size:10px;color:#555;letter-spacing:0.5px;text-transform:uppercase">BEST OPPORTUNITY</div>
          <div style="font-size:15px;font-weight:700;color:#1f3864;margin-top:4px">{audit.best_item.replace('Best item: ','')}</div>
          <div style="font-size:11px;color:#777;margin-top:2px">highest Δ profit</div>
        </td>
      </tr>
    </table>"""

    # ── Per-item table ────────────────────────────────────────────────────────
    rows_html = ""
    for item in audit.items:
        q_bg = QUADRANT_COLORS.get(item.quadrant, "#f0f0f0")
        q_tc = QUADRANT_TEXT.get(item.quadrant, "#333")
        m_bg = MARKET_COLORS.get(item.market, "#f0f0f0")
        action_color = "#006100" if item.action == "Raise" else ("#7e0000" if item.action == "Cut" else "#333")
        dp_sign = "+" if item.delta_profit_mo >= 0 else ""
        rows_html += f"""
        <tr style="page-break-inside:avoid">
          <td style="font-weight:600;padding:5px 8px;border-bottom:1px solid #eef0f4">{item.name}</td>
          <td style="color:{action_color};font-weight:600;padding:5px 4px;border-bottom:1px solid #eef0f4">{item.action}</td>
          <td style="padding:5px 4px;text-align:right;border-bottom:1px solid #eef0f4">{_fmt_currency(item.price_from,currency)}</td>
          <td style="padding:5px 4px;text-align:right;font-weight:600;border-bottom:1px solid #eef0f4">{_fmt_currency(item.price_to,currency)}</td>
          <td style="padding:5px 4px;text-align:right;color:{action_color};border-bottom:1px solid #eef0f4">{_fmt_pct(item.delta_pct)}</td>
          <td style="padding:5px 4px;text-align:right;font-weight:600;border-bottom:1px solid #eef0f4">{dp_sign}{_fmt_currency(item.delta_profit_mo,currency)}</td>
          <td style="padding:4px;text-align:center;border-bottom:1px solid #eef0f4">
            <span style="background:{q_bg};color:{q_tc};padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600">{item.quadrant}</span>
          </td>
          <td style="padding:4px;text-align:center;border-bottom:1px solid #eef0f4">
            <span style="background:{m_bg};padding:2px 7px;border-radius:4px;font-size:10px">{item.market}</span>
          </td>
          <td style="padding:5px 4px;font-size:10px;color:#555;border-bottom:1px solid #eef0f4;max-width:200px">{item.narrative}</td>
        </tr>"""

    table_html = f"""
    <h3 style="color:#1f3864;border-bottom:2px solid #1f3864;padding-bottom:4px;margin:18px 0 8px;font-size:14px">
      Per-Item Recommendations
    </h3>
    <table style="width:100%;border-collapse:collapse;font-size:11px">
      <thead style="display:table-header-group">
        <tr style="background:#1f3864;color:white">
          <th style="padding:6px 8px;text-align:left">Item</th>
          <th style="padding:6px 4px;text-align:left">Action</th>
          <th style="padding:6px 4px;text-align:right">From</th>
          <th style="padding:6px 4px;text-align:right">To</th>
          <th style="padding:6px 4px;text-align:right">Δ%</th>
          <th style="padding:6px 4px;text-align:right">Δ Profit/mo</th>
          <th style="padding:6px 4px;text-align:center">Quadrant</th>
          <th style="padding:6px 4px;text-align:center">Market</th>
          <th style="padding:6px 4px;text-align:left">Narrative</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>"""

    # ── Sensitivity block ─────────────────────────────────────────────────────
    cons_color = "#006100" if audit.sens_conservative >= 0 else "#c00000"
    base_color = "#006100" if audit.sens_baseline >= 0 else "#c00000"
    opt_color  = "#006100" if audit.sens_optimistic >= 0 else "#c00000"
    robust_bg  = "#d9f2d9" if "YES" in (audit.sens_robust or "") else "#fce3e3"
    sens_html = f"""
    <h3 style="color:#1f3864;border-bottom:2px solid #1f3864;padding-bottom:4px;
               margin-top:18px;margin-bottom:8px;font-size:14px;page-break-after:avoid">Sensitivity Check</h3>
    <table style="width:100%;border-collapse:separate;border-spacing:8px 0;page-break-inside:avoid">
      <tr>
        <td style="width:33%;border:1px solid #ddd;border-radius:6px;padding:10px;text-align:center">
          <div style="font-size:10px;color:#777">Conservative (e×1.2)</div>
          <div style="font-size:16px;font-weight:800;color:{cons_color};margin-top:2px">
            {'+' if audit.sens_conservative>=0 else ''}{_fmt_currency(audit.sens_conservative,currency)}
          </div>
        </td>
        <td style="width:33%;border:2px solid #1f3864;border-radius:6px;padding:10px;text-align:center">
          <div style="font-size:10px;color:#777">Baseline (e×1.0)</div>
          <div style="font-size:16px;font-weight:800;color:{base_color};margin-top:2px">
            {'+' if audit.sens_baseline>=0 else ''}{_fmt_currency(audit.sens_baseline,currency)}
          </div>
        </td>
        <td style="width:33%;border:1px solid #ddd;border-radius:6px;padding:10px;text-align:center">
          <div style="font-size:10px;color:#777">Optimistic (e×0.8)</div>
          <div style="font-size:16px;font-weight:800;color:{opt_color};margin-top:2px">
            {'+' if audit.sens_optimistic>=0 else ''}{_fmt_currency(audit.sens_optimistic,currency)}
          </div>
        </td>
      </tr>
    </table>
    <div style="background:{robust_bg};border-radius:6px;padding:6px 12px;font-size:11px;font-weight:600;margin-top:6px">
      Recommendation robust? {audit.sens_robust}
    </div>"""

    # ── Next steps ────────────────────────────────────────────────────────────
    next_steps_html = f"""
    <h3 style="color:#1f3864;border-bottom:2px solid #1f3864;padding-bottom:4px;
               margin-top:18px;margin-bottom:8px;font-size:14px;page-break-after:avoid">Next Steps</h3>
    <ol style="font-size:11px;line-height:1.55;color:#333;padding-left:18px;margin:6px 0;page-break-inside:avoid">
      <li><b>Sequence, don't simultaneously change.</b> Start with the single highest-confidence raise.
          Hold the new price for two weeks. Measure traffic and revenue against the prior two weeks.</li>
      <li><b>Watch your Traffic Drivers.</b> The model caps these tightly. Don't override the cap without
          a clear plan — these items anchor customer perception of value across the rest of the menu.</li>
      <li><b>Re-run after one cycle.</b> Once you've implemented and observed, re-do the audit with the new
          numbers. Confidence tiers improve quickly once we have real before/after data.</li>
    </ol>
    <div style="background:#f4f6f9;border-left:3px solid #1f3864;padding:10px 14px;margin-top:10px;font-size:11px;line-height:1.5;page-break-inside:avoid">
      <b>Want help implementing this?</b><br>
      Reply to the email this report came in, or book a free 15-minute walkthrough:
      <a href="{calendly_url}" style="color:#1f3864;text-decoration:underline">{calendly_url}</a>
    </div>"""

    # ── Sign-off ──────────────────────────────────────────────────────────────
    signoff_html = f"""
    <div style="margin-top:18px;font-size:11px;color:#444;page-break-inside:avoid">
      Prepared by <b style="font-style:italic">{consultant_name}</b> · MarginLab Pricing Lab<br>
      <span style="color:#888">{consultant_email}</span>
    </div>"""

    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    @page {{
      size: A4 landscape;
      margin: 14mm 14mm 22mm 14mm;
      @bottom-center {{
        content: "{watermark_text}";
        font-size: 8px;
        color: #999;
        font-family: Arial, sans-serif;
      }}
    }}
    body {{
      font-family: Arial, Helvetica, sans-serif;
      font-size: 12px;
      color: #222;
      margin: 0;
      padding: 0;
    }}
    h1.cafe-name {{
      color: #1f3864;
      margin: 0 0 2px 0;
      font-size: 28px;
      font-weight: 800;
      letter-spacing: -0.3px;
    }}
    h2.subhead {{
      color: #777;
      font-size: 11px;
      font-weight: normal;
      margin: 0 0 6px 0;
      letter-spacing: 0.3px;
      text-transform: uppercase;
    }}
    h3 {{ page-break-after: avoid; }}
    .marginlab-mark {{
      color: #1f3864;
      font-weight: 700;
      font-size: 13px;
      letter-spacing: 0.4px;
      margin-top: 6px;
    }}
    table {{ page-break-inside: auto; }}
    tr {{ page-break-inside: avoid; page-break-after: auto; }}
    thead {{ display: table-header-group; }}
  </style>
</head>
<body>
  <h1 class="cafe-name">{display_cafe}</h1>
  <h2 class="subhead">Pricing Audit · {date_str}</h2>
  <div class="marginlab-mark">MARGINLAB</div>

  {banner_html}
  {headline_html}
  {table_html}
  {sens_html}
  {next_steps_html}
  {signoff_html}
</body>
</html>"""

    return full_html


def generate_pdf(audit, currency="USD", cafe_name="",
                 consultant_name="Felix Richard",
                 consultant_email="felixrichard1208@gmail.com",
                 calendly_url="https://calendly.com/marginlab-felix") -> bytes | None:
    """Returns PDF bytes, or None if weasyprint not available."""
    try:
        from weasyprint import HTML
    except ImportError:
        return None
    try:
        html = build_pdf_html(audit, currency, cafe_name, consultant_name,
                              consultant_email, calendly_url)
        return HTML(string=html).write_pdf()
    except Exception:
        return None


def generate_html_report(audit, currency="USD", cafe_name="",
                         consultant_name="Felix Richard",
                         consultant_email="felixrichard1208@gmail.com",
                         calendly_url="https://calendly.com/marginlab-felix") -> str:
    """HTML version that always works (no weasyprint required)."""
    return build_pdf_html(audit, currency, cafe_name, consultant_name,
                          consultant_email, calendly_url)
