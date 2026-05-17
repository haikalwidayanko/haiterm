import streamlit as st


def render_quantum_tab(ticker, df, score_res, macro, sd, *args):
    """Quantum V12 UI — Full indicator display."""
    total = score_res.get('total', 0)
    details = score_res.get('details', {})
    audit   = score_res.get('audit', {})
    last    = df.iloc[-1]

    # Color scheme
    if   total >= 8:  color = "#00ffcc"; label = "STRONG BULLISH SIGNAL"; glow = "0 0 40px #00ffcc44"
    elif total >= 5:  color = "#a3ffeb"; label = "BULLISH BIAS"; glow = "0 0 20px #a3ffeb33"
    elif total <= -8: color = "#ff4b4b"; label = "STRONG BEARISH SIGNAL"; glow = "0 0 40px #ff4b4b44"
    elif total <= -5: color = "#ff8585"; label = "BEARISH BIAS"; glow = "0 0 20px #ff858533"
    else:             color = "#888888"; label = "NEUTRAL / MONITORING"; glow = "none"

    # ── QUANTUM SCORE HERO ────────────────────────────────────
    st.markdown(f"""
        <div style="text-align:center; padding:35px 20px; border-radius:16px;
                    background:linear-gradient(135deg,rgba(0,0,0,0.6),rgba(255,255,255,0.02));
                    border:1px solid {color}44; box-shadow:{glow}; margin-bottom:24px;">
            <p style="font-family:'Orbitron',sans-serif; font-size:11px; color:{color};
                       letter-spacing:5px; margin:0; opacity:0.8;">QUANTUM BIAS SCORE</p>
            <h1 style="font-family:'Orbitron',sans-serif; font-size:80px; color:{color};
                       margin:8px 0; font-weight:900; line-height:1;">{total:+}</h1>
            <p style="font-family:'Orbitron',sans-serif; font-size:13px; color:{color};
                       letter-spacing:3px; margin:0;">{label}</p>
            <p style="font-size:10px; color:#555; margin-top:8px;">Score range: ±15 | Signal threshold: ±6</p>
        </div>
    """, unsafe_allow_html=True)

    # ── LIVE MARKET INDICATORS ────────────────────────────────
    rsi      = last.get('RSI', 0)
    stoch_k  = last.get('StochRSI_K', 0)
    adx_val  = last.get('ADX', 0)
    bb_pctb  = last.get('BB_PctB', 0.5)
    wr_val   = last.get('Williams_R', -50)
    vwap_val = last.get('VWAP', 0)
    p_now    = last.get('Close', 0)

    def ind_card(label, value, suffix="", note="", c="#888"):
        return f"""<div style="background:rgba(255,255,255,0.03); padding:14px 12px; border-radius:10px;
                                border-bottom:3px solid {c}; text-align:center;">
            <p style="color:#555; font-size:9px; margin:0; font-family:'Orbitron'; letter-spacing:1px;">{label}</p>
            <b style="font-size:20px; color:{c}; font-family:'JetBrains Mono';">{value}{suffix}</b>
            <p style="color:#666; font-size:9px; margin:4px 0 0; font-family:'Public Sans';">{note}</p>
        </div>"""

    def _rsi_color(v): return "#00ffcc" if v > 55 else ("#ff4b4b" if v < 45 else "#888")
    def _wr_color(v):  return "#00ffcc" if v > -20 else ("#ff4b4b" if v < -80 else "#888")
    def _adx_color(v): return "#00ffcc" if v > 30 else ("#FFD700" if v > 20 else "#ff4b4b")
    def _bb_color(v):  return "#00ffcc" if v > 0.8 else ("#ff4b4b" if v < 0.2 else "#888")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(ind_card("RSI 14", f"{rsi:.1f}", "", "Overbought>70 | <30 Oversold", _rsi_color(rsi)), unsafe_allow_html=True)
    with c2: st.markdown(ind_card("StochRSI K", f"{stoch_k:.1f}", "", ">80 OB | <20 OS", "#00ffcc" if stoch_k > 50 else "#ff4b4b"), unsafe_allow_html=True)
    with c3: st.markdown(ind_card("ADX", f"{adx_val:.1f}", "", ">30 Strong | <20 Ranging", _adx_color(adx_val)), unsafe_allow_html=True)
    with c4: st.markdown(ind_card("BB %B", f"{bb_pctb:.2f}", "", ">1.0 OB | <0.0 OS", _bb_color(bb_pctb)), unsafe_allow_html=True)
    with c5: st.markdown(ind_card("Williams %R", f"{wr_val:.1f}", "", ">-20 OB | <-80 OS", _wr_color(wr_val)), unsafe_allow_html=True)

    # Ichimoku status
    span_a = last.get('Ichi_SpanA', 0)
    span_b = last.get('Ichi_SpanB', 0)
    tenkan = last.get('Ichi_Tenkan', 0)
    kijun  = last.get('Ichi_Kijun', 0)
    cloud_top, cloud_bot = max(span_a, span_b), min(span_a, span_b)
    ichi_pos = "ABOVE CLOUD ✓" if p_now > cloud_top else ("BELOW CLOUD ✗" if p_now < cloud_bot else "INSIDE CLOUD ⚠")
    ichi_col = "#00ffcc" if p_now > cloud_top else ("#ff4b4b" if p_now < cloud_bot else "#FFD700")
    vwap_col = "#00ffcc" if p_now > vwap_val else "#ff4b4b"

    c6, c7, c8 = st.columns(3)
    with c6: st.markdown(ind_card("ICHIMOKU", ichi_pos, "", f"Tenkan:{tenkan:.5f} | Kijun:{kijun:.5f}", ichi_col), unsafe_allow_html=True)
    with c7: st.markdown(ind_card("VWAP", f"{vwap_val:.5f}", "", "Above=Bullish | Below=Bearish", vwap_col), unsafe_allow_html=True)
    with c8:
        macd_h = last.get('MACD_Hist', 0)
        macd_col = "#00ffcc" if macd_h > 0 else "#ff4b4b"
        st.markdown(ind_card("MACD HIST", f"{macd_h:.5f}", "", "Positive=Bull | Negative=Bear", macd_col), unsafe_allow_html=True)

    st.divider()

    # ── PARAMETER BREAKDOWN ───────────────────────────────────
    st.markdown("<p style='font-family:Orbitron;font-size:11px;color:#444;letter-spacing:2px;margin-bottom:16px;'>PARAMETER BREAKDOWN</p>", unsafe_allow_html=True)

    all_params = list(details.keys())
    row1, row2 = all_params[:5], all_params[5:]
    cols1 = st.columns(len(row1))
    for i, m in enumerate(row1):
        val  = details.get(m, 0)
        note = audit.get(m, "—")
        mc   = "#00ffcc" if val > 0 else ("#ff4b4b" if val < 0 else "#555")
        with cols1[i]:
            st.markdown(f"""<div style="background:rgba(255,255,255,0.03);padding:14px 10px;border-radius:10px;
                                        border-bottom:3px solid {mc};min-height:130px;">
                <p style="color:#444;font-size:9px;margin:0;font-family:'Orbitron';letter-spacing:1px;">{m.upper()}</p>
                <h2 style="color:{mc};margin:8px 0;font-family:'JetBrains Mono';font-size:26px;">{val:+}</h2>
                <p style="color:#666;font-size:9px;line-height:1.4;margin-top:8px;">{note}</p>
            </div>""", unsafe_allow_html=True)

    if row2:
        cols2 = st.columns(len(row2))
        for i, m in enumerate(row2):
            val  = details.get(m, 0)
            note = audit.get(m, "—")
            mc   = "#00ffcc" if val > 0 else ("#ff4b4b" if val < 0 else "#555")
            with cols2[i]:
                st.markdown(f"""<div style="background:rgba(255,255,255,0.03);padding:14px 10px;border-radius:10px;
                                            border-bottom:3px solid {mc};min-height:110px;">
                    <p style="color:#444;font-size:9px;margin:0;font-family:'Orbitron';letter-spacing:1px;">{m.upper()}</p>
                    <h2 style="color:{mc};margin:8px 0;font-family:'JetBrains Mono';font-size:26px;">{val:+}</h2>
                    <p style="color:#666;font-size:9px;line-height:1.4;margin-top:8px;">{note}</p>
                </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("⚛️ Quantum V12 | 9 Dimensions: EMA Stack, StochRSI, MACD, Bollinger, Ichimoku, VWAP, Williams %R, ADX, ATR | Score ±15 | Signal ≥ ±6")