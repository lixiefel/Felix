"""
pdf_report.py — Generates a clean one-page consulting PDF from an AuditResult
Uses weasyprint (HTML → PDF) with inline CSS so no file assets needed.
"""

from datetime import datetime
from engine import AuditResult

QUADRANT_COLORS = {
    "Star": "#d9f2d9",
    "Plowhorse": "#d9e1f2",
    "Puzzle": "#fce4d6",
    "Dog": "#fce3e3",
}
QUADRANT_TEXT = {
    "Star": "#1a5e1a",
    "Plowhorse": "#1f3864",
    "Puzzle": "#7e2e00",
    "Dog": "#7e0000",
}
MARKET_COLORS = {
    "Above market": "#fce3e3",
    "Below market": "#fff2cc",
    "Within market": "#d9f2d9",
    "No comp data": "#f0f0f0",
}
CONF_COLORS = {
    "HIGH": "#d9f2d9", "MEDIUM": "#fff2cc", "LOW": "#fce4d6"
}


def _fmt_currency(v, currency="USD"):
    if currency in ("IDR", "JPY", "VND"):
        return f"{v:,.0f}"
    return f"{v:,.2f}"


def _fmt_pct(v):
    sign = "+" if v >= 0 else ""
    return f"{sign}{v*100:.1f}%"


def _conf_badge(conf):
    bg = CONF_COLORS.get(conf, "#f0f0f0")
    return f'<span style="background:{bg};padding:2px 8px;border-radius:4px;font-weight:600;font-size:11px">{conf}</span>'


def build_pdf_html(audit: AuditResult, currency: str = "USD", cafe_name: str = "") -> str:
    date_str = datetime.utcnow().strftime("%B %d, %Y")
    title = f"MarginLab Pricing Audit — {cafe_name}" if cafe_name else "MarginLab Pricing Audit"

    # Banner
    banner_html = ""
    if audit.banner:
        banner_html = f"""
        <div style="background:#c00000;color:white;padding:10px 16px;border-radius:6px;
                    margin-bottom:20px;font-weight:600;font-size:13px">
            {audit.banner}
        </div>"""

    # Headline cards
    conf_bg = CONF_COLORS.get(audit.confidence, "#f0f0f0")
    conf_tc = QUADRANT_TEXT.get(audit.confidence, "#333")
    lift_sign = "+" if audit.monthly_lift >= 0 else ""
    lift_display = f"{lift_sign}{_fmt_currency(audit.monthly_lift, currency)}"
    pct_display = _fmt_pct(audit.lift_pct)

    headline_html = f"""
    <div style="display:flex;gap:16px;margin-bottom:24px">
      <div style="flex:1;background:#1f3864;color:white;border-radius:8px;padding:16px;text-align:center">
        <div style="font-size:11px;opacity:0.8;margin-bottom:4px">MONTHLY Δ PROFIT</div>
        <div style="font-size:26px;font-weight:700">{lift_display} {currency}</div>
        <div style="font-size:13px;opacity:0.8">{pct_display} vs baseline</div>
      </div>
      <div style="flex:1;background:{conf_bg};border-radius:8px;padding:16px;text-align:center">
        <div style="font-size:11px;color:{conf_tc};opacity:0.8;margin-bottom:4px">CONFIDENCE</div>
        <div style="font-size:26px;font-weight:700;color:{conf_tc}">{audit.confidence}</div>
        <div style="font-size:13px;color:{conf_tc};opacity:0.8">{audit.changes_count} items</div>
      </div>
      <div style="flex:1;background:#f8f9fa;border-radius:8px;padding:16px;text-align:center">
        <div style="font-size:11px;color:#555;margin-bottom:4px">BEST OPPORTUNITY</div>
        <div style="font-size:16px;font-weight:700;color:#1f3864">{audit.best_item}</div>
        <div style="font-size:12px;color:#777">highest Δ profit</div>
      </div>
    </div>"""

    # Per-item table
    rows_html = ""
    for item in audit.items:
        q_bg = QUADRANT_COLORS.get(item.quadrant, "#f0f0f0")
        q_tc = QUADRANT_TEXT.get(item.quadrant, "#333")
        m_bg = MARKET_COLORS.get(item.market, "#f0f0f0")
        action_color = "#006100" if item.action == "Raise" else ("#7e0000" if item.action == "Cut" else "#333")
        dp_sign = "+" if item.delta_profit_mo >= 0 else ""
        rows_html += f"""
        <tr>
          <td style="font-weight:600;padding:6px 8px">{item.name}</td>
          <td style="color:{action_color};font-weight:600;padding:6px 4px">{item.action}</td>
          <td style="padding:6px 4px;text-align:right">{_fmt_currency(item.price_from,currency)}</td>
          <td style="padding:6px 4px;text-align:right;font-weight:600">{_fmt_currency(item.price_to,currency)}</td>
          <td style="padding:6px 4px;text-align:right;color:{action_color}">{_fmt_pct(item.delta_pct)}</td>
          <td style="padding:6px 4px;text-align:right;font-weight:600">{dp_sign}{_fmt_currency(item.delta_profit_mo,currency)}</td>
          <td style="padding:4px;text-align:center">
            <span style="background:{q_bg};color:{q_tc};padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600">{item.quadrant}</span>
          </td>
          <td style="padding:4px;text-align:center">
            <span style="background:{m_bg};padding:2px 7px;border-radius:4px;font-size:11px">{item.market}</span>
          </td>
          <td style="padding:6px 4px;font-size:11px;color:#555;max-width:180px">{item.narrative}</td>
        </tr>"""

    table_html = f"""
    <h3 style="color:#1f3864;border-bottom:2px solid #1f3864;padding-bottom:4px;margin-bottom:8px">
      Per-Item Recommendations
    </h3>
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead>
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

    # Sensitivity block
    cons_color = "#006100" if audit.sens_conservative >= 0 else "#c00000"
    base_color = "#006100" if audit.sens_baseline >= 0 else "#c00000"
    opt_color  = "#006100" if audit.sens_optimistic >= 0 else "#c00000"
    robust_bg  = "#d9f2d9" if "YES" in audit.sens_robust else "#fce3e3"
    sens_html = f"""
    <h3 style="color:#1f3864;border-bottom:2px solid #1f3864;padding-bottom:4px;
               margin-top:20px;margin-bottom:8px">Sensitivity Check</h3>
    <div style="display:flex;gap:12px;margin-bottom:8px">
      <div style="flex:1;border:1px solid #ddd;border-radius:6px;padding:10px;text-align:center">
        <div style="font-size:10px;color:#777;margin-bottom:2px">Conservative (e×1.2)</div>
        <div style="font-size:18px;font-weight:700;color:{cons_color}">
          {'+' if audit.sens_conservative>=0 else ''}{_fmt_currency(audit.sens_conservative,currency)}
        </div>
      </div>
      <div style="flex:1;border:2px solid #1f3864;border-radius:6px;padding:10px;text-align:center">
        <div style="font-size:10px;color:#777;margin-bottom:2px">Baseline (e×1.0)</div>
        <div style="font-size:18px;font-weight:700;color:{base_color}">
          {'+' if audit.sens_baseline>=0 else ''}{_fmt_currency(audit.sens_baseline,currency)}
        </div>
      </div>
      <div style="flex:1;border:1px solid #ddd;border-radius:6px;padding:10px;text-align:center">
        <div style="font-size:10px;color:#777;margin-bottom:2px">Optimistic (e×0.8)</div>
        <div style="font-size:18px;font-weight:700;color:{opt_color}">
          {'+' if audit.sens_optimistic>=0 else ''}{_fmt_currency(audit.sens_optimistic,currency)}
        </div>
      </div>
    </div>
    <div style="background:{robust_bg};border-radius:6px;padding:8px 12px;font-size:12px;font-weight:600">
      Recommendation robust? {audit.sens_robust}
    </div>"""

    # Footer
    footer_html = f"""
    <div style="margin-top:24px;padding-top:12px;border-top:1px solid #ddd;
                font-size:10px;color:#999;display:flex;justify-content:space-between">
      <span>Generated by MarginLab Pricing Lab · {date_str}</span>
      <span>Powered by Lerner-optimal pricing with demand-calibrated elasticity</span>
    </div>"""

    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    @page {{ size: A4 landscape; margin: 15mm; }}
    body {{ font-family: Arial, Helvetica, sans-serif; font-size: 13px;
            color: #222; margin: 0; padding: 0; }}
    h1 {{ color: #1f3864; margin: 0 0 4px 0; font-size: 22px; }}
    h2 {{ color: #555; font-size: 13px; font-weight: normal; margin: 0 0 20px 0; }}
    table {{ page-break-inside: avoid; }}
    tr {{ page-break-inside: avoid; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <h2>Confidential pricing analysis · {date_str}</h2>
  {banner_html}
  {headline_html}
  {table_html}
  {sens_html}
  {footer_html}
</body>
</html>"""

    return full_html


def generate_pdf(audit: AuditResult, currency: str = "USD", cafe_name: str = "") -> bytes | None:
    """Returns PDF bytes, or None if weasyprint not available."""
    try:
        from weasyprint import HTML
        html = build_pdf_html(audit, currency, cafe_name)
        return HTML(string=html).write_pdf()
    except ImportError:
        return None


def generate_html_report(audit: AuditResult, currency: str = "USD", cafe_name: str = "") -> str:
    """Always works — returns the HTML string."""
    return build_pdf_html(audit, currency, cafe_name)
