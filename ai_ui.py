import streamlit as st


def render_ai_intelligence_tab(ticker, analysis):
    color = analysis['color']
    conf = analysis['confidence']

    # 1. Main Header Card
    st.markdown(f"""
        <div style="background:rgba(255,255,255,0.02); padding:30px; border-radius:15px; border:1px solid {color}44; text-align:center; margin-bottom:20px;">
            <p style="font-family:Orbitron; font-size:12px; color:#666; letter-spacing:3px; margin-bottom:10px;">MARKET SENTINEL V10</p>
            <h1 style="color:{color}; font-family:Orbitron; font-size:38px; margin:0; font-weight:900; text-shadow: 0 0 15px {color}44;">
                {analysis['judgement']}
            </h1>
            <p style="color:#aaa; font-size:14px; margin-top:10px; font-style:italic;">"{analysis['action']}"</p>
        </div>
    """, unsafe_allow_html=True)

    # 2. Confidence Meter
    st.write(f"**Confidence Level: {conf}%**")
    st.progress(conf / 100)

    st.markdown("---")

    # 3. Confluence Matrix (Visual Checklist)
    col1, col2, col3 = st.columns(3)

    with col1:
        status = "✅" if abs(analysis['q_val']) >= 6 else "❌"
        st.metric("Quantum Bias", f"{analysis['q_val']}", delta=None)
        st.caption(f"{status} Momentum")

    with col2:
        status = "✅" if analysis['is_floor'] else "⏳"
        st.metric("Astro Area", "Golden 61.8%" if analysis['is_floor'] else "Off-Level")
        st.caption(f"{status} Price Floor")

    with col3:
        status = "✅" if analysis['fvg_found'] else "🔍"
        st.metric("SMC Scan", "Gap Found" if analysis['fvg_found'] else "Efficient")
        st.caption(f"{status} Smart Money")

    # 4. Final Verdict Box
    if conf >= 80:
        st.success(f"🔥 **HIGH CONVICTION SETUP** identified for {ticker}. Risk/Reward ratio is optimal.")
    elif conf >= 50:
        st.warning(f"⚖️ **NEUTRAL/MODERATE** - Trade with smaller position size or wait for further confirmation.")
    else:
        st.error(f"🛑 **NO TRADE ZONE** - Signals are conflicting or market is inefficient.")