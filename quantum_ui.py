import streamlit as st


def render_quantum_tab(ticker, df_active, score_res, macro, sd, glow_class, status, news):
    """
    Layout Tab Quantum: Menampilkan skor bias teknikal dengan penjelasan (Audit Notes).
    """
    # --- 1. LOGIC: DYNAMIC COLORING ---
    total_score = score_res.get('total', 0)

    # Penentuan warna berdasarkan ambang batas (threshold)
    if total_score >= 6:
        accent_color = "#00ffcc"  # HIJAU NEON
        score_desc = "BULLISH CONFIRMATION"
        glow_shadow = "0 0 30px #00ffcc44"
    elif total_score <= -6:
        accent_color = "#ff4b4b"  # MERAH NEON
        score_desc = "BEARISH CONFIRMATION"
        glow_shadow = "0 0 30px #ff4b4b44"
    else:
        accent_color = "#ffffff"  # PUTIH
        score_desc = "NEUTRAL / MONITORING"
        glow_shadow = "none"

    # --- 2. HEADER: QUANTUM BIAS DISPLAY ---
    st.markdown(f"""
        <div style="text-align:center; padding:30px; border-radius:15px; background:rgba(255,255,255,0.02); border:1px solid {accent_color}33; box-shadow:{glow_shadow}; margin-bottom:25px;">
            <p style="font-family:'Orbitron'; font-size:12px; color:{accent_color}; letter-spacing:4px; margin:0;">QUANTUM BIAS SCORE</p>
            <h1 style="font-family:'Orbitron'; font-size:72px; color:{accent_color}; margin:10px 0; font-weight:900;">{total_score:+}</h1>
            <p style="font-family:'Orbitron'; font-size:14px; color:{accent_color}; letter-spacing:2px; margin:0; opacity:0.8;">{score_desc}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 3. MARKET INDICATORS (SUB-HEADER) ---
    last = df_active.iloc[-1]
    adx_val = last.get('ADX', 0)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:10px; border-left:3px solid #555;">
                <p style="color:#555; font-size:10px; margin:0; font-family:'Orbitron';">SIGNAL STATUS</p>
                <b style="font-size:18px; color:#eee; font-family:'Orbitron';">{status}</b>
            </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:10px; border-left:3px solid #888;">
                <p style="color:#555; font-size:10px; margin:0; font-family:'Orbitron';">TREND POWER (ADX)</p>
                <b style="font-size:18px; color:#eee; font-family:'JetBrains Mono';">{adx_val:.2f}</b>
            </div>
        """, unsafe_allow_html=True)

    with c3:
        # Indikator News Shield
        is_news_active = len(news) > 0 if isinstance(news, list) else False
        news_status = "⚠️ CAUTION" if is_news_active else "✅ CLEAR"
        news_color = "#ff4b4b" if is_news_active else "#00ffcc"
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:10px; border-left:3px solid {news_color};">
                <p style="color:#555; font-size:10px; margin:0; font-family:'Orbitron';">NEWS SHIELD</p>
                <b style="font-size:18px; color:{news_color}; font-family:'Orbitron';">{news_status}</b>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --- 4. CORE PARAMETERS WITH AUDIT NOTES ---
    st.markdown(
        "<p style='font-family:Orbitron; font-size:11px; color:#555; letter-spacing:2px; margin-bottom:15px;'>PARAMETER BREAKDOWN</p>",
        unsafe_allow_html=True)

    details = score_res.get('details', {})
    audit = score_res.get('audit', {})

    cols = st.columns(5)
    metrics = ["Trend", "Macro", "Momentum", "Sentiment", "MTF Bonus"]

    for i, m in enumerate(metrics):
        val = details.get(m, 0)
        # Ambil catatan dari engine.py, jika tidak ada pakai default
        note = audit.get(m, "Condition Monitored")

        # Penentuan warna per kotak
        m_color = "#00ffcc" if val > 0 else "#ff4b4b" if val < 0 else "#555"

        with cols[i]:
            st.markdown(f"""
                <div style="background:rgba(255,255,255,0.03); padding:15px; border-radius:10px; border-bottom:3px solid {m_color}; min-height:140px;">
                    <p style="color:#555; font-size:9px; margin:0; font-family:'Orbitron'; letter-spacing:1px;">{m.upper()}</p>
                    <h2 style="color:{m_color}; margin:10px 0; font-family:'JetBrains Mono';">{val:+}</h2>
                    <p style="color:#777; font-size:10px; font-family:'Public Sans'; line-height:1.3; margin-top:10px;">
                        <i style="color:#999;">{note}</i>
                    </p>
                </div>
            """, unsafe_allow_html=True)

    # --- 5. LEGEND & INFORMATION ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("Quantum Score +/- 10 is the maximum confluence for execution. Threshold for signal starts at +/- 6.")