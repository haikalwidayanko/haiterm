import streamlit as st
from engine import calculate_fibonacci_levels
from astrology_engine import get_astrology_status


def render_astronacci_tab(ticker, df_active):
    """
    Layout Tab Astronacci: Fokus pada Eksekusi Presisi dengan Filter 'WAIT' Area.
    """
    # --- 1. DATA PREPARATION ---
    astro = get_astrology_status()
    fib = calculate_fibonacci_levels(df_active)
    p_now = float(df_active['Close'].iloc[-1])

    # Filter Level: Buang 0% dan 100% sesuai request
    clean_fib = {lvl: val for lvl, val in fib.items() if "0%" not in lvl and "100%" not in lvl}

    # Level Kunci
    lv_382 = fib.get('38.2%', 0)
    lv_500 = fib.get('50.0%', 0)
    lv_618 = fib.get('61.8% (Golden)', 0)
    lv_786 = fib.get('78.6%', 0)

    # --- 2. CELESTIAL MONITOR (STAY ON TOP) ---
    st.markdown(
        "<p style='font-family:Orbitron; font-size:11px; color:#555; letter-spacing:2px; margin-bottom:10px;'>CELESTIAL TIME CONFLUENCE</p>",
        unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"""<div style="background:rgba(0,255,204,0.02); padding:15px; border-radius:10px; border:1px solid #00ffcc44; text-align:center;">
            <p style="color:#666; font-size:9px; margin:0;">LUNAR PHASE</p>
            <b style="color:#00ffcc; font-family:Orbitron; font-size:18px;">{astro['next_event']}</b>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:10px; border:1px solid #333; text-align:center;">
            <p style="color:#666; font-size:9px; margin:0;">MERCURY STATUS</p>
            <b style="color:#eee; font-family:Orbitron; font-size:18px;">{astro['mercury_status']}</b>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div style="background:rgba(255,215,0,0.02); padding:15px; border-radius:10px; border:1px solid #FFD70044; text-align:center;">
            <p style="color:#666; font-size:9px; margin:0;">REVERSAL WINDOW</p>
            <b style="color:#FFD700; font-family:Orbitron; font-size:18px;">{astro['days_left']} Days</b>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # --- 3. DYNAMIC SIGNAL LOGIC (WITH WAIT ZONE) ---
    # Menghitung seberapa dekat harga dengan Golden Ratio (Threshold 0.15% untuk Forex)
    distance_to_golden = abs(p_now - lv_618) / lv_618
    is_near_golden = distance_to_golden < 0.0015

    # Inisialisasi Default (WAIT)
    signal_type = "WAIT"
    signal_color = "#888888"
    instruction = "Harga berada di zona netral. Tunggu konfirmasi di area Golden Ratio (61.8%)."
    entry_lv, tp_lv, sl_lv = lv_618, 0, 0

    if is_near_golden:
        # Jika harga dekat Golden Ratio, baru cek Bias
        if p_now > lv_618:  # Potensi Rebound
            signal_type, signal_color = "BUY", "#00ffcc"
            tp_lv, sl_lv = lv_382, lv_786
            instruction = "ENTRY READY: Harga menyentuh Golden Ratio. Look for Rebound."
        else:  # Potensi Rejection
            signal_type, signal_color = "SELL", "#ff4b4b"
            tp_lv, sl_lv = lv_786, lv_382
            instruction = "ENTRY READY: Harga menyentuh Golden Ratio. Look for Rejection."
    elif lv_500 < p_now < lv_382 or lv_786 < p_now < lv_618:
        # Jika harga di antara level tapi tidak di Golden Ratio
        signal_type, signal_color = "MONITOR", "#FFD700"
        instruction = "Harga sedang bergerak antar level. Belum ada setup probabilitas tinggi."

    # --- 4. SIGNAL COMMAND CENTER ---
    st.markdown(f"""
        <div style="background:{signal_color}11; border:2px solid {signal_color}; padding:25px; border-radius:12px; text-align:center; margin-bottom:20px;">
            <p style="color:{signal_color}; font-family:Orbitron; font-size:11px; letter-spacing:3px; margin:0;">TACTICAL STATUS</p>
            <h1 style="color:{signal_color}; font-family:Orbitron; margin:5px 0; font-size:42px;">{signal_type} SETUP</h1>
            <p style="color:#eee; font-size:13px;">{instruction}</p>
        </div>
    """, unsafe_allow_html=True)

    if signal_type != "WAIT":
        l1, l2, l3 = st.columns(3)
        with l1:
            st.markdown(f"""<div style="background:rgba(255,215,0,0.05); padding:15px; border-radius:10px; border:1px solid #FFD700; text-align:center;">
                <p style="color:#FFD700; font-family:Orbitron; font-size:10px; margin:0;">ENTRY</p>
                <h2 style="font-family:'JetBrains Mono'; color:#eee; margin:10px 0;">{entry_lv:,.5f}</h2>
            </div>""", unsafe_allow_html=True)
        with l2:
            st.markdown(f"""<div style="background:rgba(0,255,204,0.05); padding:15px; border-radius:10px; border:1px solid #00ffcc; text-align:center;">
                <p style="color:#00ffcc; font-family:Orbitron; font-size:10px; margin:0;">TARGET (TP)</p>
                <h2 style="font-family:'JetBrains Mono'; color:#eee; margin:10px 0;">{tp_lv:,.5f}</h2>
            </div>""", unsafe_allow_html=True)
        with l3:
            st.markdown(f"""<div style="background:rgba(255,75,75,0.05); padding:15px; border-radius:10px; border:1px solid #ff4b4b; text-align:center;">
                <p style="color:#ff4b4b; font-family:Orbitron; font-size:10px; margin:0;">STOP LOSS</p>
                <h2 style="font-family:'JetBrains Mono'; color:#eee; margin:10px 0;">{sl_lv:,.5f}</h2>
            </div>""", unsafe_allow_html=True)

    st.divider()

    # --- 5. CLEAN FIBONACCI MATRIX (NO 0% & 100%) ---
    st.markdown(
        "<p style='font-family:Orbitron; font-size:11px; color:#555; letter-spacing:2px; margin-bottom:15px;'>CORE FIBONACCI LEVELS</p>",
        unsafe_allow_html=True)
    grid_cols = st.columns(len(clean_fib))
    for i, (lvl, val) in enumerate(clean_fib.items()):
        is_golden = "61.8%" in lvl
        border_col = "#FFD700" if is_golden else "#222"
        bg_col = "rgba(255,215,0,0.1)" if is_golden else "rgba(255,255,255,0.01)"

        grid_cols[i].markdown(f"""
            <div style="background:{bg_col}; border:1px solid {border_col}; padding:10px; border-radius:6px; text-align:center;">
                <p style="font-size:9px; color:{'#FFD700' if is_golden else '#666'}; margin:0; font-family:Orbitron;">{lvl.replace(' (Golden)', '')}</p>
                <b style="font-family:'JetBrains Mono'; font-size:13px; color:{'#eee' if not is_golden else '#FFD700'};">{val:.5f}</b>
            </div>
        """, unsafe_allow_html=True)