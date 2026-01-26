import streamlit as st


def render_smc_tab(smc_data):
    # 1. Header dengan render HTML aman
    st.markdown("<h3 style='color:#888; font-family:sans-serif; letter-spacing:2px;'>INSTITUTIONAL FOOTPRINTS</h3>",
                unsafe_allow_html=True)

    if not smc_data:
        st.info("Market is efficient. No FVG.")
        return

    # 2. Loop data (ambil 5 terbaru)
    for zone in reversed(smc_data[-5:]):
        is_bull = "BULLISH" in zone['type']
        color = "#00ffcc" if is_bull else "#ff4b4b"
        bg = "rgba(0, 255, 204, 0.05)" if is_bull else "rgba(255, 75, 75, 0.05)"
        status_color = "#888" if zone['status'] == "Unfilled" else "#444"

        # Gabungkan semua ke dalam satu string besar (F-String)
        html_box = f"""
        <div style="background:{bg}; padding:20px; border-radius:10px; border-left:5px solid {color}; margin-bottom:15px; border-right:1px solid {color}33; border-top:1px solid {color}11;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="color:{color}; font-family:sans-serif; font-size:14px;">{zone['type']}</b>
                <span style="color:{status_color}; font-size:10px; font-weight:bold;">{zone['status']}</span>
            </div>
            <div style="margin:15px 0;">
                <span style="color:#666; font-size:10px; font-family:sans-serif;">ENTRY ZONE</span><br>
                <code style="font-size:16px; color:#eee; font-family:monospace;">{zone['bottom']:.5f} - {zone['top']:.5f}</code>
            </div>
            <div style="background:rgba(255,255,255,0.03); padding:12px; border-radius:8px; text-align:center; border:1px dashed {color}44;">
                <span style="color:{color}; font-size:10px; font-family:sans-serif; opacity:0.8;">GOLDEN ENTRY (50%)</span><br>
                <b style="font-size:24px; color:{color}; font-family:monospace;">{zone['mid']:.5f}</b>
            </div>
        </div>
        """

        # 3. Render ke layar
        st.markdown(html_box, unsafe_allow_html=True)