"""
auto_trader_ui.py — Auto Trade Simulator UI
Widayanko Terminal v2.0
"""
import streamlit as st
from data_provider import FOREX_PAIRS, get_forex_list, fetch_forex_data
from auto_trader import (
    create_profile, get_profiles, update_profile, delete_profile,
    toggle_profile, get_sim_trades, run_auto_scan, sync_sim_trades,
    get_profile_stats, get_unrealized_pnl, manual_close_sim_trade,
    generate_trade_review, LOT_PRESETS
)

_CSS = """
<style>
.at-card{background:rgba(255,255,255,0.03);border:1px solid #222;border-radius:12px;padding:16px;margin-bottom:12px;}
.at-header{font-family:'Orbitron',sans-serif;font-size:10px;letter-spacing:2px;color:#555;margin:0 0 4px;}
.at-val{font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;}
.at-badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:10px;font-family:'Orbitron',sans-serif;letter-spacing:1px;}
.at-row{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;
        background:rgba(255,255,255,0.02);border:1px solid #1a1a1a;border-radius:8px;margin-bottom:6px;}
</style>
"""

def _fmt_price(v, ticker=""):
    if v is None or v == 0: return "—"
    if v > 100: return f"{v:,.3f}"
    return f"{v:,.5f}"

def _pnl_color(v):
    if v is None: return "#888"
    return "#00ffcc" if v >= 0 else "#ff4b4b"

def _direction_badge(d):
    if d == "BUY":
        return "<span class='at-badge' style='background:rgba(0,255,204,0.15);color:#00ffcc;border:1px solid #00ffcc55;'>▲ BUY</span>"
    return "<span class='at-badge' style='background:rgba(255,75,75,0.15);color:#ff4b4b;border:1px solid #ff4b4b55;'>▼ SELL</span>"

def _status_badge(s):
    colors = {"OPEN": "#FFD700", "WIN": "#00ffcc", "LOSS": "#ff4b4b", "BE": "#aaa"}
    c = colors.get(s, "#888")
    return f"<span class='at-badge' style='background:{c}22;color:{c};border:1px solid {c}55;'>{s}</span>"


def _render_trade_review(trade: dict):
    """Render review panel untuk satu closed trade."""
    rv = generate_trade_review(trade)
    result = rv["result"]
    res_color = {"WIN": "#00ffcc", "LOSS": "#ff4b4b", "BE": "#aaa"}.get(result, "#888")
    pnl_sign = "+" if rv["pnl_usd"] >= 0 else ""
    pips_sign = "+" if rv["pips"] >= 0 else ""

    # Header summary
    st.markdown(f"""
        <div style='display:flex;flex-wrap:wrap;gap:16px;padding:12px 0;border-bottom:1px solid #1a1a1a;margin-bottom:14px;'>
            <div><p class='at-header'>HASIL</p>
                <p style='font-family:Orbitron;color:{res_color};font-size:16px;margin:0;font-weight:900;'>{result}</p></div>
            <div><p class='at-header'>PnL</p>
                <p style='font-family:JetBrains Mono;color:{res_color};font-size:16px;margin:0;'>{pnl_sign}${rv['pnl_usd']:.2f}</p></div>
            <div><p class='at-header'>PIPS</p>
                <p style='font-family:JetBrains Mono;color:{res_color};font-size:14px;margin:0;'>{pips_sign}{rv['pips']:.1f}</p></div>
            <div><p class='at-header'>Q-SCORE SAAT ENTRY</p>
                <p style='font-family:JetBrains Mono;color:{rv['quality_color']};font-size:14px;margin:0;'>{rv['q_score']:+} — {rv['signal_quality']}</p></div>
            <div><p class='at-header'>CONFLUENCE</p>
                <p style='font-family:JetBrains Mono;color:#FFD700;font-size:14px;margin:0;'>{rv['alignment_pct']}% {rv['aligned_label'].upper()}</p></div>
            <div><p class='at-header'>PA SIGNAL</p>
                <p style='font-size:11px;color:#aaa;margin:0;'>{rv['pa_signal'] or 'NONE'}</p></div>
            <div><p class='at-header'>CLOSE REASON</p>
                <p style='font-size:11px;color:#aaa;margin:0;'>{rv['close_reason']}</p></div>
        </div>
    """, unsafe_allow_html=True)

    # Indicator breakdown
    col_bull, col_bear = st.columns(2)
    with col_bull:
        st.markdown("<p style='font-family:Orbitron;color:#00ffcc;font-size:10px;letter-spacing:1px;'>✅ FAKTOR BULLISH</p>", unsafe_allow_html=True)
        if rv["bullish_factors"]:
            for f in rv["bullish_factors"]:
                st.markdown(f"""
                    <div style='background:rgba(0,255,204,0.05);border-left:3px solid #00ffcc44;
                                padding:8px 10px;border-radius:4px;margin-bottom:5px;'>
                        <p style='font-size:11px;color:#00ffcc;margin:0;font-weight:600;'>{f['label']} <span style='color:#555;'>(+{f['score']})</span></p>
                        <p style='font-size:10px;color:#555;margin:2px 0 0;'>{f['detail'][:100] if f['detail'] else ''}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("<p style='font-size:11px;color:#333;'>Tidak ada faktor bullish</p>", unsafe_allow_html=True)

    with col_bear:
        st.markdown("<p style='font-family:Orbitron;color:#ff4b4b;font-size:10px;letter-spacing:1px;'>❌ FAKTOR BEARISH</p>", unsafe_allow_html=True)
        if rv["bearish_factors"]:
            for f in rv["bearish_factors"]:
                st.markdown(f"""
                    <div style='background:rgba(255,75,75,0.05);border-left:3px solid #ff4b4b44;
                                padding:8px 10px;border-radius:4px;margin-bottom:5px;'>
                        <p style='font-size:11px;color:#ff4b4b;margin:0;font-weight:600;'>{f['label']} <span style='color:#555;'>({f['score']})</span></p>
                        <p style='font-size:10px;color:#555;margin:2px 0 0;'>{f['detail'][:100] if f['detail'] else ''}</p>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("<p style='font-size:11px;color:#333;'>Tidak ada faktor bearish</p>", unsafe_allow_html=True)

    # Lessons learned
    st.markdown("<p style='font-family:Orbitron;color:#FFD700;font-size:10px;letter-spacing:1px;margin-top:14px;'>📚 LESSON LEARNED</p>", unsafe_allow_html=True)
    for lesson in rv["lessons"]:
        st.markdown(f"<p style='font-size:12px;color:#ccc;padding:4px 0;border-bottom:1px solid #111;'>{lesson}</p>", unsafe_allow_html=True)

    # AI Reasoning (if stored)
    if rv.get("reasoning"):
        with st.expander("🧠 AI Reasoning Chain saat Entry"):
            for r in rv["reasoning"]:
                st.markdown(f"<p style='font-size:11px;color:#888;'>• {r}</p>", unsafe_allow_html=True)


# ============================================================
# TAB 1 — PROFILE MANAGER
# ============================================================
def _tab_profiles(username):
    st.markdown("""
        <p style='font-family:Orbitron;color:#00ffcc;font-size:11px;letter-spacing:2px;margin-bottom:16px;'>
        ⚙️ KELOLA PROFIL TRADING OTOMATIS</p>
    """, unsafe_allow_html=True)

    profiles = get_profiles(username)

    # ── Existing Profiles ──────────────────────────────────
    if profiles:
        st.markdown("<p style='font-family:Orbitron;color:#888;font-size:10px;letter-spacing:1px;'>PROFIL AKTIF</p>", unsafe_allow_html=True)
        for p in profiles:
            is_on = p.get("is_active", True)
            dot   = "🟢" if is_on else "⚫"
            with st.expander(f"{dot} **{p['name']}** — ${p['capital']:,.0f} | {p['lot_size']} lot | {len(p.get('pairs',[]))} pairs"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Modal", f"${p['capital']:,.0f}")
                c2.metric("Lot Size", str(p['lot_size']))
                c3.metric("Pairs", len(p.get('pairs', [])))

                c4, c5 = st.columns(2)
                c4.metric("Min Q-Score", f"±{p.get('min_q_score',8)}")
                c5.metric("Max Open", p.get('max_open_trades', 3))

                st.markdown(f"<p style='font-size:11px;color:#555;'>Pairs: {', '.join(p.get('pairs',[])[:8])}</p>", unsafe_allow_html=True)
                if p.get("last_scan_at"):
                    st.markdown(f"<p style='font-size:10px;color:#444;'>Last scan: {p['last_scan_at'][:16]}</p>", unsafe_allow_html=True)

                btn1, btn2, btn3 = st.columns(3)
                if btn1.button("▶/⏸ Toggle", key=f"tog_{p['id']}"):
                    new_state = toggle_profile(p["id"])
                    st.toast(f"Profil {'AKTIF' if new_state else 'NONAKTIF'}", icon="✅")
                    st.rerun()
                if btn2.button("🔄 Scan Sekarang", key=f"scan_{p['id']}"):
                    with st.spinner("Scanning market..."):
                        res = run_auto_scan(p)
                    st.success(f"✅ {res['new_orders']} order baru | {res['skipped']} skip | {res['errors']} error")
                    for d in res["details"]:
                        st.markdown(f"<p style='font-size:11px;color:#aaa;'>{d}</p>", unsafe_allow_html=True)
                    st.rerun()
                if btn3.button("🗑️ Hapus", key=f"del_{p['id']}"):
                    delete_profile(p["id"])
                    st.toast("Profil dihapus", icon="🗑️")
                    st.rerun()

        st.divider()

    # ── Create New Profile ─────────────────────────────────
    with st.expander("➕ BUAT PROFIL BARU", expanded=not bool(profiles)):
        name = st.text_input("Nama Profil", placeholder="Contoh: Aggressive 4H", key="at_pname")
        capital = st.number_input("Modal Simulasi (USD)", min_value=100.0, max_value=1_000_000.0,
                                   value=1000.0, step=100.0, key="at_cap")

        # Lot selection
        lot_label = st.selectbox("Ukuran Lot", list(LOT_PRESETS.keys()), key="at_lot_sel")
        if LOT_PRESETS[lot_label] is None:
            lot_size = st.number_input("Lot Custom", min_value=0.0001, max_value=100.0,
                                        value=0.05, step=0.001, format="%.4f", key="at_lot_custom")
        else:
            lot_size = LOT_PRESETS[lot_label]
            st.info(f"💡 Lot size: **{lot_size}** lot")

        # Pair selector grouped by category
        all_pairs = get_forex_list()
        pair_display = {}
        for t in all_pairs:
            info = FOREX_PAIRS.get(t, {})
            pair_display[t] = f"{info.get('name', t)} [{info.get('group','Forex')}]"

        selected_pairs = st.multiselect(
            "Pilih Pair yang Dimonitor",
            options=list(pair_display.keys()),
            format_func=lambda x: pair_display.get(x, x),
            default=["EURUSD=X", "GBPUSD=X", "USDJPY=X"] if "EURUSD=X" in pair_display else [],
            key="at_pairs"
        )

        col_a, col_b = st.columns(2)
        with col_a:
            min_q = st.slider("Min Q-Score untuk Execute", 5, 15, 8, key="at_minq",
                               help="Makin tinggi = makin selektif. Rekomendasi: 8")
            sl_mult = st.number_input("SL Multiplier (×ATR)", 0.5, 5.0, 1.5, 0.5, key="at_sl")
        with col_b:
            max_open = st.slider("Max Trade Open Sekaligus", 1, 10, 3, key="at_maxo")
            tp_mult = st.number_input("TP Multiplier (×ATR)", 1.0, 10.0, 4.5, 0.5, key="at_tp")

        if st.button("✅ BUAT PROFIL", use_container_width=True, type="primary", key="at_create"):
            if not name.strip():
                st.error("Nama profil tidak boleh kosong!")
            elif not selected_pairs:
                st.error("Pilih minimal 1 pair!")
            else:
                create_profile(
                    owner=username, name=name.strip(), capital=capital,
                    lot_size=lot_size, pairs=selected_pairs,
                    min_q_score=min_q, max_open_trades=max_open,
                    sl_atr_mult=sl_mult, tp_atr_mult=tp_mult
                )
                st.success(f"✅ Profil '{name}' berhasil dibuat!")
                st.rerun()


# ============================================================
# TAB 2 — LIVE MONITOR
# ============================================================
def _tab_monitor(username):
    profiles = get_profiles(username)
    if not profiles:
        st.info("Belum ada profil. Buat profil dulu di tab **Profil Manager**.")
        return

    # Profile selector
    pnames = {p["id"]: p["name"] for p in profiles}
    sel_id = st.selectbox("Pilih Profil", list(pnames.keys()),
                           format_func=lambda x: pnames[x], key="at_mon_sel")
    sel_profile = next((p for p in profiles if p["id"] == sel_id), None)
    if not sel_profile:
        return

    # Quick action buttons
    bc1, bc2, bc3 = st.columns(3)
    if bc1.button("🔄 Scan & Place Orders", use_container_width=True, key="at_mon_scan"):
        with st.spinner("Scanning market untuk semua pair..."):
            res = run_auto_scan(sel_profile)
        st.success(f"✅ {res['new_orders']} order baru dibuka | {res['skipped']} skip | {res['errors']} error")
        with st.expander("Detail Scan"):
            for d in res["details"]:
                st.markdown(f"<p style='font-size:11px;color:#aaa;'>{d}</p>", unsafe_allow_html=True)
        st.rerun()

    if bc2.button("⚡ Sync SL/TP", use_container_width=True, key="at_mon_sync"):
        with st.spinner("Checking SL/TP..."):
            n = sync_sim_trades(sel_id)
        st.success(f"✅ {n} trade auto-closed oleh SL/TP")
        st.rerun()

    if bc3.button("🔃 Refresh", use_container_width=True, key="at_mon_refresh"):
        st.rerun()

    st.divider()

    # ── Open Trades ───────────────────────────────────────
    open_trades = get_sim_trades(sel_id, status_filter="OPEN")
    st.markdown(f"""
        <p style='font-family:Orbitron;color:#FFD700;font-size:10px;letter-spacing:2px;'>
        📡 OPEN TRADES ({len(open_trades)})</p>
    """, unsafe_allow_html=True)

    if not open_trades:
        st.markdown("""
            <div class='at-card' style='text-align:center;padding:30px;'>
                <p style='color:#555;font-family:Orbitron;font-size:12px;'>TIDAK ADA TRADE OPEN</p>
                <p style='color:#333;font-size:11px;'>Klik "Scan & Place Orders" untuk mulai trading otomatis</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        for t in open_trades:
            ticker = t["ticker"]
            # Get live price
            try:
                df_live = fetch_forex_data(ticker, "1d", "15m")
                cur_price = float(df_live.iloc[-1]["Close"]) if df_live is not None and not df_live.empty else t["entry_price"]
            except Exception:
                cur_price = t["entry_price"]

            unreal_pnl = get_unrealized_pnl(t, cur_price)
            pnl_col = _pnl_color(unreal_pnl)
            pnl_sign = "+" if unreal_pnl >= 0 else ""

            st.markdown(f"""
                <div class='at-card' style='border-left:3px solid {pnl_col};'>
                    <div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;'>
                        <div>
                            <p style='font-family:Orbitron;color:#eee;font-size:14px;margin:0;font-weight:900;'>{t['pair_name']}</p>
                            <div style='margin-top:4px;'>{_direction_badge(t['direction'])} &nbsp;
                            <span style='font-size:10px;color:#555;'>Q:{t.get('q_score',0):+} | Conf:{t.get('confidence',0)}%</span></div>
                        </div>
                        <div style='text-align:right;'>
                            <p style='font-family:JetBrains Mono;font-size:20px;color:{pnl_col};margin:0;font-weight:700;'>{pnl_sign}${unreal_pnl:.2f}</p>
                            <p style='font-size:10px;color:#555;margin:0;'>Unrealized PnL</p>
                        </div>
                    </div>
                    <div style='display:flex;gap:20px;margin-top:12px;flex-wrap:wrap;'>
                        <div><p class='at-header'>ENTRY</p><p style='font-family:JetBrains Mono;color:#eee;font-size:13px;margin:0;'>{_fmt_price(t['entry_price'],ticker)}</p></div>
                        <div><p class='at-header'>LIVE</p><p style='font-family:JetBrains Mono;color:#FFD700;font-size:13px;margin:0;'>{_fmt_price(cur_price,ticker)}</p></div>
                        <div><p class='at-header'>SL</p><p style='font-family:JetBrains Mono;color:#ff4b4b;font-size:13px;margin:0;'>{_fmt_price(t['sl'],ticker)}</p></div>
                        <div><p class='at-header'>TP2</p><p style='font-family:JetBrains Mono;color:#00ffcc;font-size:13px;margin:0;'>{_fmt_price(t['tp2'],ticker)}</p></div>
                        <div><p class='at-header'>LOT</p><p style='font-family:JetBrains Mono;color:#aaa;font-size:13px;margin:0;'>{t['lot_size']}</p></div>
                        <div><p class='at-header'>OPENED</p><p style='font-size:11px;color:#555;margin:0;'>{t.get('opened_at_str','')[:16]}</p></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if st.button(f"❌ Close Manual — {t['pair_name']}", key=f"cls_{t['id']}"):
                manual_close_sim_trade(t["id"])
                st.toast(f"Trade {t['pair_name']} ditutup manual", icon="✅")
                st.rerun()

    st.divider()

    # ── Recent Closed ─────────────────────────────────────
    closed_trades = get_sim_trades(sel_id)
    closed_trades = [t for t in closed_trades if t.get("status") in ("WIN", "LOSS", "BE")][:10]

    st.markdown(f"""
        <p style='font-family:Orbitron;color:#888;font-size:10px;letter-spacing:2px;'>
        📋 RIWAYAT TRADE TERAKHIR ({len(closed_trades)})</p>
    """, unsafe_allow_html=True)

    for t in closed_trades:
        pnl  = t.get("pnl_usd", 0) or 0
        pips = t.get("pips_result", 0) or 0
        pnl_col = _pnl_color(pnl)
        sign = "+" if pnl >= 0 else ""
        res_icon = "✅" if t["status"] == "WIN" else ("❌" if t["status"] == "LOSS" else "⚖️")
        label = f"{res_icon} {t['pair_name']} | {t['direction']} | {sign}${pnl:.2f} ({sign}{pips:.1f}p) | {t.get('closed_at','')[:13]}"
        with st.expander(label):
            _render_trade_review(t)


# ============================================================
# TAB 3 — STATISTIK
# ============================================================
def _tab_stats(username):
    profiles = get_profiles(username)
    if not profiles:
        st.info("Belum ada profil. Buat profil dulu di tab **Profil Manager**.")
        return

    pnames = {p["id"]: p["name"] for p in profiles}
    sel_id = st.selectbox("Pilih Profil", list(pnames.keys()),
                           format_func=lambda x: pnames[x], key="at_stat_sel")

    stats = get_profile_stats(sel_id)
    if not stats:
        st.warning("Profil tidak ditemukan.")
        return

    profile = stats["profile"]
    lot_size = profile.get("lot_size", 0.01)
    capital = profile.get("capital", 1000)

    # ── Header KPIs ───────────────────────────────────────
    st.markdown(f"""
        <div class='at-card' style='border-left:3px solid #00ffcc;margin-bottom:20px;'>
            <p style='font-family:Orbitron;color:#00ffcc;font-size:13px;letter-spacing:2px;margin:0 0 4px;'>{profile['name']}</p>
            <p style='color:#555;font-size:11px;margin:0;'>Modal: ${capital:,.0f} | Lot: {lot_size} | Pairs: {len(profile.get('pairs',[]))} pair</p>
        </div>
    """, unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    wr_col = "#00ffcc" if stats["win_rate"] >= 50 else "#ff4b4b"
    pnl_col = _pnl_color(stats["net_pnl_usd"])
    sign = "+" if stats["net_pnl_usd"] >= 0 else ""

    with k1:
        st.markdown(f"""<div class='at-card' style='text-align:center;'>
            <p class='at-header'>TOTAL TRADES</p>
            <p class='at-val' style='color:#eee;'>{stats['total_trades']}</p>
            <p style='font-size:10px;color:#555;margin:0;'>Open: {stats['open_trades']} | Closed: {stats['total_closed']}</p>
        </div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""<div class='at-card' style='text-align:center;'>
            <p class='at-header'>WIN RATE</p>
            <p class='at-val' style='color:{wr_col};'>{stats['win_rate']:.1f}%</p>
            <p style='font-size:10px;color:#555;margin:0;'>{stats['wins']}W / {stats['losses']}L</p>
        </div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""<div class='at-card' style='text-align:center;'>
            <p class='at-header'>NET PnL</p>
            <p class='at-val' style='color:{pnl_col};'>{sign}${stats['net_pnl_usd']:.2f}</p>
            <p style='font-size:10px;color:#555;margin:0;'>{sign}{stats['net_pips']:.1f} pips</p>
        </div>""", unsafe_allow_html=True)
    with k4:
        dd_col = "#ff4b4b" if stats["max_drawdown"] > 0 else "#00ffcc"
        roi = (stats["net_pnl_usd"] / capital * 100) if capital else 0
        roi_sign = "+" if roi >= 0 else ""
        st.markdown(f"""<div class='at-card' style='text-align:center;'>
            <p class='at-header'>ROI / MAX DD</p>
            <p class='at-val' style='color:{_pnl_color(roi)};'>{roi_sign}{roi:.2f}%</p>
            <p style='font-size:10px;color:{dd_col};margin:0;'>DD: ${stats['max_drawdown']:.2f}</p>
        </div>""", unsafe_allow_html=True)

    # ── Equity Curve ──────────────────────────────────────
    eq = stats.get("equity_curve", [])
    if len(eq) >= 2:
        st.markdown("<p style='font-family:Orbitron;color:#888;font-size:10px;letter-spacing:2px;margin-top:20px;'>📈 EQUITY CURVE</p>", unsafe_allow_html=True)
        import pandas as pd
        eq_df = pd.DataFrame({"Equity (USD)": eq})
        st.line_chart(eq_df, color="#00ffcc")

    # ── Trade Log ─────────────────────────────────────────
    all_t = stats.get("all_trades", [])
    if all_t:
        st.divider()
        st.markdown("<p style='font-family:Orbitron;color:#888;font-size:10px;letter-spacing:2px;'>📋 SEMUA TRADE</p>", unsafe_allow_html=True)
        for t in all_t[:20]:
            pnl  = t.get("pnl_usd") or 0
            pips = t.get("pips_result") or 0
            sign = "+" if pnl >= 0 else ""
            res_icon = "✅" if t.get("status") == "WIN" else ("❌" if t.get("status") == "LOSS" else ("📡" if t.get("status") == "OPEN" else "⚖️"))
            label = f"{res_icon} {t['pair_name']} | {t['direction']} | {sign}${pnl:.2f} | {t.get('opened_at_str','')[:13]}"
            with st.expander(label):
                if t.get("status") in ("WIN", "LOSS", "BE"):
                    _render_trade_review(t)
                else:
                    st.markdown(f"<p style='color:#555;font-size:12px;'>Trade masih OPEN — review tersedia setelah ditutup.</p>", unsafe_allow_html=True)


# ============================================================
# MAIN RENDER
# ============================================================
def render_auto_trader_page():
    username = st.session_state.get("username", "")
    role     = st.session_state.get("role", "")

    # ── ADMIN ONLY GUARD ──────────────────────────────────
    if role != "admin":
        st.markdown("""
            <div style='text-align:center;padding:60px 20px;'>
                <p style='font-size:48px;margin:0;'>🔒</p>
                <p style='font-family:Orbitron;color:#ff4b4b;font-size:18px;letter-spacing:3px;margin:16px 0 8px;'>AKSES DITOLAK</p>
                <p style='color:#555;font-size:13px;'>Fitur Auto Trade Simulator hanya tersedia untuk <b style='color:#FFD700;'>Admin</b>.</p>
            </div>
        """, unsafe_allow_html=True)
        return

    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown("""
        <div style='padding:20px 0 10px;'>
            <p style='font-family:Orbitron;font-size:20px;color:#00ffcc;letter-spacing:4px;margin:0;'>🤖 AUTO TRADE SIMULATOR</p>
            <p style='color:#444;font-size:11px;margin:4px 0 0;'>Paper Trading Otomatis — Berbasis Quantum V12 Engine · Admin Only</p>
        </div>
    """, unsafe_allow_html=True)

    # ── AUTO-SYNC saat halaman dibuka ─────────────────────
    # Cek semua profil aktif, sync SL/TP berdasarkan data historis
    # Ini yang bikin: buka web tgl 3, order masuk tgl 2 → tetap akurat
    profiles = get_profiles(username)
    total_synced = 0
    for p in profiles:
        if p.get("is_active"):
            n = sync_sim_trades(p["id"])
            total_synced += n
    if total_synced > 0:
        st.success(f"⚡ Auto-sync: **{total_synced} trade** ditutup otomatis berdasarkan data historis (SL/TP kena saat web tutup)")

    tab1, tab2, tab3 = st.tabs(["⚙️ PROFIL MANAGER", "📡 MONITOR LIVE", "📊 STATISTIK"])

    with tab1:
        _tab_profiles(username)
    with tab2:
        _tab_monitor(username)
    with tab3:
        _tab_stats(username)
