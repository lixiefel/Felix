"""
consult_walkthrough.py — MarginLab
─────────────────────────────────────────────────────────────────────────────
Client-facing pricing walkthrough. This is the surface you screen-share with a
café owner during a pitch, or share read-only via a private link afterwards.

It reuses the engine's AuditResult / ItemResult objects and the Design System v3
tokens already loaded in app.py (--ink, --cream, --ochre, --green, --rust ...).
All new CSS is scoped under `.wt-` so it cannot collide with existing styles.

Wiring (see bottom of file for the 3 edits in app.py):
    from consult_walkthrough import inject_walkthrough_css, render_walkthrough
    inject_walkthrough_css()
    render_walkthrough(audit, currency, cafe_name,
                       fmt_money=_currency_display, fmt_pct=_pct_display,
                       client_mode=False)
"""

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# CSS — scoped, additive. Call once per page render.
# ─────────────────────────────────────────────────────────────────────────────
def inject_walkthrough_css():
    st.markdown("""
<style>
  /* ── WALKTHROUGH (client-facing) ─────────────────────────────── */
  .wt-shell { max-width: 1040px; margin: 0 auto; }

  /* Section index / nav rail */
  .wt-index {
    display: flex; flex-wrap: wrap; gap: 0; align-items: center;
    border: 1px solid var(--line); border-radius: 999px;
    background: var(--paper); padding: 5px; margin: 4px 0 30px;
    box-shadow: var(--shadow-sm);
  }
  .wt-index a {
    font-family: "JetBrains Mono", monospace; font-size: 10.5px;
    letter-spacing: 0.13em; text-transform: uppercase;
    color: var(--slate); text-decoration: none;
    padding: 8px 15px; border-radius: 999px; transition: all .18s ease;
    white-space: nowrap;
  }
  .wt-index a:hover { color: var(--ink); background: var(--cream-deep); }

  /* Title band */
  .wt-band {
    border-top: 2px solid var(--ink);
    padding: 22px 0 26px; margin-bottom: 6px;
  }
  .wt-band .eyebrow {
    font-family: "JetBrains Mono", monospace; font-size: 11px;
    letter-spacing: 0.22em; text-transform: uppercase; color: var(--ochre-deep);
    margin-bottom: 12px;
  }
  .wt-band h1 {
    font-family: "Fraunces", serif !important; font-weight: 500;
    font-size: 40px; line-height: 1.08; color: var(--ink);
    margin: 0; letter-spacing: -0.02em;
  }
  .wt-band h1 em { font-style: italic; color: var(--ochre-deep); font-weight: 400; }
  .wt-band .meta {
    margin-top: 14px; font-size: 13px; color: var(--slate);
    display: flex; gap: 22px; flex-wrap: wrap;
  }
  .wt-band .meta b { color: var(--ink-mid); font-weight: 500; }

  /* Section heading */
  .wt-sec {
    font-family: "JetBrains Mono", monospace; font-size: 11px;
    letter-spacing: 0.2em; text-transform: uppercase; color: var(--slate);
    margin: 46px 0 16px; padding-bottom: 9px;
    border-bottom: 1px solid var(--line); display: flex;
    justify-content: space-between; align-items: baseline;
  }
  .wt-sec span:last-child { color: var(--slate-soft); letter-spacing: 0.1em; }

  /* Hero headline result */
  .wt-hero {
    background: var(--ink); border-radius: 16px; padding: 36px 40px;
    color: var(--cream); box-shadow: var(--shadow-lg);
    display: flex; justify-content: space-between; align-items: flex-end;
    gap: 30px; flex-wrap: wrap;
  }
  .wt-hero .lead { flex: 1; min-width: 280px; }
  .wt-hero .lead .k {
    font-family: "JetBrains Mono", monospace; font-size: 10.5px;
    letter-spacing: 0.2em; text-transform: uppercase;
    color: var(--ochre); margin-bottom: 14px;
  }
  .wt-hero .lead .big {
    font-family: "Fraunces", serif; font-style: italic; font-weight: 400;
    font-size: 64px; line-height: 0.95; color: var(--cream);
    letter-spacing: -0.02em;
  }
  .wt-hero .lead .unit {
    font-size: 14px; color: var(--slate-soft); margin-top: 12px;
    font-family: "Geist", sans-serif;
  }
  .wt-hero .lead .unit b { color: var(--ochre); font-weight: 500; }
  .wt-hero .side { text-align: right; min-width: 150px; }
  .wt-hero .side .conf-pill {
    display: inline-block; font-family: "JetBrains Mono", monospace;
    font-size: 11px; letter-spacing: 0.14em; padding: 7px 16px;
    border-radius: 999px; font-weight: 500;
  }
  .wt-hero .side .annual {
    margin-top: 18px; font-size: 13px; color: var(--slate-soft);
  }
  .wt-hero .side .annual em {
    display: block; font-family: "Fraunces", serif; font-style: italic;
    font-size: 26px; color: var(--cream); margin-top: 4px;
  }

  /* Plain-language summary line */
  .wt-summary {
    font-family: "Fraunces", serif; font-size: 19px; line-height: 1.5;
    color: var(--ink-soft); margin: 26px 4px 8px; font-weight: 400;
  }
  .wt-summary b { color: var(--ochre-deep); font-weight: 500; font-style: italic; }

  /* Before → After rows */
  .wt-baf { display: flex; flex-direction: column; gap: 4px; }
  .wt-row {
    display: grid; grid-template-columns: 190px 1fr 120px;
    align-items: center; gap: 18px;
    padding: 15px 4px; border-bottom: 1px solid var(--line-soft);
  }
  .wt-row .nm {
    font-family: "Fraunces", serif; font-size: 16px; color: var(--ink);
    font-weight: 500;
  }
  .wt-row .nm small {
    display: block; font-family: "JetBrains Mono", monospace; font-size: 9.5px;
    letter-spacing: 0.1em; text-transform: uppercase; color: var(--slate-soft);
    margin-top: 3px; font-weight: 400;
  }
  .wt-track { display: flex; flex-direction: column; gap: 7px; }
  .wt-bar { display: flex; align-items: center; gap: 10px; height: 20px; }
  .wt-bar .fill { height: 9px; border-radius: 999px; }
  .wt-bar .now  { background: var(--slate-soft); }
  .wt-bar .raise { background: var(--ochre); }
  .wt-bar .cut  { background: var(--rust); }
  .wt-bar .hold { background: var(--ink-mid); }
  .wt-bar .pl {
    font-family: "JetBrains Mono", monospace; font-size: 12px;
    color: var(--ink-mid); white-space: nowrap; min-width: 86px;
  }
  .wt-bar .tag {
    font-family: "JetBrains Mono", monospace; font-size: 8.5px;
    letter-spacing: 0.1em; text-transform: uppercase; color: var(--slate);
    width: 34px;
  }
  .wt-row .dlt { text-align: right; }
  .wt-row .dlt .pct {
    font-family: "Fraunces", serif; font-size: 20px; font-weight: 500;
  }
  .wt-row .dlt .pct.up { color: var(--green); }
  .wt-row .dlt .pct.dn { color: var(--rust); }
  .wt-row .dlt .pct.fl { color: var(--slate); }
  .wt-row .dlt .pf {
    font-family: "JetBrains Mono", monospace; font-size: 11px;
    color: var(--slate); margin-top: 2px;
  }

  /* Insight callouts */
  .wt-insights { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .wt-call {
    background: var(--paper); border: 1px solid var(--line);
    border-left: 3px solid var(--ochre); border-radius: 10px;
    padding: 18px 20px; box-shadow: var(--shadow-sm);
  }
  .wt-call .h {
    font-family: "JetBrains Mono", monospace; font-size: 10px;
    letter-spacing: 0.16em; text-transform: uppercase; color: var(--ochre-deep);
    margin-bottom: 9px;
  }
  .wt-call .b {
    font-family: "Fraunces", serif; font-size: 17px; line-height: 1.45;
    color: var(--ink); font-weight: 400;
  }
  .wt-call .b b { color: var(--ochre-deep); font-weight: 600; }

  /* Scenario range bar */
  .wt-scenario {
    background: var(--cream-deep); border-radius: 12px; padding: 26px 28px;
    border: 1px solid var(--line);
  }
  .wt-scale { position: relative; height: 56px; margin: 18px 6px 6px; }
  .wt-scale .line {
    position: absolute; top: 50%; left: 0; right: 0; height: 3px;
    background: var(--ochre-soft); border-radius: 999px;
  }
  .wt-scale .pt {
    position: absolute; top: 50%; transform: translate(-50%, -50%);
    text-align: center;
  }
  .wt-scale .pt .dot {
    width: 12px; height: 12px; border-radius: 50%; margin: 0 auto;
    background: var(--ochre); border: 2px solid var(--cream);
  }
  .wt-scale .pt.base .dot {
    width: 18px; height: 18px; background: var(--ink);
  }
  .wt-scale .pt .lbl {
    position: absolute; top: 16px; left: 50%; transform: translateX(-50%);
    font-family: "JetBrains Mono", monospace; font-size: 10px;
    letter-spacing: 0.08em; color: var(--slate); white-space: nowrap;
  }
  .wt-scale .pt .v {
    position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
    font-family: "Fraunces", serif; font-size: 15px; color: var(--ink);
    white-space: nowrap; font-weight: 500;
  }
  .wt-scale .pt.base .v { font-size: 17px; }
  .wt-robust {
    margin-top: 20px; font-size: 13px; color: var(--ink-mid);
    display: flex; align-items: center; gap: 10px;
  }
  .wt-robust .yn {
    font-family: "Fraunces", serif; font-style: italic; font-weight: 500;
    padding: 3px 12px; border-radius: 999px; font-size: 14px;
  }

  /* Method & limits */
  .wt-limit {
    background: var(--paper); border: 1px solid var(--line);
    border-radius: 12px; padding: 24px 28px;
  }
  .wt-limit ol { margin: 14px 0 0; padding-left: 0; list-style: none; counter-reset: l; }
  .wt-limit li {
    counter-increment: l; position: relative; padding: 11px 0 11px 42px;
    border-top: 1px solid var(--line-soft); font-size: 14px; color: var(--ink-mid);
    line-height: 1.5;
  }
  .wt-limit li:first-child { border-top: none; }
  .wt-limit li::before {
    content: counter(l); position: absolute; left: 0; top: 11px;
    width: 26px; height: 26px; border-radius: 50%;
    background: var(--cream-deep); color: var(--ochre-deep);
    font-family: "JetBrains Mono", monospace; font-size: 12px; font-weight: 500;
    display: flex; align-items: center; justify-content: center;
  }
  .wt-limit li b { color: var(--ink); font-weight: 600; }
  .wt-hook {
    margin-top: 18px; padding: 16px 20px; border-radius: 10px;
    background: var(--ink); color: var(--cream); font-size: 14px; line-height: 1.5;
  }
  .wt-hook b { color: var(--ochre); }

  .wt-foot {
    margin: 40px 0 8px; padding-top: 18px; border-top: 1px solid var(--line);
    font-size: 12px; color: var(--slate-soft); line-height: 1.6;
  }

  @media (max-width: 720px) {
    .wt-row { grid-template-columns: 1fr; gap: 8px; }
    .wt-insights { grid-template-columns: 1fr; }
    .wt-band h1 { font-size: 30px; }
    .wt-hero .lead .big { font-size: 46px; }
  }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────
_CONF_BG = {"HIGH": "#DDE6DC", "MEDIUM": "#E8DCC4", "LOW": "#F0D9D4"}
_CONF_TC = {"HIGH": "#4A6B4A", "MEDIUM": "#9A7842", "LOW": "#9C4A3C"}


def _action_class(action: str) -> str:
    a = (action or "").lower()
    if "raise" in a:
        return "raise"
    if "cut" in a:
        return "cut"
    return "hold"


def _summary_sentence(audit, fmt_money, currency: str) -> str:
    """Plain-language one-liner an owner instantly understands."""
    lift = audit.monthly_lift or 0.0
    money = fmt_money(abs(lift), currency)
    n = audit.changes_count or "a few"
    if lift > 0:
        return (f"By adjusting <b>{n}</b> across your menu — not raising everything — "
                f"this rebalance is projected to add <b>{money} {currency} a month</b> "
                f"from the customers you already serve.")
    if lift < 0:
        return ("The current menu is close to balanced. The model finds little room to "
                "push without risking demand — the value here is protecting what works.")
    return ("The current menu is broadly well-priced. We'd focus on positioning and "
            "menu structure rather than price moves.")


# ─────────────────────────────────────────────────────────────────────────────
# main render
# ─────────────────────────────────────────────────────────────────────────────
def render_walkthrough(audit, currency, cafe_name="", *,
                       fmt_money, fmt_pct, client_mode=False, review_date=""):
    """
    audit       : engine.AuditResult
    currency    : str
    fmt_money   : callable(value, currency) -> str   (pass app._currency_display)
    fmt_pct     : callable(value) -> str              (pass app._pct_display)
    client_mode : True = read-only shared view (hides nothing structural, just framing)
    """
    if audit is None:
        st.info("Run an audit first — results will render here as a client walkthrough.")
        return

    cafe = cafe_name.strip() or "This café"
    conf = audit.confidence or "—"
    lift = audit.monthly_lift or 0.0
    sign = "+" if lift >= 0 else "−"
    annual = abs(lift) * 12

    st.markdown('<div class="wt-shell">', unsafe_allow_html=True)

    # ── Section index ─────────────────────────────────────────────
    st.markdown("""
    <div class="wt-index">
      <a href="#wt-opportunity">The opportunity</a>
      <a href="#wt-moves">Before → after</a>
      <a href="#wt-why">Why these moves</a>
      <a href="#wt-range">Confidence range</a>
      <a href="#wt-method">Method &amp; limits</a>
    </div>
    """, unsafe_allow_html=True)

    # ── Title band ────────────────────────────────────────────────
    meta_date = f'<span><b>Reviewed</b> {review_date}</span>' if review_date else ""
    st.markdown(f"""
    <div class="wt-band">
      <div class="eyebrow">MarginLab · Pricing Analysis</div>
      <h1>{cafe}: a menu <em>profit rebalance</em>.</h1>
      <div class="meta">
        <span><b>Currency</b> {currency}</span>
        <span><b>Items reviewed</b> {len(audit.items)}</span>
        {meta_date}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Hero result ───────────────────────────────────────────────
    st.markdown('<a id="wt-opportunity"></a>', unsafe_allow_html=True)
    st.markdown(f'<div class="wt-sec"><span>01 — The opportunity</span><span>Projected monthly impact</span></div>',
                unsafe_allow_html=True)
    st.markdown(f"""
    <div class="wt-hero">
      <div class="lead">
        <div class="k">Projected monthly Δ profit</div>
        <div class="big">{sign}{fmt_money(abs(lift), currency)}</div>
        <div class="unit">{currency} per month · <b>{fmt_pct(audit.lift_pct)}</b> on profit</div>
      </div>
      <div class="side">
        <div class="conf-pill" style="background:{_CONF_BG.get(conf,'#EFEAE0')};color:{_CONF_TC.get(conf,'#3D4862')}">
          {conf} confidence
        </div>
        <div class="annual">Indicative annual<em>{sign}{fmt_money(annual, currency)}</em></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="wt-summary">{_summary_sentence(audit, fmt_money, currency)}</div>',
                unsafe_allow_html=True)

    # ── Before → After ────────────────────────────────────────────
    st.markdown('<a id="wt-moves"></a>', unsafe_allow_html=True)
    st.markdown('<div class="wt-sec"><span>02 — Before → after</span><span>Per item</span></div>',
                unsafe_allow_html=True)

    items = audit.items or []
    max_price = max([1.0] + [max(i.price_from, i.price_to) for i in items])
    rows_html = ['<div class="wt-baf">']
    for it in items:
        cls = _action_class(it.action)
        w_now = max(2.0, (it.price_from / max_price) * 100)
        w_to = max(2.0, (it.price_to / max_price) * 100)
        dp = it.delta_pct or 0.0
        pct_cls = "up" if dp > 0 else ("dn" if dp < 0 else "fl")
        dp_sign = "+" if dp > 0 else ""
        pf_sign = "+" if (it.delta_profit_mo or 0) >= 0 else ""
        rows_html.append(f"""
        <div class="wt-row">
          <div class="nm">{it.name}<small>{it.quadrant} · {it.market}</small></div>
          <div class="wt-track">
            <div class="wt-bar"><span class="tag">Now</span>
              <span class="fill now" style="width:{w_now:.1f}%"></span>
              <span class="pl">{fmt_money(it.price_from, currency)}</span></div>
            <div class="wt-bar"><span class="tag">New</span>
              <span class="fill {cls}" style="width:{w_to:.1f}%"></span>
              <span class="pl">{fmt_money(it.price_to, currency)}</span></div>
          </div>
          <div class="dlt">
            <div class="pct {pct_cls}">{dp_sign}{fmt_pct(dp)}</div>
            <div class="pf">{pf_sign}{fmt_money(it.delta_profit_mo, currency)}/mo</div>
          </div>
        </div>""")
    rows_html.append('</div>')
    st.markdown("".join(rows_html), unsafe_allow_html=True)

    # ── Why these moves (insight callouts) ────────────────────────
    st.markdown('<a id="wt-why"></a>', unsafe_allow_html=True)
    st.markdown('<div class="wt-sec"><span>03 — Why these moves</span><span>The logic</span></div>',
                unsafe_allow_html=True)

    n_raise = sum(1 for i in items if _action_class(i.action) == "raise")
    n_cut = sum(1 for i in items if _action_class(i.action) == "cut")
    n_hold = len(items) - n_raise - n_cut
    above = sum(1 for i in items if "Above" in (i.market or ""))
    within = sum(1 for i in items if "Within" in (i.market or ""))
    below = sum(1 for i in items if "Below" in (i.market or ""))
    best = (audit.best_item or "").replace("Best item: ", "") or "—"

    calls = [
        ("It's a rebalance, not a hike",
         f"<b>{n_raise} up · {n_cut} down · {n_hold} held.</b> Margin shifts toward items "
         f"that can carry it, while everyday favourites stay sharp to protect footfall."),
        ("Where the gain concentrates",
         f"Most of the lift comes from <b>{best}</b> — a strong item that's currently "
         f"leaving margin on the table relative to its demand."),
        ("Still inside the local market",
         f"<b>{below} below · {within} within · {above} above</b> nearby pricing. Moves keep "
         f"you in a believable range, not out ahead of your street."),
        ("Built to be reversible",
         "Roll out the top 3 first, watch for two weeks, revert any item that slips. "
         "Nothing here is a one-way door."),
    ]
    cards = "".join(
        f'<div class="wt-call"><div class="h">{h}</div><div class="b">{b}</div></div>'
        for h, b in calls
    )
    st.markdown(f'<div class="wt-insights">{cards}</div>', unsafe_allow_html=True)

    # ── Confidence range ──────────────────────────────────────────
    st.markdown('<a id="wt-range"></a>', unsafe_allow_html=True)
    st.markdown('<div class="wt-sec"><span>04 — Confidence range</span><span>Stress test</span></div>',
                unsafe_allow_html=True)

    c = audit.sens_conservative or 0.0
    b = audit.sens_baseline or 0.0
    o = audit.sens_optimistic or 0.0
    lo, hi = min(c, b, o), max(c, b, o)
    span = (hi - lo) or 1.0

    def _pos(v):
        return 6 + ((v - lo) / span) * 88  # 6%..94% inset

    robust_yes = "YES" in (audit.sens_robust or "").upper()
    rb_bg, rb_tc = ("#DDE6DC", "#4A6B4A") if robust_yes else ("#F0D9D4", "#9C4A3C")
    st.markdown(f"""
    <div class="wt-scenario">
      <div style="font-family:'Fraunces',serif;font-size:17px;color:var(--ink)">
        If customers react more strongly than assumed, the gain holds up:
      </div>
      <div class="wt-scale">
        <div class="line"></div>
        <div class="pt" style="left:{_pos(c):.1f}%"><div class="v">{'+' if c>=0 else '−'}{fmt_money(abs(c),currency)}</div><div class="dot"></div><div class="lbl">Conservative</div></div>
        <div class="pt base" style="left:{_pos(b):.1f}%"><div class="v">{'+' if b>=0 else '−'}{fmt_money(abs(b),currency)}</div><div class="dot"></div><div class="lbl">Baseline</div></div>
        <div class="pt" style="left:{_pos(o):.1f}%"><div class="v">{'+' if o>=0 else '−'}{fmt_money(abs(o),currency)}</div><div class="dot"></div><div class="lbl">Optimistic</div></div>
      </div>
      <div class="wt-robust">Recommendation robust across scenarios?
        <span class="yn" style="background:{rb_bg};color:{rb_tc}">{audit.sens_robust or '—'}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Method & limits (the honest part = the sales hook) ─────────
    st.markdown('<a id="wt-method"></a>', unsafe_allow_html=True)
    st.markdown('<div class="wt-sec"><span>05 — Method &amp; limits</span><span>What this does &amp; doesn\'t see</span></div>',
                unsafe_allow_html=True)
    st.markdown(f"""
    <div class="wt-limit">
      <div style="font-size:14px;color:var(--ink-mid);line-height:1.55">
        This analysis combines your menu economics with category-benchmark demand
        sensitivity{(' (no live sales history was used, so it is directional)' if conf == 'LOW' else '')}.
        It is decision support, not a guarantee. Three things it deliberately can't see —
        and these are exactly what we layer in together on the walkthrough:
      </div>
      <ol>
        <li><b>Switching between your own items</b> — when a flat white moves, some customers shift to a latte. The model prices each item on its own.</li>
        <li><b>The basket effect</b> — a coffee price change can move pastry attach-rate too. The model only sees the coffee.</li>
        <li><b>Time-of-day &amp; weekday mix</b> — a 7am and a 3pm flat white are different products, averaged into one number here.</li>
      </ol>
      <div class="wt-hook">
        These three gaps are why pricing isn't a spreadsheet. On a <b>60-minute walkthrough</b>
        we read this against how your café actually trades — and turn the directional numbers
        into a confident 30-day plan.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="wt-foot">
      MarginLab · Menu profit engineering for independent cafés. Projections are estimates
      based on the data provided and benchmark demand assumptions; actual results vary with
      customer behaviour, seasonality, and competitor moves. Changes are implemented gradually
      and monitored. Confidence on this run: <b>{conf}</b>.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
