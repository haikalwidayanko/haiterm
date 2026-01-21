import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. CORE IMPORTS (MODULAR) ---
from data_provider import (
    fetch_macro_data,
    fetch_forex_data,
    get_forex_list,
    check_news_shield,
    get_market_sentiment
)
from engine import hitung_indikator_lengkap, get_detailed_scores_v10, calculate_fibonacci_levels
from market_sessions import get_market_sessions
from ai_analyst import generate_strategic_verdict

# UI Components Modular
from quantum_ui import render_quantum_tab
from astronacci_ui import render_astronacci_tab
from ai_ui import render_ai_intelligence_tab


# --- 2. SECURITY GATE (STREAMLIT SECRETS) ---
def check_password():
    """Mengecek akses menggunakan kunci di .streamlit/secrets.toml dengan proteksi KeyError."""

    # 1. Inisialisasi status awal jika belum ada di memori
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # 2. Jika sudah pernah login sukses, langsung kembalikan True
    if st.session_state["password_correct"]:
        return True

    def password_entered():
        """Callback saat user menekan Enter di kotak password."""
        # Pastikan key 'password' ada di session_state sebelum dibaca
        if "password" in st.session_state:
            if st.session_state["password"] == st.secrets["terminal_password"]:
                st.session_state["password_correct"] = True
                # Hapus password dari memori setelah sukses (keamanan)
                del st.session_state["password"]
            else:
                st.session_state["password_correct"] = False

    # 3. Tampilan Login Page
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Public+Sans&display=swap');
            .login-container { text-align: center; margin-top: 15%; font-family: 'Public Sans', sans-serif; }
            .terminal-header { font-family: 'Orbitron', sans-serif; color: #00ffcc; letter-spacing: 5px; font-size: 24px; margin-bottom: 30px; }
        </style>
        <div class="login-container">
            <p class="terminal-header">⚛️ hAI terminal ACCESS</p>
        </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 1, 1])
    with col_m:
        # Widget ini yang menciptakan key "password" di session_state
        st.text_input("ENTER ACCESS KEY", type="password", on_change=password_entered, key="password")

        # Tampilkan pesan error jika salah
        if "password_correct" in st.session_state and st.session_state["password_correct"] == False:
            if "password" not in st.session_state:  # Cek jika sudah di-submit tapi salah
                st.error("⚠️ ACCESS DENIED: INVALID KEY")

    return False

    return st.session_state["password_correct"]


# --- 3. MAIN TERMINAL INTERFACE ---
if check_password():
    # Page Configuration
    st.set_page_config(page_title="hAI terminal", layout="wide", page_icon="⚛️")

    # Global CSS Refinement
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Public+Sans:wght@300;400;600&family=JetBrains+Mono:wght@400;500&display=swap');

            /* Typography */
            html, body, [class*="css"] { font-family: 'Public Sans', sans-serif; background-color: #050505; color: #d1d1d1; }
            .terminal-title { font-family: 'Orbitron', sans-serif; color: #00ffcc; font-size: 20px; font-weight: 700; letter-spacing: 4px; text-transform: uppercase; }

            /* Telemetry Styling */
            .telemetry-box { background: rgba(255, 255, 255, 0.02); border: 1px solid #1a1a1a; padding: 12px 18px; border-radius: 8px; }

            /* Tabs Styling */
            .stTabs [data-baseweb="tab-list"] { gap: 10px; }
            .stTabs [data-baseweb="tab"] { background-color: rgba(255,255,255,0.02); border-radius: 4px 4px 0 0; padding: 10px 20px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. SIDEBAR ---
    with st.sidebar:
        st.markdown('<p class="terminal-title">⚛️ hAI terminal</p>', unsafe_allow_html=True)
        st.caption("Strategic Intelligence Hub v3.5")
        st.divider()

        # Jakarta Time Monitor
        tz_jkt = pytz.timezone('Asia/Jakarta')
        st.markdown(f"""
            <div style="font-family:'JetBrains Mono'; color:#00ffcc; font-size:18px; text-align:center; padding:10px; border:1px solid #1a1a1a; border-radius:4px;">
                {datetime.now(tz_jkt).strftime('%H:%M:%S')} <span style="font-size:10px; color:#555;">WIB</span>
            </div>
        """, unsafe_allow_html=True)

        st.divider()
        ticker = st.selectbox("ACTIVE ASSET", get_forex_list(), index=0)
        tf = st.selectbox("TIMEFRAME", ["15m", "1h", "4h", "1d"], index=1)

        st.divider()
        # Toggle Auto Refresh
        refresh_on = st.toggle("Live Telemetry Sync", value=False)
        if refresh_on:
            st_autorefresh(interval=10000, key="global_refresh")

            # --- TELEGRAM TEST TRIGGER ---
        st.divider()
        if st.button("🚀 TEST NOTIF KE IPHONE"):
            from data_provider import send_telegram_alert

            test_msg = f"⚛️ *hAI Terminal: Connection Sync*\nStatus: Connected\nTime: {datetime.now(tz_jkt).strftime('%H:%M:%S')}\n\n*Ready for Trading, Bang!*"
            send_telegram_alert(test_msg)
            st.toast("Notifikasi dikirim!", icon="📲")

    # --- 5. DATA ENGINE PROCESSING ---
    try:
        macro = fetch_macro_data()
        df_raw = fetch_forex_data(ticker, "60d", tf)
        df_active = hitung_indikator_lengkap(df_raw)

        # Hitung variabel ini di sini (Global), jangan di dalam Tab!
        news_alerts = check_news_shield(ticker)
        fib_levels = calculate_fibonacci_levels(df_active)
        last_close = df_active['Close'].iloc[-1]

        # Header Logic
        prev_close = df_active['Close'].iloc[-2]
        price_delta = last_close - prev_close
        pct_delta = (price_delta / prev_close) * 100
        delta_color = "#00ffcc" if price_delta >= 0 else "#ff4b4b"

        # Quantum Logic
        si, sd, _ = get_market_sentiment(ticker)
        score_res = get_detailed_scores_v10(df_active, macro, si, 0)

        # Proses Analisa AI Strategis (Jadikan Global untuk Notifikasi)
        analysis = generate_strategic_verdict(ticker, score_res, fib_levels, last_close, news_alerts)

        # Market Session Logic
        sessions, _, m_note, m_color = get_market_sessions()

        # --- 6. BACKGROUND ENGINE (NOTIFIKASI & HEARTBEAT) ---
        tz_jkt = pytz.timezone('Asia/Jakarta')
        now_jkt = datetime.now(tz_jkt)

        # --- 6. GLOBAL TELEMETRY HEADER (STAY ON TOP) ---
        h1, h2, h3 = st.columns([2, 1, 1])

        with h1:
            st.markdown(f"""
                <div class="telemetry-box" style="border-left: 3px solid {delta_color};">
                    <p style="font-size:9px; color:#555; letter-spacing:1px; margin:0;">INSTRUMENT FEED</p>
                    <div style="display:flex; align-items:baseline; gap:12px;">
                        <span style="font-family:'Orbitron'; font-size:22px; color:#eee; letter-spacing:1px;">{ticker.replace('=X', '')}</span>
                        <span style="font-family:'JetBrains Mono'; font-size:24px; color:{delta_color};">$ {last_close:,.5f}</span>
                        <span style="font-family:'JetBrains Mono'; font-size:12px; color:{delta_color}; font-weight:500;">
                            {price_delta:+.5f} ({pct_delta:+.2f}%)
                        </span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with h2:
            st.markdown(f"""
                <div class="telemetry-box" style="border-left: 3px solid #FFD700;">
                    <p style="font-size:9px; color:#555; letter-spacing:1px; margin:0;">DXY INDEX</p>
                    <div style="font-family:'JetBrains Mono'; font-size:22px; color:#eee;">
                        {macro.get('dxy_val', 0.0):.3f} <span style="font-size:14px; color:#888;">{"▲" if macro.get('dxy_rel') else "▼"}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with h3:
            # Market Session dikecilkan agar tidak mengganggu
            st.markdown(f"""
                <div class="telemetry-box" style="border-left: 3px solid {m_color};">
                    <p style="font-size:9px; color:#555; letter-spacing:1px; margin:0;">MARKET SESSION</p>
                    <div style="font-family:'Orbitron'; font-size:12px; color:{m_color}; padding-top:4px; letter-spacing:2px; font-weight:500;">
                        {m_note}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- HEARTBEAT 22:00 WIB ---
        tz_jkt = pytz.timezone('Asia/Jakarta')
        now_jkt = datetime.now(tz_jkt)

        if now_jkt.hour == 22 and now_jkt.minute == 0:
            heartbeat_key = f"hb_{now_jkt.strftime('%Y%m%d')}"
            if heartbeat_key not in st.session_state:
                from data_provider import send_telegram_alert

                send_telegram_alert("📡 *SYSTEM CHECK*: Masih cari yang OK nih...")
                st.session_state[heartbeat_key] = True

        # --- DYNAMIC SIGNAL TRIGGER (+/- 6 + Astro) ---
        # Trigger otomatis jika skor minimal +/- 6 DAN harga di area Golden
        if abs(analysis['q_val']) >= 6 and analysis['is_near']:
            notif_key = f"signal_{ticker}_{df_active.index[-1]}"
            if notif_key not in st.session_state:
                from data_provider import send_telegram_alert

                pesan = f"⚛️ *{ticker.replace('=X', '')}* | `{last_close:,.5f}`\n" \
                        f"Verdict: *{analysis['verdict']}*\n" \
                        f"Action: {analysis['action']}"
                send_telegram_alert(pesan)
                st.session_state[notif_key] = True

        # --- 7. THE INTERFACE TABS ---
        tab_q, tab_a, tab_ai = st.tabs(["⚛️ QUANTUM DATA", "🔭 ASTRONACCI", "🧠 AI HUB"])

        with tab_q:
            # Menggunakan renderer dari quantum_ui.py
            render_quantum_tab(ticker, df_active, score_res, macro, sd, "glow", "SYNCED", [])

        with tab_a:
            # Menggunakan renderer dari astronacci_ui.py (High Conviction Logic)
            render_astronacci_tab(ticker, df_active)

        with tab_ai:
           render_ai_intelligence_tab(ticker, analysis)

    except Exception as e:
        st.error(f"🛑 TERMINAL CORE ERROR: {e}")