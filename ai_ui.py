import streamlit as st


def render_ai_intelligence_tab(ticker, analysis):
    """
    AI Intelligence UI: Menampilkan Trading Plan & Analisa Konfluensi
    Quantum, Astro, dan Smart Money Concepts (SMC).
    """
    # Mengambil data dari dictionary analysis dengan fallback safe
    color = analysis.get('color', '#888')
    plan = analysis.get('plan', {"entry": 0, "sl": 0, "tp1": 0, "tp2": 0})
    conf = int(analysis.get('confidence', 0))
    q_val = analysis.get('q_val', 0)

    # 1. JUDGMENT HEADER CARD
    # Menampilkan sinyal utama (Buy/Sell/Neutral)
    st.markdown(f"""
        <div style="background:rgba(255,255,255,0.02); padding:25px; border-radius:15px; border:1px solid {color}55; text-align:center; margin-bottom:20px;">
            <p style="font-family:sans-serif; font-size:10px; color:#888; letter-spacing:3px; text-transform:uppercase; margin-bottom:5px;">Neural AI Judgment</p>
            <h1 style="color:{color}; font-family:sans-serif; font-size:32px; margin:0; font-weight:bold; letter-spacing:-1px;">
                {analysis['judgement']}
            </h1>
            <p style="color:#eee; font-size:14px; opacity:0.8; margin-top:10px; font-style:italic;">"{analysis['action']}"</p>
        </div>
    """, unsafe_allow_html=True)

    # 2. CONFIDENCE METER
    # Visualisasi seberapa yakin AI dengan sinyal ini
    st.write(f"**AI Confidence Level: {conf}%**")
    st.progress(conf / 100)

    # 3. TRADE EXECUTION PLAN PANEL
    # Panel krusial untuk Entry, SL, dan Take Profit
    if plan['entry'] > 0:
        st.markdown(
            "<br><p style='font-family:sans-serif; font-size:12px; color:#555; letter-spacing:2px; font-weight:bold;'>TRADE EXECUTION PLAN</p>",
            unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(f"""
                <div style='text-align:center; padding:15px; background:rgba(0,255,204,0.05); border-radius:10px; border:1px solid #00ffcc22;'>
                    <span style='font-size:10px; color:#00ffcc; font-weight:bold;'>ENTRY</span><br>
                    <b style='font-size:16px; color:#eee; font-family:monospace;'>{plan['entry']:.5f}</b>
                </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
                <div style='text-align:center; padding:15px; background:rgba(255,75,75,0.05); border-radius:10px; border:1px solid #ff4b4b22;'>
                    <span style='font-size:10px; color:#ff4b4b; font-weight:bold;'>STOP LOSS</span><br>
                    <b style='font-size:16px; color:#eee; font-family:monospace;'>{plan['sl']:.5f}</b>
                </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
                <div style='text-align:center; padding:15px; background:rgba(255,255,255,0.03); border-radius:10px; border:1px solid #ffffff11;'>
                    <span style='font-size:10px; color:#aaa; font-weight:bold;'>TP 1</span><br>
                    <b style='font-size:16px; color:#eee; font-family:monospace;'>{plan['tp1']:.5f}</b>
                </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
                <div style='text-align:center; padding:15px; background:rgba(255,255,255,0.03); border-radius:10px; border:1px solid #ffffff11;'>
                    <span style='font-size:10px; color:#aaa; font-weight:bold;'>TP 2</span><br>
                    <b style='font-size:16px; color:#eee; font-family:monospace;'>{plan['tp2']:.5f}</b>
                </div>
            """, unsafe_allow_html=True)

    # 4. CONFLUENCE MATRIX (Analisa Pendukung)
    st.markdown(
        "<br><p style='font-family:sans-serif; font-size:11px; color:#444; margin-bottom:15px;'>CONFLUENCE MATRIX</p>",
        unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        # Quantum Bias Power
        q_color = "#00ffcc" if abs(q_val) >= 6 else "#666"
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02); padding:12px; border-radius:8px; border-top:2px solid {q_color}; text-align:center;">
                <p style="font-size:9px; color:#555; margin:0;">QUANTUM POWER</p>
                <h4 style="margin:5px 0; color:{q_color}; font-family:monospace;">{q_val} pts</h4>
            </div>
        """, unsafe_allow_html=True)

    with col_b:
        # Astro Zone (Golden Ratio 61.8%)
        astro_color = "#00ffcc" if analysis.get('is_floor') else "#666"
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02); padding:12px; border-radius:8px; border-top:2px solid {astro_color}; text-align:center;">
                <p style="font-size:9px; color:#555; margin:0;">ASTRO ZONE</p>
                <h4 style="margin:5px 0; color:{astro_color};">{'FLOOR FOUND' if analysis.get('is_floor') else 'MID-AIR'}</h4>
            </div>
        """, unsafe_allow_html=True)

    with col_c:
        # SMC Logic (Smart Money Concept)
        smc_text = analysis.get('smc_logic', 'SCANNING')
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02); padding:12px; border-radius:8px; border-top:2px solid #00ffcc; text-align:center;">
                <p style="font-size:9px; color:#555; margin:0;">SMC LOGIC</p>
                <h4 style="margin:5px 0; color:#00ffcc; font-size:11px;">{smc_text}</h4>
            </div>
        """, unsafe_allow_html=True)

    # 5. FINAL VERDICT
    st.markdown("<br>", unsafe_allow_html=True)
    if conf >= 70:
        st.success(f"🔥 **Setup Valid.** High probability execution window for {ticker}.")
    elif conf >= 40:
        st.warning(f"⚖️ **Monitoring.** Bias is present but confluence is incomplete.")
    else:
        st.info(f"🛑 **No Trade Zone.** Market noise detected. Preservation mode active.")