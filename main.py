import streamlit as st
import pytz
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from data_provider import (
    fetch_macro_data, fetch_forex_data,
    get_forex_list, get_ticker_display_name,
    check_news_shield, get_market_sentiment, fetch_ticker_news,
    send_telegram_alert, get_market_sessions, FOREX_PAIRS
)
from engine import (
    hitung_indikator_lengkap, get_detailed_scores_v12,
    calculate_fibonacci_levels, deteksi_smc_v2, run_backtest
)
from ai_hub import generate_ai_judgment
from quantum_ui import render_quantum_tab
from news_ui import render_news_tab
from ai_ui import render_ai_verdict_tab
from forex_ui import render_forex_scanner
from auth_ui import render_login_page, render_profile_page, render_admin_dashboard
from auth import has_pair_access, get_session_user, destroy_session, get_user_role, get_user_config
from journal_ui import render_journal_page
from journal import log_signal
from bg_scanner import run_background_scan, get_last_scan_results, get_all_scan_results
from calendar_ui import render_calendar_widget, render_calendar_full


# ============================================================
# PAGE CONFIG (must be first)
# ============================================================
st.set_page_config(
    page_title="Widayanko-Terminal v2.0",
    page_icon="⚛️",
    layout="wide"
)

# ============================================================
# GLOBAL CSS
# ============================================================
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Public+Sans:wght@300;400;600&family=JetBrains+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {
            font-family: 'Public Sans', sans-serif;
            background-color: #050505;
            color: #d1d1d1;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #1a1a1a; }
        .stTabs [data-baseweb="tab"] {
            background: rgba(255,255,255,0.02);
            border-radius: 6px 6px 0 0;
            padding: 10px 22px;
            font-family: 'Orbitron', sans-serif;
            font-size: 11px;
            letter-spacing: 1px;
            color: #555;
            border: none;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(0,255,204,0.08) !important;
            color: #00ffcc !important;
            border-bottom: 2px solid #00ffcc !important;
        }
        .stSelectbox > div > div { background: #0a0a0a; border: 1px solid #222; }
        .stRadio > div { gap: 8px; }
        div[data-testid="stMetricValue"] { font-family: 'JetBrains Mono'; }
        .stProgress > div > div > div { background-color: #00ffcc; }
        hr { border-color: #1a1a1a; }

        /* ── MOBILE RESPONSIVE ──────────────────────────── */
        @media (max-width: 768px) {
            [data-testid="stSidebar"] { min-width: 220px !important; max-width: 260px !important; }
            h1 { font-size: 22px !important; letter-spacing: 3px !important; }
            h2 { font-size: 16px !important; }
            .stTabs [data-baseweb="tab"] { padding: 8px 12px !important; font-size: 9px !important; letter-spacing: 0.5px !important; }
            div[data-testid="column"] { min-width: 100% !important; }
            .plan-row { flex-direction: column !important; }
            .plan-label { min-width: unset !important; width: 100% !important; }
            .plan-price { font-size: 14px !important; }
            .plan-pips { min-width: unset !important; }
            .plan-rr { border-radius: 0 0 10px 10px !important; min-width: unset !important; width: 100% !important; }
        }
        @media (max-width: 480px) {
            h1 { font-size: 18px !important; letter-spacing: 2px !important; }
            .stTabs [data-baseweb="tab"] { padding: 6px 8px !important; font-size: 8px !important; }
        }
    </style>
""", unsafe_allow_html=True)


# Removed password gate


# ============================================================
# STATE INITIALIZATION
# ============================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""

# Attempt to restore session from query params
if not st.session_state.logged_in and "session_token" in st.query_params:
    token = st.query_params["session_token"]
    user = get_session_user(token)
    if user:
        st.session_state.logged_in = True
        st.session_state.username = user
        st.session_state.role = get_user_role(user)
    else:
        # Invalid token, clear it
        del st.query_params["session_token"]

if not st.session_state.logged_in:
    render_login_page()
    st.stop()

if "app_view" not in st.session_state:
    st.session_state.app_view = "landing"
if "active_ticker" not in st.session_state:
    st.session_state.active_ticker = None
if "active_category" not in st.session_state:
    st.session_state.active_category = "Forex"

# Handle clickable flashcard routing via query params
if "ticker" in st.query_params:
    t = st.query_params["ticker"]
    st.session_state.active_ticker = t
    st.session_state.app_view = "detail"
    
    # Preserve active category based on instrument group
    from data_provider import FOREX_PAIRS
    g = FOREX_PAIRS.get(t, {}).get("group", "")
    if g in ("Metals", "Energy", "Agriculture", "Commodity"):
        st.session_state.active_category = "Commodities"
    elif g == "Crypto":
        st.session_state.active_category = "Crypto"
    else:
        st.session_state.active_category = "Forex"
        
    del st.query_params["ticker"]

if "action" in st.query_params:
    if st.query_params["action"] == "home":
        st.session_state.app_view = "landing"
        st.session_state.active_ticker = None
    del st.query_params["action"]

tz_jkt = pytz.timezone('Asia/Jakarta')

with st.sidebar:
    token_str = f"?session_token={st.query_params['session_token']}&action=home" if "session_token" in st.query_params else "?action=home"
    st.markdown(f'<a href="{token_str}" target="_self" style="text-decoration:none;"><p style="font-family:Orbitron;color:#00ffcc;font-size:22px;letter-spacing:4px;font-weight:900;transition:0.2s;cursor:pointer;">⚛️ W-TERMINAL</p></a>', unsafe_allow_html=True)
    st.caption("v2.0 — by Widayanko Capital")
    st.divider()

    # Live ticking clock via JavaScript
    st.components.v1.html("""
        <div id="wt-clock" style="font-family:'Courier New',monospace;color:#00ffcc;font-size:22px;
                               text-align:center;padding:10px;border:1px solid #1a1a1a;
                               border-radius:6px;margin-bottom:4px;background:#050505;"></div>
        <script>
            (function() {
                function updateClock() {
                    const now = new Date();
                    const opts = { timeZone: 'Asia/Jakarta', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12: false };
                    const time = now.toLocaleTimeString('id-ID', opts);
                    const dateOpts = { timeZone: 'Asia/Jakarta', weekday:'short', day:'2-digit', month:'short' };
                    const date = now.toLocaleDateString('id-ID', dateOpts);
                    const el = document.getElementById('wt-clock');
                    if (el) el.innerHTML =
                        '<span style="font-size:24px;letter-spacing:3px;">' + time + '</span>' +
                        '<br><span style="font-size:9px;color:#555;letter-spacing:2px;"> WIB &nbsp;|&nbsp; ' + date.toUpperCase() + '</span>';
                }
                updateClock();
                setInterval(updateClock, 1000);
            })();
        </script>
    """, height=85)

    st.divider()

    # User Permissions
    user_config = get_user_config(st.session_state.username)
    market_access = user_config.get("market_access", "ALL")
    can_journal = user_config.get("can_access_journal", True)

    # Market Buttons
    if market_access in ["ALL", "FOREX_CRYPTO"]:
        if st.button("⚛️ Market Forex", use_container_width=True):
            st.session_state.active_category = "Forex"
            st.session_state.app_view = "scanner"
            st.session_state.active_ticker = None
            st.rerun()
            
    if market_access in ["ALL", "COMMODITIES"]:
        if st.button("🛢️ Market Komoditas", use_container_width=True):
            st.session_state.active_category = "Commodities"
            st.session_state.app_view = "scanner"
            st.session_state.active_ticker = None
            st.rerun()
            
    if market_access in ["ALL", "FOREX_CRYPTO"]:
        if st.button("🪙 Market Crypto", use_container_width=True):
            st.session_state.active_category = "Crypto"
            st.session_state.app_view = "scanner"
            st.session_state.active_ticker = None
            st.rerun()

    st.divider()

    # Navigation for Detail View
    is_detail = st.session_state.app_view == "detail"
    if is_detail or st.session_state.app_view in ["admin", "profile", "journal", "calendar"]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔙 BACK TO SCANNER", use_container_width=True):
            st.session_state.app_view = "scanner"
            st.session_state.active_ticker = None
            st.rerun()
    else:
        if st.session_state.app_view == "scanner":
             if st.button("🏠 HOME MENU", use_container_width=True):
                 st.session_state.app_view = "landing"
                 st.session_state.active_ticker = None
                 st.rerun()

    st.divider()

    # User Profile & Admin
    st.markdown(f"<p style='font-size:12px;color:#aaa;'>👤 {st.session_state.username} ({st.session_state.role})</p>", unsafe_allow_html=True)
    if st.button("⚙️ PROFILE", use_container_width=True):
        st.session_state.app_view = "profile"
        st.session_state.active_ticker = None
        st.rerun()

    if can_journal:
        if st.button("📓 TRADE JOURNAL", use_container_width=True):
            st.session_state.app_view = "journal"
            st.session_state.active_ticker = None
            st.rerun()

    if st.button("📅 CALENDAR", use_container_width=True):
        st.session_state.app_view = "calendar"
        st.session_state.active_ticker = None
        st.rerun()

    if st.session_state.role == "admin":
        if st.button("🛡️ ADMIN DASHBOARD", use_container_width=True):
            st.session_state.app_view = "admin"
            st.session_state.active_ticker = None
            st.rerun()

    st.divider()
    
    try:
        with open("README.html", "r", encoding="utf-8") as f:
            readme_data = f.read()
        st.download_button(
            label="📘 DOWNLOAD BUKU PANDUAN",
            data=readme_data,
            file_name="Buku_Panduan_Widayanko_V2.html",
            mime="text/html",
            use_container_width=True
        )
    except Exception:
        pass

    if st.button("🚪 LOGOUT", use_container_width=True):
        if "session_token" in st.query_params:
            destroy_session(st.query_params["session_token"])
            del st.query_params["session_token"]
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.rerun()

    st.divider()

    refresh_on = st.toggle("⚡ Live Sync (5m)", value=False)
    if refresh_on:
        st_autorefresh(interval=300000, key="clock_refresh")

    # Background scanner runs automatically every hour
    st_autorefresh(interval=3600000, key="bg_scan_refresh")
    if "bg_last_run" not in st.session_state:
        st.session_state.bg_last_run = True
        run_background_scan(st.session_state.username)

    st.divider()

    # Economic Calendar widget in sidebar
    render_calendar_widget()

    st.divider()
    if st.session_state.role == "admin":
        if st.button("📲 TEST TELEGRAM"):
            send_telegram_alert(f"⚛️ *Widayanko-Terminal v2.0*\nStatus: Connected\nTime: {datetime.now(tz_jkt).strftime('%H:%M:%S')} WIB")
            st.toast("Notifikasi dikirim!", icon="📲")


# ============================================================
# VIEW ROUTING
# ============================================================
if st.session_state.app_view == "profile":
    render_profile_page()
    st.stop()

if st.session_state.app_view == "admin":
    render_admin_dashboard()
    st.stop()

if st.session_state.app_view == "journal":
    render_journal_page()
    st.stop()

if st.session_state.app_view == "calendar":
    render_calendar_full()
    st.stop()

# ============================================================
# HEATMAP HELPER
# ============================================================
def _render_heatmap():
    """Quick heatmap of all pairs using cached scan data or a fast score estimate."""
    from data_provider import get_forex_list, FOREX_PAIRS
    all_pairs = get_forex_list()
    username = st.session_state.get("username", "")
    user_pairs = [t for t in all_pairs if has_pair_access(username, t)]

    # Use bg scan results if available, else show placeholder
    bg_sigs, _ = get_all_scan_results()
    sig_map = {s["ticker"]: s for s in bg_sigs} if bg_sigs else {}

    cells_html = ""
    for ticker in user_pairs:
        name = FOREX_PAIRS.get(ticker, {}).get("name", ticker.replace("=X", "").replace("=F", ""))
        short = name.split(" ")[0] if len(name) > 8 else name
        sig = sig_map.get(ticker)
        if sig:
            q = sig.get("q_score", 0)
        else:
            q = 0  # No scan data yet

        if q >= 6:
            bg = "rgba(0,255,204,0.25)"
            tc = "#00ffcc"
        elif q >= 3:
            bg = "rgba(0,255,204,0.10)"
            tc = "#a3ffeb"
        elif q <= -6:
            bg = "rgba(255,75,75,0.25)"
            tc = "#ff4b4b"
        elif q <= -3:
            bg = "rgba(255,75,75,0.10)"
            tc = "#ff8585"
        else:
            bg = "rgba(255,255,255,0.03)"
            tc = "#555"

        cells_html += f"""<div style="background:{bg};border:1px solid #222;border-radius:6px;
                                      padding:8px 4px;text-align:center;min-width:70px;">
            <span style="font-size:9px;color:{tc};font-family:'Orbitron';font-weight:700;">{short}</span><br>
            <span style="font-size:14px;color:{tc};font-family:'JetBrains Mono';font-weight:900;">{q:+}</span>
        </div>"""

    st.markdown(f"""
        <div style="display:flex;flex-wrap:wrap;gap:6px;justify-content:center;">
            {cells_html}
        </div>
    """, unsafe_allow_html=True)


# ============================================================
# LANDING PAGE
# ============================================================
if st.session_state.app_view == "landing":
    uname = st.session_state.get('username', 'TRADER').upper()
    st.markdown(f"""
        <div style="padding:40px 0 20px; text-align:center;">
            <p style="font-family:'Orbitron';color:#FFD700;font-size:12px;letter-spacing:3px;margin-bottom:10px;">WELCOME, {uname}</p>
            <h1 style="font-family:'Orbitron';color:#00ffcc;font-size:36px;letter-spacing:6px;margin:0;">WIDAYANKO-TERMINAL</h1>
            <p style="color:#888;font-size:14px;letter-spacing:2px;margin-top:10px;">COMMAND CENTER</p>
        </div>
    """, unsafe_allow_html=True)

    # ── ACTIVE SIGNALS FROM BG SCANNER ────────────────────────
    bg_signals, bg_time = get_last_scan_results()
    if bg_signals:
        st.markdown(f"""
            <div style="margin-bottom:20px;">
                <p style="font-family:'Orbitron';font-size:10px;color:#FFD700;letter-spacing:2px;margin:0 0 10px;">
                    🔔 ACTIVE SIGNALS ({len(bg_signals)}) — Last scan: {bg_time or 'Never'}
                </p>
            </div>
        """, unsafe_allow_html=True)
        sig_cols = st.columns(min(len(bg_signals), 3))
        for i, sig in enumerate(bg_signals[:3]):
            with sig_cols[i]:
                sc = sig.get("color", "#888")
                st.markdown(f"""
                    <div style="background:rgba(255,255,255,0.03);border:1px solid {sc}55;border-left:4px solid {sc};
                                border-radius:10px;padding:14px;text-align:center;">
                        <p style="font-family:'Orbitron';font-size:14px;color:#eee;margin:0;font-weight:900;">
                            {sig.get('pair_name','')}
                        </p>
                        <p style="font-family:'Orbitron';font-size:10px;color:{sc};margin:6px 0;letter-spacing:1px;">
                            {sig.get('decision','')}
                        </p>
                        <span style="font-size:11px;color:#888;">Q: {sig.get('q_score',0):+} · Conf: {sig.get('confidence',0)}%</span>
                    </div>
                """, unsafe_allow_html=True)
        st.divider()

    # ── HEATMAP / RANKING ─────────────────────────────────────
    _, bg_time = get_all_scan_results()
    scan_label = f" — Last scan: {bg_time}" if bg_time else ""
    st.markdown(f"""
        <p style="font-family:'Orbitron';font-size:10px;color:#555;letter-spacing:2px;margin:0 0 12px;">
            🏆 MARKET HEATMAP · TF 4H{scan_label}
        </p>
    """, unsafe_allow_html=True)
    _render_heatmap()
    st.markdown("""
        <p style="font-size:10px;color:#444;text-align:center;margin:10px 0 0;">
            📌 Pilih pair di atas untuk lihat timeframe lain · Atau pilih kategori Forex / Commodities di bawah
        </p>
    """, unsafe_allow_html=True)
    st.divider()

    # ── CATEGORY CARDS ────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
            <div style="background:rgba(0,255,204,0.05);border:1px solid #00ffcc44;border-radius:12px;padding:20px;text-align:center;height:180px;">
                <h2 style="font-family:'Orbitron';color:#eee;font-size:18px;">⚛️ FOREX</h2>
                <p style="color:#aaa;font-size:11px;">Majors & Minors</p>
                <div style="font-size:10px;color:#666;margin:10px 0;">
                    EUR/USD • GBP/USD • USD/JPY • AUD/USD • USD/CAD • USD/CHF • NZD/USD <br>
                    EUR/GBP • EUR/JPY • GBP/JPY • EUR/AUD • GBP/AUD
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("OPEN FOREX SCANNER", key="btn_forex", use_container_width=True):
            st.session_state.active_category = "Forex"
            st.session_state.app_view = "scanner"
            st.rerun()

    with col2:
        st.markdown("""
            <div style="background:rgba(255,215,0,0.05);border:1px solid rgba(255,215,0,0.3);border-radius:12px;padding:20px;text-align:center;height:180px;">
                <h2 style="font-family:'Orbitron';color:#eee;font-size:18px;">🛢️ COMMODITIES</h2>
                <p style="color:#aaa;font-size:11px;">Metals, Energy, Agriculture</p>
                <div style="font-size:10px;color:#666;margin:10px 0;line-height:1.6;">
                    Gold • Silver • Copper<br>
                    WTI • NatGas • Wheat • Coffee • Cocoa
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("OPEN COMMODITIES", key="btn_commo", use_container_width=True):
            st.session_state.active_category = "Commodities"
            st.session_state.app_view = "scanner"
            st.rerun()

    with col3:
        st.markdown("""
            <div style="background:rgba(138,43,226,0.08);border:1px solid rgba(138,43,226,0.3);border-radius:12px;padding:20px;text-align:center;height:180px;">
                <h2 style="font-family:'Orbitron';color:#eee;font-size:18px;">🪙 CRYPTO</h2>
                <p style="color:#aaa;font-size:11px;">Top 5 Coins</p>
                <div style="font-size:10px;color:#666;margin:10px 0;line-height:1.6;">
                    Bitcoin • Ethereum • Solana<br>
                    Avalanche • Sui
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("OPEN CRYPTO SCANNER", key="btn_crypto", use_container_width=True):
            st.session_state.active_category = "Crypto"
            st.session_state.app_view = "scanner"
            st.rerun()
            
    st.stop()



# ============================================================
# SCANNER MODE
# ============================================================
tf = "4h" if st.session_state.app_view == "scanner" else st.session_state.get("detail_tf", "4h")

if st.session_state.app_view == "scanner":
    cat = st.session_state.active_category
    icon = "⚛️" if cat == "Forex" else "🛢️"
    color = "#00ffcc" if cat == "Forex" else "#FFD700"
    st.markdown(f"""
        <div style="padding:20px 0 10px;">
            <p style="font-family:'Orbitron';font-size:20px;color:{color};letter-spacing:4px;margin:0;">{icon} {cat.upper()} SCANNER</p>
            <p style="color:#444;font-size:11px;margin:4px 0 0;">Quantum AI Analysis</p>
        </div>
    """, unsafe_allow_html=True)
    render_forex_scanner(tf=tf, category=cat)
    st.stop()


# ============================================================
# FOREX MODE — DATA ENGINE
# ============================================================
active_ticker = st.session_state.active_ticker
if active_ticker and not has_pair_access(st.session_state.get("username", ""), active_ticker):
    st.error("Access Denied. You do not have permission to view this asset.")
    if st.button("🔙 BACK TO SCANNER"):
        st.session_state.app_view = "scanner"
        st.session_state.active_ticker = None
        st.rerun()
    st.stop()

try:
    macro     = fetch_macro_data()
    df_raw    = fetch_forex_data(active_ticker, "30d", tf)
    df        = hitung_indikator_lengkap(df_raw)
    si, sd, raw_news = get_market_sentiment(active_ticker)

    sent_exp = ""
    if raw_news and isinstance(raw_news[0], dict):
        t_ = raw_news[0].get('title', '')
        sent_exp = (t_[:75] + '...') if len(t_) > 75 else t_

    news_alerts = check_news_shield(active_ticker)
    fib_levels  = calculate_fibonacci_levels(df)
    last_close  = df.iloc[-1]['Close']
    prev_close  = df.iloc[-2]['Close']
    price_delta = last_close - prev_close
    pct_delta   = (price_delta / prev_close) * 100
    dc          = "#00ffcc" if price_delta >= 0 else "#ff4b4b"

    # HTF Bias (same period as main data)
    htf_tf     = "4h" if tf in ("15m", "1h") else ("1d" if tf == "4h" else "1wk")
    df_htf_raw = fetch_forex_data(active_ticker, "60d", htf_tf)
    df_htf     = hitung_indikator_lengkap(df_htf_raw)
    htf_bias   = 1 if df_htf.iloc[-1]['Close'] > df_htf.iloc[-1]['EMA50'] else -1

    score_res = get_detailed_scores_v12(df, macro, si, fib_levels, htf_bias, sent_exp)
    smc_zones = deteksi_smc_v2(df)
    last_atr  = float(df.iloc[-1].get('ATR', 0)) if 'ATR' in df.columns else None
    ai_data   = generate_ai_judgment(score_res, fib_levels, smc_zones, last_close, atr=last_atr)
    sessions, _, m_note, m_color = get_market_sessions()

    # Crypto markets are 24/7 — override session info
    asset_group = FOREX_PAIRS.get(active_ticker, {}).get('group', '')
    if asset_group == "Crypto":
        sessions = ["24/7"]
        m_note = "PASAR CRYPTO BUKA 24/7"
        m_color = "#a855f7"

    # ── GLOBAL TELEMETRY HEADER ─────────────────────────────
    pair_name = FOREX_PAIRS.get(active_ticker, {}).get('name', active_ticker.replace('=X', ''))
    h1, h2, h3, h4 = st.columns([3, 1, 1, 1])

    with h1:
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid #1a1a1a;border-left:3px solid {dc};
                        padding:12px 18px;border-radius:8px;">
                <p style="font-size:9px;color:#555;letter-spacing:1px;margin:0;">INSTRUMENT FEED</p>
                <div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;">
                    <span style="font-family:'Orbitron';font-size:20px;color:#eee;letter-spacing:1px;">{pair_name}</span>
                    <span style="font-family:'JetBrains Mono';font-size:24px;color:{dc};">{last_close:,.5f}</span>
                    <span style="font-family:'JetBrains Mono';font-size:12px;color:{dc};">{price_delta:+.5f} ({pct_delta:+.2f}%)</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with h2:
        dxy_v = macro.get('dxy_val', 0)
        dxy_c = "#ff4b4b" if macro.get('dxy_rel') else "#00ffcc"
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid #1a1a1a;border-left:3px solid #FFD700;
                        padding:12px 18px;border-radius:8px;height:100%;">
                <p style="font-size:9px;color:#555;letter-spacing:1px;margin:0;">DXY INDEX</p>
                <b style="font-family:'JetBrains Mono';font-size:20px;color:#eee;">{dxy_v:.3f}</b>
                <span style="font-size:12px;color:{dxy_c};">{'▲' if macro.get('dxy_rel') else '▼'}</span>
            </div>
        """, unsafe_allow_html=True)

    with h3:
        ai_color = ai_data.get('color', '#888')
        ai_dec   = ai_data.get('decision', 'STANDBY')
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid #1a1a1a;border-left:3px solid {ai_color};
                        padding:12px 18px;border-radius:8px;height:100%;">
                <p style="font-size:9px;color:#555;letter-spacing:1px;margin:0;">AI VERDICT</p>
                <b style="font-family:'Orbitron';font-size:11px;color:{ai_color};">{ai_dec}</b>
            </div>
        """, unsafe_allow_html=True)

    with h4:
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid #1a1a1a;border-left:3px solid {m_color};
                        padding:12px 18px;border-radius:8px;height:100%;">
                <p style="font-size:9px;color:#555;letter-spacing:1px;margin:0;">SESSION</p>
                <b style="font-family:'Orbitron';font-size:11px;color:{m_color};letter-spacing:1px;">{m_note}</b>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # News shield alert banner
    if news_alerts:
        st.warning(f"⚠️ **NEWS SHIELD ACTIVE** — {len(news_alerts)} high-impact event detected: {news_alerts[0][:80]}")

    # ── TELEGRAM SIGNAL TRIGGER ────────────────────────────────
    q_total = score_res.get('total', 0)
    if tf == "4h" and abs(q_total) >= 8 and ai_data.get('decision') in ('EXECUTE BUY', 'EXECUTE SELL'):
        notif_key = f"sig_{active_ticker}_{df.index[-1]}"
        if notif_key not in st.session_state:
            plan    = ai_data.get('plan', {})
            entry   = plan.get('entry', 0)
            sl      = plan.get('sl', 0)
            tp1     = plan.get('tp1', 0)
            tp2     = plan.get('tp2', 0)
            tp3     = plan.get('tp3', 0)
            rr3     = plan.get('rr3', 0)
            sl_pips = plan.get('pips_sl', 0)

            # Formatter: detect JPY/commodity vs standard forex
            def _fmt(v):
                if v == 0: return "—"
                if last_close > 10:  return f"{v:,.3f}"
                return f"{v:,.5f}"

            from data_provider import get_mtf_scores
            mtf = get_mtf_scores(active_ticker, macro, si)
            mtf_str = f"15m: {mtf.get('15m',0):+} | 1H: {mtf.get('1h',0):+} | 1D: {mtf.get('1d',0):+}"

            msg = (
                f"⚛️ *WIDAYANKO-TERMINAL v2.0 — SIGNAL*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 Pair: *{pair_name}*\n"
                f"💰 Price: `{last_close:,.5f}`\n"
                f"🧠 Verdict: *{ai_data['decision']}*\n"
                f"📈 Confidence: {ai_data['confidence']}%\n"
                f"⚡ Q-Score (4H): {q_total:+} / ±15\n"
                f"⏱️ MTF Scores: {mtf_str}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 Entry Zone: `{_fmt(entry)}`\n"
                f"🛑 Stop Loss:  `{_fmt(sl)}` ({sl_pips} pips)\n"
                f"TP1 (1:1):    `{_fmt(tp1)}`\n"
                f"TP2 (2:1):    `{_fmt(tp2)}`\n"
                f"TP3 (3:1):    `{_fmt(tp3)}` ← Target\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📐 R:R Ratio: *1 : {rr3:.1f}*\n"
                f"⏰ TF: {tf.upper()} | Session: {m_note}"
            )
            send_telegram_alert(msg)
            log_signal(
                ticker=active_ticker,
                pair_name=pair_name,
                decision=ai_data['decision'],
                confidence=ai_data.get('confidence', 0),
                q_score=q_total,
                pa_signal=ai_data.get('pa_signal', 'NONE'),
                plan=plan,
                price=last_close,
            )
            st.session_state[notif_key] = True

    # ── MAIN TABS ────────────────────────────────────────────
    st.markdown("<div style='margin-top: -30px;'></div>", unsafe_allow_html=True)
    _, col_tf = st.columns([6, 1])
    with col_tf:
        new_tf = st.selectbox("TF", ["15m", "1h", "4h", "1d"], index=["15m", "1h", "4h", "1d"].index(tf), label_visibility="collapsed")
        if new_tf != tf:
            st.session_state.detail_tf = new_tf
            st.rerun()

    tab_q, tab_n, tab_ai, tab_bt = st.tabs(["⚛️ QUANTUM DATA", "📰 NEWS FEED", "🧠 AI FINAL VERDICT", "📊 BACKTEST HISTORY"])

    with tab_q:
        render_quantum_tab(active_ticker, df, score_res, macro, sd)

    with tab_n:
        # Lazy-load news only when this tab is active
        ticker_news = fetch_ticker_news(active_ticker)
        render_news_tab(active_ticker, ticker_news)

    with tab_ai:
        render_ai_verdict_tab(active_ticker, ai_data)

    with tab_bt:
        st.markdown("<br><p style='font-family:Orbitron;color:#aaa;font-size:14px;letter-spacing:2px;'>HISTORICAL STRATEGY VALIDATION</p>", unsafe_allow_html=True)
        bt_res = run_backtest(df)
        if bt_res['total_trades'] == 0:
            st.info("Not enough historical volatility/signals found to run a valid backtest.")
        else:
            w_rate = bt_res['win_rate']
            c_color = "#00ffcc" if w_rate >= 50 else "#ff4b4b"
            p_color = "#00ffcc" if bt_res['pips_net'] >= 0 else "#ff4b4b"
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""<div style="background:rgba(255,255,255,0.03);padding:16px;border-radius:12px;border:1px solid #333;text-align:center;">
                    <p style="font-size:10px;color:#888;font-family:'Orbitron';">TOTAL TRADES</p>
                    <h2 style="margin:0;color:#eee;">{bt_res['total_trades']}</h2>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div style="background:rgba(255,255,255,0.03);padding:16px;border-radius:12px;border:1px solid #333;text-align:center;">
                    <p style="font-size:10px;color:#888;font-family:'Orbitron';">WIN RATE (3:1 R:R)</p>
                    <h2 style="margin:0;color:{c_color};">{w_rate:.1f}%</h2>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div style="background:rgba(255,255,255,0.03);padding:16px;border-radius:12px;border:1px solid #333;text-align:center;">
                    <p style="font-size:10px;color:#888;font-family:'Orbitron';">NET PROFIT (PIPS)</p>
                    <h2 style="margin:0;color:{p_color};">{bt_res['pips_net']:+,.1f}</h2>
                </div>""", unsafe_allow_html=True)
                
            st.markdown("<br><p style='font-family:Orbitron;color:#888;font-size:11px;letter-spacing:1px;'>RECENT VIRTUAL TRADES</p>", unsafe_allow_html=True)
            for t in reversed(bt_res['history']):
                res_col = "#00ffcc" if t['result'] == "WIN" else "#ff4b4b"
                bg_col = "rgba(0,255,204,0.05)" if t['result'] == "WIN" else "rgba(255,75,75,0.05)"
                st.markdown(f"""
                <div style="background:{bg_col};border-left:3px solid {res_col};padding:10px 16px;margin-bottom:8px;border-radius:4px;display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <b style="font-family:'Orbitron';color:#eee;">{t['type']}</b> <span style="color:#555;font-size:12px;">| {t['exit_time'].strftime('%Y-%m-%d %H:%M')}</span>
                    </div>
                    <div style="text-align:right;">
                        <b style="color:{res_col};">{t['result']}</b><br>
                        <span style="font-size:10px;color:#888;">{t['pips']:+,.1f} pips</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"🛑 TERMINAL CORE ERROR: {e}")
    import traceback
    tb = traceback.format_exc()
    with open("error_log.txt", "w") as f:
        f.write(tb)
    st.code(tb)