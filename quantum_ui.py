import streamlit as st


def render_quantum_tab(ticker, df_active, score_res, macro, sd, glow_class, status, news):
    """
    Layout Tab Quantum: Fokus pada Bias Teknikal & Deteksi Perubahan Warna Skor.
    Update: Fix Positional Arguments (8 Args Synchronized).
    """
    # --- 1. LOGIC: DYNAMIC COLORING (Threshold +/- 5) ---
    total_score = score_res.get('total', 0)

    # Penentuan warna berdasarkan instruksi: +-5 sebagai pemicu visual
    if total_score >= 5:
        accent_color = "#00ffcc"  # HIJAU NEON
        score_desc = "BULLISH CONFIRMATION"
        glow_shadow = "0 0 30px #00ffcc44"
    elif total_score <= -5:
        accent_color = "#ff4b4b"  # MERAH NEON
        score_desc = "BEARISH CONFIRMATION"
        glow_shadow = "0 0 30px #ff4b4b44"
    else:
        accent_color = "#ffffff"  # PUTIH
        score_desc = "NEUTRAL / MONITORING"
        glow_shadow = "none"

    # --- 2. HEADER: QUANTUM BIAS DISPLAY ---
    # Menggunakan 'glow_class' jika diperlukan untuk styling tambahan
    st.markdown(f"""
        <div style="text-align:center; padding:35px; border:1px solid {accent_color}44; border-radius:15px; 
                    background:rgba(255,255,255,0.02); box-shadow: {glow_shadow}; transition: all 0.5s ease;">
            <p style="font-family:'Orbitron'; font-size:10px; color:#666; letter-spacing:4px; margin-bottom:5px;">QUANTUM BIAS INDEX</p>
            <h1 style="font-family:'Orbitron'; font-size:80px; margin:0; line-height:1; color:{accent_color}; 
                       text-shadow: 0 0 20px {accent_color}66;">{total_score:+}</h1>
            <p style="font-family:'Orbitron'; font-size:11px; color:{accent_color}; margin-top:15px; letter-spacing:2px; font-weight:700;">
                {score_desc}
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 3. MARKET PULSE & TELEMETRY ---
    col1, col2, col3 = st.columns(3)

    last = df_active.iloc[-1]
    rsi_val = last.get('RSI', 50)
    adx_val = last.get('ADX', 0)

    with col1:
        st.markdown(f"""<div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:10px; border-left:3px solid #00ffcc;">
            <p style="color:#555; font-size:10px; margin:0; font-family:'Orbitron';">MOMENTUM (RSI)</p>
            <b style="font-size:20px; font-family:'JetBrains Mono';">{rsi_val:.2f}</b>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""<div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:10px; border-left:3px solid #FFD700;">
            <p style="color:#555; font-size:10px; margin:0; font-family:'Orbitron';">TREND POWER (ADX)</p>
            <b style="font-size:20px; font-family:'JetBrains Mono';">{adx_val:.2f}</b>
        </div>""", unsafe_allow_html=True)

    with col3:
        # Indikator News Shield
        is_news_active = len(news) > 0 if isinstance(news, list) else False
        news_status = "⚠️ CAUTION" if is_news_active else "✅ CLEAR"
        news_color = "#ff4b4b" if is_news_active else "#00ffcc"
        st.markdown(
            f"""<div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:10px; border-left:3px solid {news_color};">
            <p style="color:#555; font-size:10px; margin:0; font-family:'Orbitron';">NEWS SHIELD</p>
            <b style="font-size:18px; color:{news_color}; font-family:'Orbitron';">{news_status}</b>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # --- 4. AUDIT DETAILS ---
    with st.expander("🔍 VIEW QUANTUM CALCULATION DETAILS"):
        details = score_res.get('details', {})
        for label, val in details.items():
            c = "#00ffcc" if val > 0 else ("#ff4b4b" if val < 0 else "#666")
            st.markdown(f"""
                <div style="display:flex; justify-content:space-between; border-bottom:1px solid #1a1a1a; padding:8px 0;">
                    <span style="color:#888; font-size:13px;">{label.upper()}</span>
                    <b style="color:{c}; font-family:'JetBrains Mono';">{val:+}</b>
                </div>
            """, unsafe_allow_html=True)