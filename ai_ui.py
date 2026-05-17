import streamlit as st


def render_ai_verdict_tab(ticker, analysis):
    """
    AI Final Verdict Hub — Full decision display with reasoning chain and trade plan.
    Trade Plan features: 4 TP levels, pip distance, R:R ladder, partial close strategy.
    """
    decision = analysis.get('decision', 'STANDBY')
    color     = analysis.get('color', '#888')
    action    = analysis.get('action', '—')
    conf      = int(analysis.get('confidence', 0))
    plan      = analysis.get('plan', {})
    reasons   = analysis.get('reasons', [])
    q_val     = analysis.get('q_val', 0)

    icons = {
        "EXECUTE BUY":   "🟢",
        "BULLISH BIAS":  "🔵",
        "EXECUTE SELL":  "🔴",
        "BEARISH BIAS":  "🟠",
        "DANGER ZONE":   "⚠️",
        "STANDBY":       "⚪",
    }
    icon = icons.get(decision, "❔")

    # ── 1. AI VERDICT HERO CARD ──────────────────────────────
    is_execute = decision in ("EXECUTE BUY", "EXECUTE SELL")
    pulse_anim = "animation: pulse 1.5s infinite;" if is_execute else ""

    st.markdown(f"""
        <style>
            @keyframes pulse {{
                0%,100% {{ box-shadow: 0 0 20px {color}33; }}
                50%      {{ box-shadow: 0 0 50px {color}88; }}
            }}
        </style>
        <div style="background:linear-gradient(135deg,rgba(0,0,0,0.7),rgba(255,255,255,0.02));
                    padding:35px 30px; border-radius:20px; border:1px solid {color}55;
                    text-align:center; margin-bottom:24px; {pulse_anim}">
            <p style="font-size:11px;color:#555;letter-spacing:4px;font-family:'Orbitron';margin:0;">
                🧠 AI FINAL VERDICT — {ticker.replace('=X','').replace('-USD','').replace('=F','')}
            </p>
            <div style="font-size:52px; margin:12px 0;">{icon}</div>
            <h1 style="font-family:'Orbitron',sans-serif; font-size:36px; color:{color};
                       margin:0; font-weight:900; letter-spacing:2px;">{decision}</h1>
            <p style="color:#ccc; font-size:14px; margin-top:14px; font-style:italic; max-width:600px; margin-left:auto; margin-right:auto;">
                "{action}"
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── 2. CONFIDENCE METER ───────────────────────────────────
    conf_color = "#00ffcc" if conf >= 70 else ("#FFD700" if conf >= 45 else "#ff4b4b")
    st.markdown(f"""
        <div style="margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span style="font-family:'Orbitron';font-size:10px;color:#555;letter-spacing:2px;">AI CONFIDENCE LEVEL</span>
                <span style="font-family:'JetBrains Mono';font-size:14px;color:{conf_color};font-weight:bold;">{conf}%</span>
            </div>
            <div style="background:#111; border-radius:4px; height:8px; overflow:hidden;">
                <div style="width:{conf}%; height:100%; background:linear-gradient(90deg,{conf_color}88,{conf_color});
                             border-radius:4px; transition:width 0.5s;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── 3. QUANTUM SCORE QUICK VIEW ────────────────────────────
    q_color   = "#00ffcc" if q_val >= 6 else ("#ff4b4b" if q_val <= -6 else "#888")
    fib_color = "#00ffcc" if analysis.get('is_near_fib') else "#444"
    bull_n    = analysis.get('bull_fvg', 0)
    bear_n    = analysis.get('bear_fvg', 0)
    smc_color = "#00ffcc" if (q_val > 0 and bull_n > 0) or (q_val < 0 and bear_n > 0) else "#444"
    
    pa_score = analysis.get('pa_score', 0)
    pa_signal = analysis.get('pa_signal', 'NONE')
    pa_color = "#00ffcc" if pa_score > 0 else ("#ff4b4b" if pa_score < 0 else "#444")

    ca, cb, cc, cd = st.columns(4)
    with ca:
        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);padding:16px;border-radius:12px;
                                    border-top:3px solid {q_color};text-align:center;">
            <p style="color:#444;font-size:9px;margin:0;font-family:'Orbitron';">QUANTUM POWER</p>
            <h2 style="color:{q_color};margin:6px 0;font-family:'JetBrains Mono';">{q_val:+}</h2>
            <p style="color:#555;font-size:9px;">Max ±15 | Threshold ±6</p>
        </div>""", unsafe_allow_html=True)
    with cb:
        fib_txt = "GOLDEN ZONE ✓" if analysis.get('is_floor') or analysis.get('is_near_fib') else "MID-AIR"
        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);padding:16px;border-radius:12px;
                                    border-top:3px solid {fib_color};text-align:center;">
            <p style="color:#444;font-size:9px;margin:0;font-family:'Orbitron';">FIBONACCI ZONE</p>
            <h2 style="color:{fib_color};margin:6px 0;font-size:18px;">{fib_txt}</h2>
            <p style="color:#555;font-size:9px;">61.8% / 78.6% proximity</p>
        </div>""", unsafe_allow_html=True)
    with cc:
        smc_txt = f"🟢 {bull_n} Bull FVG" if bull_n > 0 else (f"🔴 {bear_n} Bear FVG" if bear_n > 0 else "No FVG")
        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);padding:16px;border-radius:12px;
                                    border-top:3px solid {smc_color};text-align:center;">
            <p style="color:#444;font-size:9px;margin:0;font-family:'Orbitron';">SMC / FVG ZONES</p>
            <h2 style="color:{smc_color};margin:6px 0;font-size:18px;">{smc_txt}</h2>
            <p style="color:#555;font-size:9px;">Institutional footprint</p>
        </div>""", unsafe_allow_html=True)
    with cd:
        pa_icon = "🔥 " if pa_score != 0 else ""
        pa_txt = pa_signal.replace("_", " ") if pa_signal != "NONE" else "NO PA SIGNAL"
        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);padding:16px;border-radius:12px;
                                    border-top:3px solid {pa_color};text-align:center;">
            <p style="color:#444;font-size:9px;margin:0;font-family:'Orbitron';">PRICE ACTION (PA)</p>
            <h2 style="color:{pa_color};margin:6px 0;font-size:14px;font-family:'Orbitron';">{pa_icon}{pa_txt}</h2>
            <p style="color:#555;font-size:9px;">Rejection / Sweep</p>
        </div>""", unsafe_allow_html=True)

    # ── 4. TRADE EXECUTION PLAN ────────────────────────────────
    if plan.get('entry', 0) > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        _render_trade_plan(ticker, decision, color, plan)

    # ── 5. AI REASONING CHAIN ─────────────────────────────────
    if reasons:
        st.markdown("<br><p style='font-family:Orbitron;font-size:10px;color:#444;letter-spacing:2px;'>AI REASONING CHAIN</p>", unsafe_allow_html=True)
        reasons_html = "".join([
            f'<div style="padding:10px 14px; margin-bottom:8px; background:rgba(255,255,255,0.02); '
            f'border-radius:8px; border-left:3px solid {color}55; color:#aaa; font-size:12px; line-height:1.6;">'
            f'{r}</div>' for r in reasons
        ])
        st.markdown(reasons_html, unsafe_allow_html=True)

    # ── 6. FINAL BANNER ───────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if conf >= 70 and decision in ("EXECUTE BUY", "EXECUTE SELL"):
        st.success(f"🔥 **HIGH CONVICTION SETUP** — AI Confidence {conf}%. Window eksekusi terbuka.")
    elif conf >= 50:
        st.warning(f"⚖️ **MODERATE SETUP** — Bias terdeteksi, konfluensi belum penuh. Pertimbangkan posisi kecil.")
    elif decision == "DANGER ZONE":
        st.error(f"⚠️ **DANGER ZONE** — Sinyal tinggi tapi konfluensi lemah. Risiko tinggi.")
    else:
        st.info(f"🛑 **STANDBY MODE** — Market noise. Tidak ada setup premium saat ini.")


# ── TRADE PLAN RENDERER ──────────────────────────────────────────────────────

def _render_trade_plan(ticker, decision, color, plan):
    """Render the full trade execution plan with price ladder, pip distance, R:R."""
    is_buy    = plan.get('direction', 'BUY') == 'BUY'
    is_crypto = '-USD' in ticker
    entry     = plan['entry']

    def fmt(v):
        if v == 0: return "—"
        if is_crypto and v < 0.01:   return f"${v:,.8f}"
        if is_crypto and v < 100:    return f"${v:,.4f}"
        if is_crypto:                return f"${v:,.2f}"
        if entry > 10_000:           return f"{v:,.2f}"   # BTC / Gold
        return f"{v:,.5f}"

    def fmt_pips(p):
        if p == 0: return "—"
        if p >= 1000: return f"{p:,.0f}"
        return f"{p:.1f}"

    # Header
    st.markdown(f"""
        <p style='font-family:Orbitron;font-size:10px;color:#444;letter-spacing:2px;margin-bottom:16px;'>
            📐 TRADE EXECUTION PLAN — MIN 3:1 R:R ENFORCED
        </p>
    """, unsafe_allow_html=True)

    # ── PRICE LADDER ─────────────────────────────────────────
    rr3   = plan.get('rr3', 0)
    rr4   = plan.get('rr4', 0)
    rr_ok = rr3 >= 2.8  # tolerance for float rounding

    sl_pips  = fmt_pips(plan.get('pips_sl', 0))
    tp1_pips = fmt_pips(plan.get('pips_tp1', 0))
    tp2_pips = fmt_pips(plan.get('pips_tp2', 0))
    tp3_pips = fmt_pips(plan.get('pips_tp3', 0))
    tp4_pips = fmt_pips(plan.get('pips_tp4', 0))

    # Color theming per R:R level
    rr1_color = "#aaaaaa"
    rr2_color = "#FFD700"
    rr3_color = "#00ffcc"
    rr4_color = "#ff00ff"

    st.markdown(f"""
        <style>
            .plan-row {{
                display: flex;
                align-items: center;
                margin-bottom: 10px;
                border-radius: 10px;
                overflow: hidden;
            }}
            .plan-label {{
                font-family: 'Orbitron', sans-serif;
                font-size: 9px;
                letter-spacing: 2px;
                padding: 14px 12px;
                min-width: 90px;
                text-align: center;
            }}
            .plan-price {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 16px;
                font-weight: bold;
                padding: 14px 16px;
                flex: 1;
            }}
            .plan-pips {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                padding: 14px 10px;
                min-width: 90px;
                text-align: center;
                color: #777;
            }}
            .plan-rr {{
                font-family: 'Orbitron', monospace;
                font-size: 13px;
                font-weight: 900;
                padding: 14px 16px;
                min-width: 80px;
                text-align: center;
                border-radius: 0 10px 10px 0;
            }}
            .plan-divider {{
                text-align: center;
                color: #333;
                font-size: 18px;
                margin: 2px 0;
            }}
        </style>

        <!-- TP3: 3:1 Runner -->
        <div class="plan-row" style="background:rgba(255,0,255,0.07);border:1px solid {rr4_color}33;">
            <div class="plan-label" style="background:rgba(255,0,255,0.12);color:{rr4_color};">TP 3<br><span style='font-size:8px;'>RUNNER</span></div>
            <div class="plan-price" style="color:#eee;">{fmt(plan.get('tp3', 0))}</div>
            <div class="plan-pips"><span style='color:#555;font-size:9px;'>PIPS</span><br>{tp3_pips}</div>
            <div class="plan-rr" style="background:rgba(255,0,255,0.15);color:{rr4_color};">1:{plan.get('rr3', 0):.1f}</div>
        </div>

        <!-- TP2: 2:1 Primary Target -->
        <div class="plan-row" style="background:rgba(0,255,204,0.07);border:1px solid {rr3_color}55;">
            <div class="plan-label" style="background:rgba(0,255,204,0.12);color:{rr3_color};">TP 2<br><span style='font-size:8px;'>TARGET ✓</span></div>
            <div class="plan-price" style="color:#eee;">{fmt(plan.get('tp2', 0))}</div>
            <div class="plan-pips"><span style='color:#555;font-size:9px;'>PIPS</span><br>{tp2_pips}</div>
            <div class="plan-rr" style="background:rgba(0,255,204,0.15);color:{rr3_color};">1:{plan.get('rr2', 0):.1f}</div>
        </div>

        <!-- TP1: 1:1 -->
        <div class="plan-row" style="background:rgba(255,255,255,0.03);border:1px solid #33333355;">
            <div class="plan-label" style="background:rgba(255,255,255,0.05);color:{rr1_color};">TP 1<br><span style='font-size:8px;'>SCALP</span></div>
            <div class="plan-price" style="color:#eee;">{fmt(plan.get('tp1', 0))}</div>
            <div class="plan-pips"><span style='color:#555;font-size:9px;'>PIPS</span><br>{tp1_pips}</div>
            <div class="plan-rr" style="background:rgba(255,255,255,0.05);color:{rr1_color};">1:{plan.get('rr1', 0):.1f}</div>
        </div>

        <!-- ENTRY -->
        <div class="plan-row" style="background:rgba(255,255,255,0.06);border:2px solid {color}88;">
            <div class="plan-label" style="background:{color}22;color:{color};">ENTRY<br><span style='font-size:8px;'>ZONE</span></div>
            <div class="plan-price" style="color:{color};font-size:20px;">{fmt(entry)}</div>
            <div class="plan-pips"><span style='color:#555;font-size:9px;'>STATUS</span><br><b style="color:#fff;">{plan.get('entry_status', 'WAITING')}</b></div>
            <div class="plan-rr" style="background:{color}22;color:{color};">BASE</div>
        </div>

        <!-- STOP LOSS -->
        <div class="plan-row" style="background:rgba(255,75,75,0.07);border:1px solid #ff4b4b44;">
            <div class="plan-label" style="background:rgba(255,75,75,0.12);color:#ff4b4b;">STOP<br><span style='font-size:8px;'>LOSS</span></div>
            <div class="plan-price" style="color:#ff4b4b;">{fmt(plan.get('sl', 0))}</div>
            <div class="plan-pips"><span style='color:#555;font-size:9px;'>PIPS</span><br>-{sl_pips}</div>
            <div class="plan-rr" style="background:rgba(255,75,75,0.12);color:#ff4b4b;">1:1 Risk</div>
        </div>
    """, unsafe_allow_html=True)

    # ── R:R SUMMARY BAR ──────────────────────────────────────
    rr2   = plan.get('rr2', 0)
    rr2_ok = rr2 >= 1.8  # tolerance for float rounding
    rr2_badge_color = "#00ffcc" if rr2_ok else "#FFD700"
    rr2_badge_text  = f"✅ 1:{rr2:.1f} — Target terpenuhi" if rr2_ok else f"⚠️ 1:{rr2:.1f} — Di bawah ideal"
    
    # Check if entry is near
    entry_status = plan.get("entry_status", "")
    anim_css = "animation: blink 1s infinite alternate;" if "FRESH MEAT" in entry_status else ""
    status_bg = "#ff00ff22" if "FRESH" in entry_status else "#222"
    
    st.markdown(f"""
        <style>
        @keyframes blink {{
            from {{ opacity: 1; }}
            to {{ opacity: 0.5; }}
        }}
        </style>
        <div style="margin-top:12px;padding:14px 20px;background:rgba(0,0,0,0.4);border-radius:12px;
                    border:1px solid #222;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
            <div>
                <span style="font-family:'Orbitron';font-size:9px;color:#555;letter-spacing:2px;">HEADLINE R:R (TP2)</span><br>
                <span style="font-family:'JetBrains Mono';font-size:22px;font-weight:bold;color:{rr2_badge_color};">
                    1 : {rr2:.1f}
                </span>
            </div>
            <div style="background:{status_bg}; padding: 6px 12px; border-radius: 6px; {anim_css}">
                <span style="font-family:'Orbitron';font-size:9px;color:#ccc;letter-spacing:2px;">ACTION STATUS</span><br>
                <span style="font-family:'JetBrains Mono';font-size:16px;font-weight:bold;color:#fff;">
                    {entry_status}
                </span>
            </div>
            <div>
                <span style="font-family:'Orbitron';font-size:9px;color:#555;letter-spacing:2px;">RISK (SL) DISTANCE</span><br>
                <span style="font-family:'JetBrains Mono';font-size:22px;font-weight:bold;color:#ff4b4b;">
                    {sl_pips} pips
                </span>
            </div>
            <div style="text-align:right;">
                <span style="font-size:12px;color:{rr2_badge_color};">{rr2_badge_text}</span><br>
                <span style="font-size:10px;color:#444;">Minimum ideal: 1:2.0</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── PARTIAL CLOSE STRATEGY ────────────────────────────────
    st.markdown(f"""
        <div style="margin-top:12px;padding:14px 20px;background:rgba(255,255,255,0.02);
                    border-radius:12px;border-left:3px solid #FFD700;border:1px solid #FFD70022;">
            <p style="font-family:'Orbitron';font-size:9px;color:#FFD700;letter-spacing:2px;margin:0 0 10px;">
                📋 PARTIAL CLOSE STRATEGY
            </p>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;font-size:11px;color:#888;">
                <div style="background:rgba(255,255,255,0.03);padding:8px 10px;border-radius:8px;text-align:center;">
                    <div style="color:#aaa;font-size:9px;">TP1 Hit</div>
                    <div style="color:#eee;font-weight:bold;">Close 50%</div>
                    <div style="color:#555;font-size:9px;">Lock scalp profit</div>
                </div>
                <div style="background:rgba(0,255,204,0.05);padding:8px 10px;border-radius:8px;text-align:center;">
                    <div style="color:#00ffcc;font-size:9px;">TP2 Hit</div>
                    <div style="color:#eee;font-weight:bold;">Close 30%</div>
                    <div style="color:#555;font-size:9px;">Headline Target</div>
                </div>
                <div style="background:rgba(255,0,255,0.05);padding:8px 10px;border-radius:8px;text-align:center;">
                    <div style="color:#ff00ff;font-size:9px;">TP3 Hit</div>
                    <div style="color:#eee;font-weight:bold;">Close 20%</div>
                    <div style="color:#555;font-size:9px;">Let runner free</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)