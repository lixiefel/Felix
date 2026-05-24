"""
pdf_report.py — Generates a clean consulting-grade PDF from an AuditResult.

V3 — premium redesign:
- Editorial typography (Fraunces serif headings, Geist sans body)
- Ink navy + warm cream + ochre accent palette
- Magazine-style header with brand mark + dateline
- Subdued chips, no neon colors
- Sections separated by rules and small caps eyebrows
- Watermark via @page CSS for every page
"""

from datetime import datetime
from engine import AuditResult


# ── Color tokens (mirror app.py design system) ───────────────────────────────
INK        = "#0F1A2E"
INK_SOFT   = "#1F2A40"
INK_MID    = "#3D4862"
SLATE      = "#6B7588"
SLATE_SOFT = "#9AA3B5"
LINE       = "#E5E0D4"
LINE_SOFT  = "#EFEAE0"
CREAM      = "#FAF7F2"
CREAM_DEEP = "#F2EDE3"
PAPER      = "#FDFCF9"
OCHRE      = "#B8935C"
OCHRE_DEEP = "#9A7842"
OCHRE_SOFT = "#E8DCC4"
GREEN      = "#4A6B4A"
GREEN_SOFT = "#DDE6DC"
RUST       = "#9C4A3C"
RUST_SOFT  = "#F0D9D4"

# ── Chip palettes ────────────────────────────────────────────────────────────
QUADRANT_BG = {"Star": GREEN_SOFT, "Plowhorse": "#DDE3EE",
               "Puzzle": OCHRE_SOFT, "Dog": RUST_SOFT}
QUADRANT_FG = {"Star": GREEN, "Plowhorse": INK,
               "Puzzle": OCHRE_DEEP, "Dog": RUST}
MARKET_BG = {"Above market": RUST_SOFT, "Below market": "#FAEDD3",
             "Within market": GREEN_SOFT, "No comp data": LINE_SOFT}
MARKET_FG = {"Above market": RUST, "Below market": "#6B5320",
             "Within market": GREEN, "No comp data": SLATE}
CONF_BG = {"HIGH": GREEN_SOFT, "MEDIUM": OCHRE_SOFT, "LOW": RUST_SOFT}
CONF_FG = {"HIGH": GREEN, "MEDIUM": OCHRE_DEEP, "LOW": RUST}


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
    """Build full HTML for the audit PDF."""
    date_str = datetime.utcnow().strftime("%B %d, %Y")
    display_cafe = cafe_name.strip() if cafe_name and cafe_name.strip() else "Your Café"
    watermark_text = f"Confidential analysis prepared for {display_cafe} by MarginLab · Not for redistribution · {date_str}"

    # ── Banner ────────────────────────────────────────────────────────────────
    banner_html = ""
    if audit.banner:
        banner_html = f"""
        <div style="background:{RUST_SOFT};color:{RUST};border-left:3px solid {RUST};
                    padding:11px 16px;border-radius:6px;
                    margin-bottom:18px;font-weight:500;font-size:11.5px;line-height:1.5">
          {audit.banner}
        </div>"""

    # ── Headline metrics ──────────────────────────────────────────────────────
    conf_bg = CONF_BG.get(audit.confidence, LINE_SOFT)
    conf_fg = CONF_FG.get(audit.confidence, INK_MID)
    lift_sign = "+" if audit.monthly_lift >= 0 else ""
    lift_display = f"{lift_sign}{_fmt_currency(audit.monthly_lift, currency)}"
    pct_display = _fmt_pct(audit.lift_pct)

    headline_html = f"""
    <table style="width:100%;border-collapse:separate;border-spacing:10px 0;margin-bottom:24px">
      <tr>
        <td style="width:34%;background:{INK};color:{CREAM};border-radius:10px;padding:18px 20px;vertical-align:top">
          <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:{OCHRE};letter-spacing:0.16em;text-transform:uppercase">Monthly Δ profit</div>
          <div style="font-family:Fraunces,Georgia,serif;font-weight:500;font-size:30px;margin-top:6px;letter-spacing:-0.02em;color:{CREAM}">
            <em style="color:{OCHRE};font-style:italic;font-weight:400">{lift_display}</em> {currency}
          </div>
          <div style="font-size:11.5px;color:{SLATE_SOFT};margin-top:4px;font-style:italic">{pct_display} versus baseline</div>
        </td>
        <td style="width:33%;background:{conf_bg};border-radius:10px;padding:18px 20px;vertical-align:top">
          <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:{conf_fg};letter-spacing:0.16em;text-transform:uppercase;opacity:0.85">Confidence</div>
          <div style="font-family:Fraunces,Georgia,serif;font-weight:500;font-size:30px;margin-top:6px;letter-spacing:-0.02em;color:{conf_fg}">{audit.confidence}</div>
          <div style="font-size:11.5px;color:{conf_fg};margin-top:4px;font-style:italic;opacity:0.85">weighted across items</div>
        </td>
        <td style="width:33%;background:{CREAM_DEEP};border-radius:10px;padding:18px 20px;vertical-align:top">
          <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:{SLATE};letter-spacing:0.16em;text-transform:uppercase">Best opportunity</div>
          <div style="font-family:Fraunces,Georgia,serif;font-weight:500;font-size:17px;margin-top:6px;letter-spacing:-0.01em;color:{INK}">{audit.best_item.replace('Best item: ','')}</div>
          <div style="font-size:11.5px;color:{SLATE};margin-top:4px;font-style:italic">highest Δ profit</div>
        </td>
      </tr>
    </table>"""

    # ── Per-item table ────────────────────────────────────────────────────────
    rows_html = ""
    for item in audit.items:
        q_bg = QUADRANT_BG.get(item.quadrant, LINE_SOFT)
        q_fg = QUADRANT_FG.get(item.quadrant, INK_MID)
        m_bg = MARKET_BG.get(item.market, LINE_SOFT)
        m_fg = MARKET_FG.get(item.market, SLATE)
        action_color = GREEN if item.action == "Raise" else (RUST if item.action == "Cut" else INK_MID)
        dp_sign = "+" if item.delta_profit_mo >= 0 else ""
        rows_html += f"""
        <tr style="page-break-inside:avoid">
          <td style="font-weight:600;padding:7px 10px;border-bottom:1px solid {LINE_SOFT};color:{INK}">{item.name}</td>
          <td style="color:{action_color};font-weight:600;padding:7px 4px;border-bottom:1px solid {LINE_SOFT}">{item.action}</td>
          <td style="padding:7px 4px;text-align:right;border-bottom:1px solid {LINE_SOFT};color:{INK_MID}">{_fmt_currency(item.price_from,currency)}</td>
          <td style="padding:7px 4px;text-align:right;font-weight:600;border-bottom:1px solid {LINE_SOFT};color:{INK}">{_fmt_currency(item.price_to,currency)}</td>
          <td style="padding:7px 4px;text-align:right;color:{action_color};border-bottom:1px solid {LINE_SOFT}">{_fmt_pct(item.delta_pct)}</td>
          <td style="padding:7px 4px;text-align:right;font-weight:600;border-bottom:1px solid {LINE_SOFT};color:{INK}">{dp_sign}{_fmt_currency(item.delta_profit_mo,currency)}</td>
          <td style="padding:5px 4px;text-align:center;border-bottom:1px solid {LINE_SOFT}">
            <span style="background:{q_bg};color:{q_fg};padding:2px 8px;border-radius:4px;font-size:10px;font-weight:500">{item.quadrant}</span>
          </td>
          <td style="padding:5px 4px;text-align:center;border-bottom:1px solid {LINE_SOFT}">
            <span style="background:{m_bg};color:{m_fg};padding:2px 8px;border-radius:4px;font-size:10px">{item.market}</span>
          </td>
          <td style="padding:7px 4px;font-size:10.5px;color:{INK_MID};border-bottom:1px solid {LINE_SOFT};max-width:220px;line-height:1.4">{item.narrative}</td>
        </tr>"""

    table_html = f"""
    <div style="display:flex;align-items:center;gap:12px;margin:24px 0 10px">
      <span style="font-family:'JetBrains Mono',monospace;color:{SLATE_SOFT};font-size:10px;letter-spacing:0.14em">01</span>
      <span style="font-family:Fraunces,Georgia,serif;font-style:italic;color:{INK};font-size:18px;letter-spacing:-0.01em">Per-item recommendations</span>
      <span style="flex:1;height:1px;background:{LINE}"></span>
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:11.5px;color:{INK}">
      <thead style="display:table-header-group">
        <tr style="background:{INK};color:{CREAM}">
          <th style="padding:8px 10px;text-align:left;font-weight:500;font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:0.14em;text-transform:uppercase">Item</th>
          <th style="padding:8px 4px;text-align:left;font-weight:500;font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:0.14em;text-transform:uppercase">Action</th>
          <th style="padding:8px 4px;text-align:right;font-weight:500;font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:0.14em;text-transform:uppercase">From</th>
          <th style="padding:8px 4px;text-align:right;font-weight:500;font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:0.14em;text-transform:uppercase">To</th>
          <th style="padding:8px 4px;text-align:right;font-weight:500;font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:0.14em;text-transform:uppercase">Δ%</th>
          <th style="padding:8px 4px;text-align:right;font-weight:500;font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:0.14em;text-transform:uppercase">Δ Profit/mo</th>
          <th style="padding:8px 4px;text-align:center;font-weight:500;font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:0.14em;text-transform:uppercase">Quadrant</th>
          <th style="padding:8px 4px;text-align:center;font-weight:500;font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:0.14em;text-transform:uppercase">Market</th>
          <th style="padding:8px 4px;text-align:left;font-weight:500;font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:0.14em;text-transform:uppercase">Narrative</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>"""

    # ── Sensitivity block ─────────────────────────────────────────────────────
    cons_color = GREEN if audit.sens_conservative >= 0 else RUST
    base_color = GREEN if audit.sens_baseline >= 0 else RUST
    opt_color  = GREEN if audit.sens_optimistic >= 0 else RUST
    robust_bg  = GREEN_SOFT if "YES" in (audit.sens_robust or "") else RUST_SOFT
    robust_fg  = GREEN if "YES" in (audit.sens_robust or "") else RUST

    sens_html = f"""
    <div style="display:flex;align-items:center;gap:12px;margin:24px 0 10px;page-break-after:avoid">
      <span style="font-family:'JetBrains Mono',monospace;color:{SLATE_SOFT};font-size:10px;letter-spacing:0.14em">02</span>
      <span style="font-family:Fraunces,Georgia,serif;font-style:italic;color:{INK};font-size:18px;letter-spacing:-0.01em">Sensitivity check</span>
      <span style="flex:1;height:1px;background:{LINE}"></span>
    </div>
    <table style="width:100%;border-collapse:separate;border-spacing:10px 0;page-break-inside:avoid">
      <tr>
        <td style="width:33%;border:1px solid {LINE};border-radius:8px;padding:14px;text-align:center;background:{PAPER}">
          <div style="font-family:'JetBrains Mono',monospace;font-size:9.5px;color:{SLATE};letter-spacing:0.12em;text-transform:uppercase">Conservative (e×1.2)</div>
          <div style="font-family:Fraunces,Georgia,serif;font-weight:500;font-size:20px;color:{cons_color};margin-top:4px;letter-spacing:-0.02em">
            {'+' if audit.sens_conservative>=0 else ''}{_fmt_currency(audit.sens_conservative,currency)}
          </div>
        </td>
        <td style="width:33%;border:1.5px solid {INK};border-radius:8px;padding:14px;text-align:center;background:{CREAM}">
          <div style="font-family:'JetBrains Mono',monospace;font-size:9.5px;color:{SLATE};letter-spacing:0.12em;text-transform:uppercase">Baseline (e×1.0)</div>
          <div style="font-family:Fraunces,Georgia,serif;font-weight:500;font-size:20px;color:{base_color};margin-top:4px;letter-spacing:-0.02em">
            {'+' if audit.sens_baseline>=0 else ''}{_fmt_currency(audit.sens_baseline,currency)}
          </div>
        </td>
        <td style="width:33%;border:1px solid {LINE};border-radius:8px;padding:14px;text-align:center;background:{PAPER}">
          <div style="font-family:'JetBrains Mono',monospace;font-size:9.5px;color:{SLATE};letter-spacing:0.12em;text-transform:uppercase">Optimistic (e×0.8)</div>
          <div style="font-family:Fraunces,Georgia,serif;font-weight:500;font-size:20px;color:{opt_color};margin-top:4px;letter-spacing:-0.02em">
            {'+' if audit.sens_optimistic>=0 else ''}{_fmt_currency(audit.sens_optimistic,currency)}
          </div>
        </td>
      </tr>
    </table>
    <div style="background:{robust_bg};color:{robust_fg};border-radius:6px;padding:8px 14px;font-size:11.5px;font-weight:500;margin-top:8px">
      Recommendation robust? <em style="font-style:italic">{audit.sens_robust}</em>
    </div>"""

    # ── Next steps ────────────────────────────────────────────────────────────
    next_steps_html = f"""
    <div style="display:flex;align-items:center;gap:12px;margin:24px 0 10px;page-break-after:avoid">
      <span style="font-family:'JetBrains Mono',monospace;color:{SLATE_SOFT};font-size:10px;letter-spacing:0.14em">03</span>
      <span style="font-family:Fraunces,Georgia,serif;font-style:italic;color:{INK};font-size:18px;letter-spacing:-0.01em">Next steps</span>
      <span style="flex:1;height:1px;background:{LINE}"></span>
    </div>
    <ol style="font-size:12px;line-height:1.65;color:{INK_MID};padding-left:22px;margin:6px 0;page-break-inside:avoid">
      <li style="margin-bottom:6px"><b style="color:{INK}">Sequence, don't simultaneously change.</b> Start with the single highest-confidence raise.
          Hold the new price for two weeks. Measure traffic and revenue against the prior two weeks.</li>
      <li style="margin-bottom:6px"><b style="color:{INK}">Watch your Traffic Drivers.</b> The model caps these tightly. Don't override the cap without
          a clear plan — these items anchor customer perception of value across the rest of the menu.</li>
      <li><b style="color:{INK}">Re-run after one cycle.</b> Once you've implemented and observed, re-do the audit with the new
          numbers. Confidence tiers improve quickly once we have real before/after data.</li>
    </ol>
    <div style="background:{CREAM_DEEP};border-left:3px solid {OCHRE};padding:12px 16px;margin-top:14px;font-size:12px;line-height:1.55;page-break-inside:avoid;color:{INK}">
      <b style="font-family:Fraunces,Georgia,serif;font-style:italic;font-size:14px">Want help implementing this?</b><br>
      <span style="color:{INK_MID}">Reply to the email this report came in, or book a free 15-minute walkthrough:</span><br>
      <a href="{calendly_url}" style="color:{OCHRE_DEEP};font-weight:500;text-decoration:none;border-bottom:1px solid {OCHRE_SOFT}">{calendly_url}</a>
    </div>"""

    # ── Sign-off ──────────────────────────────────────────────────────────────
    signoff_html = f"""
    <div style="margin-top:24px;padding-top:14px;border-top:1px solid {LINE};font-size:11.5px;color:{INK_MID};page-break-inside:avoid">
      Prepared by <b style="font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;color:{INK}">{consultant_name}</b> · MarginLab Pricing Lab<br>
      <span style="color:{SLATE};font-size:10.5px">{consultant_email}</span>
    </div>"""

    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Geist:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    @page {{
      size: A4 landscape;
      margin: 14mm 14mm 22mm 14mm;
      @bottom-center {{
        content: "{watermark_text}";
        font-size: 8px;
        color: {SLATE_SOFT};
        font-family: Geist, Arial, sans-serif;
        font-style: italic;
      }}
    }}
    body {{
      font-family: Geist, Arial, sans-serif;
      font-size: 12px;
      color: {INK};
      margin: 0; padding: 0;
      background: {PAPER};
    }}
    .masthead {{
      border-bottom: 2px solid {INK};
      padding-bottom: 16px;
      margin-bottom: 22px;
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
    }}
    .masthead .left {{
      flex: 1;
    }}
    .masthead h1.cafe {{
      font-family: Fraunces, Georgia, serif;
      font-weight: 500;
      font-size: 36px;
      color: {INK};
      margin: 0;
      letter-spacing: -0.025em;
      line-height: 1.05;
    }}
    .masthead .subtitle {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 10px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: {OCHRE_DEEP};
      margin-top: 8px;
    }}
    .masthead .right {{
      text-align: right;
    }}
    .masthead .brand {{
      font-family: Fraunces, Georgia, serif;
      font-style: italic;
      font-weight: 600;
      font-size: 22px;
      color: {INK};
      letter-spacing: -0.01em;
    }}
    .masthead .dateline {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 9.5px;
      color: {SLATE};
      margin-top: 4px;
      letter-spacing: 0.1em;
    }}
    table {{ page-break-inside: auto; }}
    tr {{ page-break-inside: avoid; page-break-after: auto; }}
    thead {{ display: table-header-group; }}
  </style>
</head>
<body>
  <div class="masthead">
    <div class="left">
      <h1 class="cafe">{display_cafe}</h1>
      <div class="subtitle">Pricing audit · Prepared {date_str}</div>
    </div>
    <div class="right">
      <div class="brand">MarginLab</div>
      <div class="dateline">PRICING LAB</div>
    </div>
  </div>

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
