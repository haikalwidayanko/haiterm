import streamlit as st


def render_ai_intelligence_tab(ticker, analysis_data):
    """
    Layout AI Hub yang sinkron dengan threshold Quantum +/- 10
    dan konlfuensi Astronacci.
    """
    # 1. DATA EXTRACTION
    v = analysis_data
    v_color = v.get('color', '#888888')
    q_score = v.get('q_val', 0)
    is_near = v.get('is_near', False)

    # --- 2. THE STRATEGIC VERDICT (DYNAMIC GLOW CARD) ---
    st.markdown(f"""
        <div style="background:{v_color}11; border:2px solid {v_color}; padding:35px; border-radius:15px; text-align:center; box-shadow: 0 0 30px {v_color}15;">
            <p style="font-family:'Orbitron'; font-size:10px; color:{v_color}; letter-spacing:5px; margin:0; font-weight:500;">STRATEGIC HUB VERDICT</p>
            <h1 style="font-family:'Orbitron'; font-size:42px; color:{v_color}; margin:15px 0; font-weight:900; letter-spacing:1px; line-height:1.2;">
                {v.get('verdict', 'NEUTRAL')}
            </h1>
            <div style="background:{v_color}; color:#000; padding:8px 25px; border-radius:4px; display:inline-block; font-weight:700; font-family:'Orbitron'; font-size:13px; letter-spacing:2px; text-transform:uppercase;">
                COMMAND: {v.get('action', 'WAIT')}
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 3. ANALYSIS SUMMARY COLUMNS ---
    col_left, col_right = st.columns(2)

    with col_left:
        # Technical & Astro Summary
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02); padding:22px; border-radius:10px; border-left:4px solid #00ffcc; min-height:160px;">
                <h4 style="margin:0; font-family:'Orbitron'; font-size:12px; color:#00ffcc; letter-spacing:2px;">INTELLIGENCE SUMMARY</h4>
                <p style="font-size:14px; line-height:1.7; color:#d1d1d1; margin-top:14px; font-family:'Public Sans';">
                    {v.get('summary', 'Analyzing market structure...')}
                </p>
            </div>
        """, unsafe_allow_html=True)

    with col_right:
        # Fundamental & Risk Summary
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02); padding:22px; border-radius:10px; border-left:4px solid #FFD700; min-height:160px;">
                <h4 style="margin:0; font-family:'Orbitron'; font-size:12px; color:#FFD700; letter-spacing:2px;">NEWS SHIELD MONITOR</h4>
                <p style="font-size:14px; line-height:1.7; color:#d1d1d1; margin-top:14px; font-family:'Public Sans';">
                    {v.get('news_brief', 'Scanning global economic news...')}
                </p>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --- 4. CONFLUENCE CHECKLIST (THE GATEKEEPER) ---
    st.markdown(
        "<p style='font-family:Orbitron; font-size:11px; color:#555; letter-spacing:3px; margin-bottom:20px;'>CONFLUENCE VERIFICATION MATRIX</p>",
        unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    # CHECK 1: Quantum Logic (Sesuai treshold +/- 10)
    if abs(q_score) >= 8:
        q_icon, q_label, q_sub = "✅", "CONFIRMED", "Score meets max threshold"
    elif abs(q_score) >= 5:
        q_icon, q_label, q_sub = "⚠️", "MODERATE", "Partial bias detected"
    else:
        q_icon, q_label, q_sub = "❌", "WEAK", "No institutional bias"

    c1.markdown(f"""
        <div style="background:rgba(255,255,255,0.01); padding:15px; border-radius:8px; border:1px solid #1a1a1a;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:20px;">{q_icon}</span>
                <b style="font-size:14px; color:#eee;">Quantum Bias</b>
            </div>
            <p style="color:#555; font-family:'JetBrains Mono'; font-size:11px; margin:5px 0 0 30px;">
                {q_score:+} (Req: +/-10)
            </p>
        </div>
    """, unsafe_allow_html=True)

    # CHECK 2: Astro Logic (Golden Ratio Area)
    a_icon = "✅" if is_near else "⏳"
    a_label = "IN ZONA" if is_near else "OUT OF ZONA"
    c2.markdown(f"""
        <div style="background:rgba(255,255,255,0.01); padding:15px; border-radius:8px; border:1px solid #1a1a1a;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:20px;">{a_icon}</span>
                <b style="font-size:14px; color:#eee;">Astro Entry</b>
            </div>
            <p style="color:#555; font-family:'Public Sans'; font-size:11px; margin:5px 0 0 30px;">
                Golden Ratio 61.8% Area
            </p>
        </div>
    """, unsafe_allow_html=True)

    # CHECK 3: Risk Logic (News Shield)
    n_icon = "✅" if "No major" in v.get('news_brief', '') else "⚠️"
    c3.markdown(f"""
        <div style="background:rgba(255,255,255,0.01); padding:15px; border-radius:8px; border:1px solid #1a1a1a;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:20px;">{n_icon}</span>
                <b style="font-size:14px; color:#eee;">Risk Filter</b>
            </div>
            <p style="color:#555; font-family:'Public Sans'; font-size:11px; margin:5px 0 0 30px;">
                News Shield Active
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # FOOTER METADATA
    st.markdown(f"""
        <div style="text-align:right; border-top:1px solid #1a1a1a; padding-top:10px;">
            <p style="font-family:'JetBrains Mono'; font-size:10px; color:#333; margin:0; letter-spacing:1px;">
                SYSTEM_STABLE // SYNC_TICKER: {ticker} // THRESHOLD_V10_ACTIVE
            </p>
        </div>
    """, unsafe_allow_html=True)