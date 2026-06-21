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
    generate_trade_review, LOT_PRESETS,
    check_circuit_breaker, get_today_realized_pnl, close_all_open_trades,
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


def _mt5_badge(profile, mt5_connected):
    """Badge pembeda profil LIVE (tersambung MT5) vs SIM."""
    live = profile.get("live_mode", False)
    if live and mt5_connected:
        return "<span class='at-badge' style='background:rgba(255,75,75,0.15);color:#ff4b4b;border:1px solid #ff4b4b55;'>🔴 LIVE · MT5</span>"
    if live and not mt5_connected:
        return "<span class='at-badge' style='background:rgba(255,215,0,0.15);color:#FFD700;border:1px solid #FFD70055;'>⚠️ LIVE · MT5 OFFLINE</span>"
    return "<span class='at-badge' style='background:rgba(255,255,255,0.05);color:#888;border:1px solid #88888855;'>⚫ SIM</span>"


def _mt5_is_connected():
    """Cek koneksi MT5 dengan aman (tidak error kalau package belum ada)."""
    try:
        from mt5_bridge import is_connected
        return is_connected()
    except Exception:
        return False


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
    mt5_connected = _mt5_is_connected()

    # ── Existing Profiles ──────────────────────────────────
    if profiles:
        st.markdown("<p style='font-family:Orbitron;color:#888;font-size:10px;letter-spacing:1px;'>PROFIL AKTIF</p>", unsafe_allow_html=True)
        for p in profiles:
            is_on = p.get("is_active", True)
            dot   = "🟢" if is_on else "⚫"
            mode_tag = "🔴 LIVE" if p.get("live_mode") else "⚫ SIM"
            with st.expander(f"{dot} **{p['name']}** [{mode_tag}] — ${p['capital']:,.0f} | {len(p.get('pairs',[]))} pairs"):
                st.markdown(_mt5_badge(p, mt5_connected), unsafe_allow_html=True)

                # Sizing summary
                if p.get("use_risk_sizing", True):
                    sizing_txt = f"Risiko {p.get('risk_percent', 1.0)}% modal / trade (lot otomatis)"
                else:
                    sizing_txt = f"Lot tetap: {p['lot_size']}"
                st.caption(f"📐 {sizing_txt}  ·  🛡️ Stop rugi harian {p.get('max_daily_loss_pct',5.0)}% · jeda {p.get('max_loss_streak',4)}× LOSS beruntun")

                c1, c2, c3 = st.columns(3)
                c1.metric("Modal", f"${p['capital']:,.0f}")
                c2.metric("Min Q-Score", f"±{p.get('min_q_score',8)}")
                c3.metric("Max Open", p.get('max_open_trades', 3))

                # Circuit breaker live status
                allowed, cb_reason = check_circuit_breaker(p)
                if not allowed:
                    st.error(cb_reason)
                else:
                    today_pnl = get_today_realized_pnl(p["id"])
                    st.caption(f"✅ Auto-trade aktif · P/L hari ini: ${today_pnl:+,.2f}")

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
                confirm_key = f"confirm_del_{p['id']}"
                if not st.session_state.get(confirm_key):
                    if btn3.button("🗑️ Hapus", key=f"del_{p['id']}"):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    btn3.warning("Yakin hapus?")
                    ca, cb = st.columns(2)
                    if ca.button("✅ Ya, Hapus", key=f"del_yes_{p['id']}", use_container_width=True):
                        delete_profile(p["id"])
                        st.session_state.pop(confirm_key, None)
                        st.toast("Profil & semua trade-nya dihapus", icon="🗑️")
                        st.rerun()
                    if cb.button("❌ Batal", key=f"del_no_{p['id']}", use_container_width=True):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()

        st.divider()

    # ── Create New Profile ─────────────────────────────────
    with st.expander("➕ BUAT PROFIL BARU", expanded=not bool(profiles)):
        name = st.text_input("Nama Profil", placeholder="Contoh: Aggressive 4H", key="at_pname")

        # ── STEP 1: Pilih mode profil ──────────────────────────
        st.markdown("<p style='font-size:11px;color:#00ffcc;font-family:Orbitron;letter-spacing:1px;'>1️⃣ MODE PROFIL</p>", unsafe_allow_html=True)
        mode = st.radio(
            "Mode trading", ["🤖 Internal (Paper Trading)", "🔴 MT5 Live (Order ke Broker)"],
            key="at_mode", label_visibility="collapsed",
            help="Internal = simulasi murni. MT5 Live = order benar-benar dikirim ke broker."
        )
        is_live_mode = mode.startswith("🔴")

        # ── MT5 Live → cek/konek broker dulu ───────────────────
        mt5_ready = True  # internal mode selalu siap
        if is_live_mode:
            mt5_ready = _mt5_is_connected()
            if mt5_ready:
                acc_txt = ""
                try:
                    from mt5_bridge import get_account_info
                    info = get_account_info()
                    if info:
                        acc_txt = f" — Akun #{info['login']} ({info['server']}), Balance {info['balance']:,.2f} {info['currency']}"
                except Exception:
                    pass
                st.success(f"🔴 MT5 TERHUBUNG{acc_txt}. Order profil ini akan dikirim ke broker.")
            else:
                st.warning("⚠️ MT5 belum terhubung. Hubungkan dulu sebelum buat profil Live.")
                if st.button("⚡ Auto-Connect MT5 (terminal yang sedang jalan)", key="at_create_autoconn", use_container_width=True):
                    try:
                        from mt5_bridge import auto_connect
                        with st.spinner("Mencari terminal MT5 aktif..."):
                            ok, msg = auto_connect()
                        if ok:
                            st.success(msg); st.rerun()
                        else:
                            st.error(f"{msg}\n\nBuka & login MT5 terminal, atau connect manual di tab 🔌 BROKER MT5.")
                    except Exception as e:
                        st.error(f"Gagal: {e}")
                st.caption("💡 Atau connect manual lewat tab 🔌 BROKER MT5, lalu kembali ke sini.")

        st.markdown("<p style='font-size:11px;color:#00ffcc;font-family:Orbitron;letter-spacing:1px;margin-top:8px;'>2️⃣ KONFIGURASI TRADING</p>", unsafe_allow_html=True)
        cap_label = "Modal Akun (USD)" if is_live_mode else "Modal Simulasi (USD)"
        capital = st.number_input(cap_label, min_value=100.0, max_value=1_000_000.0,
                                   value=1000.0, step=100.0, key="at_cap",
                                   help="Dipakai untuk hitung lot berbasis risiko & batas rugi harian.")

        # ── Position sizing mode ───────────────────────────────
        use_risk_sizing = st.toggle(
            "📐 Lot otomatis berbasis risiko (rekomendasi)", value=True, key="at_userisk",
            help="Lot dihitung dari % modal yang dirisiko ÷ jarak SL. Risiko $ tiap trade jadi konsisten."
        )
        if use_risk_sizing:
            risk_percent = st.slider("Risiko per Trade (% modal)", 0.25, 5.0, 1.0, 0.25, key="at_riskpct",
                                     help="Contoh: modal $1000, risiko 1% = rugi maks ~$10 jika SL kena.")
            lot_size = 0.01  # fallback saja; lot asli dihitung dinamis saat entry
            st.caption(f"💡 Lot dihitung otomatis tiap entry. Risiko ≈ **${capital * risk_percent / 100:,.2f}** per trade.")
        else:
            risk_percent = 1.0
            lot_label = st.selectbox("Ukuran Lot (tetap)", list(LOT_PRESETS.keys()), key="at_lot_sel")
            if LOT_PRESETS[lot_label] is None:
                lot_size = st.number_input("Lot Custom", min_value=0.0001, max_value=100.0,
                                            value=0.05, step=0.001, format="%.4f", key="at_lot_custom")
            else:
                lot_size = LOT_PRESETS[lot_label]
                st.info(f"💡 Lot size tetap: **{lot_size}** lot")

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

        # ── Circuit breaker / proteksi akun ────────────────────
        st.markdown("<p style='font-size:11px;color:#FFD700;font-family:Orbitron;letter-spacing:1px;margin-top:6px;'>🛡️ PROTEKSI AKUN</p>", unsafe_allow_html=True)
        col_c, col_d = st.columns(2)
        with col_c:
            max_daily_loss = st.number_input("Stop kalau rugi harian ≥ (% modal)", 1.0, 50.0, 5.0, 0.5,
                                             key="at_maxdd",
                                             help="Auto-trade berhenti hari itu kalau total rugi tembus batas ini.")
        with col_d:
            max_streak = st.slider("Stop setelah LOSS beruntun", 2, 10, 4, key="at_maxstreak",
                                   help="Jeda auto-trade setelah sekian kali kalah berturut-turut.")

        create_label = "🔴 BUAT PROFIL LIVE (MT5)" if is_live_mode else "🤖 BUAT PROFIL INTERNAL"
        if is_live_mode and not mt5_ready:
            st.button(create_label, use_container_width=True, disabled=True, key="at_create_disabled",
                      help="Hubungkan MT5 dulu untuk membuat profil Live.")
        elif st.button(create_label, use_container_width=True, type="primary", key="at_create"):
            if not name.strip():
                st.error("Nama profil tidak boleh kosong!")
            elif not selected_pairs:
                st.error("Pilih minimal 1 pair!")
            else:
                create_profile(
                    owner=username, name=name.strip(), capital=capital,
                    lot_size=lot_size, pairs=selected_pairs,
                    min_q_score=min_q, max_open_trades=max_open,
                    sl_atr_mult=sl_mult, tp_atr_mult=tp_mult,
                    use_risk_sizing=use_risk_sizing, risk_percent=risk_percent,
                    max_daily_loss_pct=max_daily_loss, max_loss_streak=max_streak,
                    live_mode=is_live_mode,
                )
                mode_txt = "LIVE (MT5)" if is_live_mode else "Internal"
                st.success(f"✅ Profil '{name}' [{mode_txt}] berhasil dibuat!")
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

    # ── Status bar: mode + MT5 + circuit breaker ──────────────
    mt5_connected = _mt5_is_connected()
    st.markdown(_mt5_badge(sel_profile, mt5_connected), unsafe_allow_html=True)
    allowed, cb_reason = check_circuit_breaker(sel_profile)
    today_pnl = get_today_realized_pnl(sel_id)
    if not allowed:
        st.error(cb_reason)
    else:
        st.caption(f"✅ Auto-trade aktif · P/L realisasi hari ini: **${today_pnl:+,.2f}**")

    # Quick action buttons
    bc1, bc2, bc3, bc4 = st.columns(4)
    if bc1.button("🔄 Scan & Place", use_container_width=True, key="at_mon_scan"):
        with st.spinner("Scanning market untuk semua pair..."):
            res = run_auto_scan(sel_profile)
        if res.get("halted"):
            st.warning(res["details"][0] if res["details"] else "Auto-trade dijeda circuit breaker.")
        else:
            st.success(f"✅ {res['new_orders']} order baru | {res['skipped']} skip | {res['errors']} error")
        with st.expander("Detail Scan"):
            for d in res["details"]:
                st.markdown(f"<p style='font-size:11px;color:#aaa;'>{d}</p>", unsafe_allow_html=True)
        st.rerun()

    if bc2.button("⚡ Sync SL/TP", use_container_width=True, key="at_mon_sync"):
        with st.spinner("Checking SL/TP..."):
            n = sync_sim_trades(sel_id)
        st.success(f"✅ {n} trade ditutup/disinkron")
        st.rerun()

    if bc3.button("🔃 Refresh", use_container_width=True, key="at_mon_refresh"):
        st.rerun()

    # Close All — with 2-step confirmation
    confirm_all_key = f"confirm_closeall_{sel_id}"
    if not st.session_state.get(confirm_all_key):
        if bc4.button("🛑 Close All", use_container_width=True, key="at_mon_closeall"):
            st.session_state[confirm_all_key] = True
            st.rerun()
    else:
        if bc4.button("⚠️ Yakin?", use_container_width=True, key="at_mon_closeall_yes"):
            with st.spinner("Menutup semua posisi..."):
                n = close_all_open_trades(sel_id)
            st.session_state.pop(confirm_all_key, None)
            st.toast(f"{n} posisi ditutup", icon="🛑")
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
        # Ambil profit aktual posisi MT5 sekali (untuk trade live) → akurat, bukan estimasi
        mt5_pos_map = {}
        if mt5_connected:
            try:
                from mt5_bridge import get_open_positions
                mt5_pos_map = {p["ticket"]: p for p in get_open_positions()}
            except Exception:
                mt5_pos_map = {}

        for t in open_trades:
            ticker = t["ticker"]
            # Trade live & posisi ada di MT5 → pakai profit + harga aktual broker
            mt5_pos = None
            if t.get("is_live") and t.get("mt5_ticket"):
                try:
                    mt5_pos = mt5_pos_map.get(int(t["mt5_ticket"]))
                except (TypeError, ValueError):
                    mt5_pos = None

            if mt5_pos:
                cur_price  = mt5_pos["current"]
                unreal_pnl = mt5_pos["profit"]
                pnl_src    = "Unrealized PnL · MT5 LIVE"
            else:
                # Sim / fallback: estimasi dari harga yfinance
                try:
                    df_live = fetch_forex_data(ticker, "1d", "15m")
                    cur_price = float(df_live.iloc[-1]["Close"]) if df_live is not None and not df_live.empty else t["entry_price"]
                except Exception:
                    cur_price = t["entry_price"]
                unreal_pnl = get_unrealized_pnl(t, cur_price)
                pnl_src    = "Unrealized PnL · estimasi"

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
                            <p style='font-size:10px;color:#555;margin:0;'>{pnl_src}</p>
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
# TAB 4 — MT5 BROKER CONNECTION
# ============================================================
def _tab_broker():
    from mt5_bridge import (
        is_mt5_installed, is_connected, connect, disconnect, auto_connect,
        get_account_info, get_open_positions, get_trade_history,
        load_mt5_config, save_mt5_config, DEFAULT_SYMBOL_MAP,
    )
    from auto_trader import get_profiles, update_profile

    st.markdown("<p style='font-family:Orbitron;color:#00ffcc;font-size:11px;letter-spacing:2px;margin-bottom:16px;'>🔌 KONEKSI BROKER MT5</p>", unsafe_allow_html=True)

    # ── Install check ─────────────────────────────────────────
    if not is_mt5_installed():
        st.error("Package **MetaTrader5** belum terinstall.")
        st.code("pip install MetaTrader5", language="bash")
        st.info("Setelah install, restart Streamlit app.")
        return

    cfg = load_mt5_config()
    connected = is_connected()

    # ── Auto-connect: nempel ke terminal MT5 yang sudah jalan ─
    if not connected:
        if st.button("⚡ Auto-Connect (terminal MT5 yang sedang jalan)", use_container_width=True, key="mt5_autoconn"):
            with st.spinner("Mencari terminal MT5 aktif..."):
                ok, msg = auto_connect()
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.warning(f"{msg}\n\nBuka & login MT5 terminal dulu, atau isi kredensial manual di bawah.")
        st.caption("💡 Kalau terminal MT5 sudah terbuka & login, tombol ini langsung nyambung tanpa perlu password.")

    # ── Connection status banner ──────────────────────────────
    if connected:
        info = get_account_info()
        if info:
            equity_color = "#00ffcc" if info["profit"] >= 0 else "#ff4b4b"
            profit_sign = "+" if info["profit"] >= 0 else ""
            st.markdown(f"""
                <div class='at-card' style='border-left:3px solid #00ffcc;margin-bottom:16px;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;'>
                        <div>
                            <p style='font-family:Orbitron;color:#00ffcc;font-size:13px;margin:0;letter-spacing:2px;'>🟢 TERHUBUNG</p>
                            <p style='color:#888;font-size:11px;margin:4px 0 0;'>#{info['login']} — {info['name']} @ {info['server']}</p>
                        </div>
                        <div style='display:flex;gap:24px;flex-wrap:wrap;'>
                            <div style='text-align:center;'>
                                <p class='at-header'>BALANCE</p>
                                <p style='font-family:JetBrains Mono;color:#eee;font-size:14px;margin:0;'>{info['balance']:,.2f} <span style='font-size:10px;color:#555;'>{info['currency']}</span></p>
                            </div>
                            <div style='text-align:center;'>
                                <p class='at-header'>EQUITY</p>
                                <p style='font-family:JetBrains Mono;color:#eee;font-size:14px;margin:0;'>{info['equity']:,.2f}</p>
                            </div>
                            <div style='text-align:center;'>
                                <p class='at-header'>FREE MARGIN</p>
                                <p style='font-family:JetBrains Mono;color:#eee;font-size:14px;margin:0;'>{info['free_margin']:,.2f}</p>
                            </div>
                            <div style='text-align:center;'>
                                <p class='at-header'>FLOATING P&L</p>
                                <p style='font-family:JetBrains Mono;color:{equity_color};font-size:14px;margin:0;font-weight:700;'>{profit_sign}{info['profit']:,.2f}</p>
                            </div>
                            <div style='text-align:center;'>
                                <p class='at-header'>LEVERAGE</p>
                                <p style='font-family:JetBrains Mono;color:#aaa;font-size:14px;margin:0;'>1:{info['leverage']}</p>
                            </div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        if st.button("🔌 Disconnect", key="mt5_disconnect"):
            disconnect()
            st.toast("MT5 disconnected", icon="🔌")
            st.rerun()
    else:
        st.markdown("""
            <div class='at-card' style='border-left:3px solid #ff4b4b;margin-bottom:16px;'>
                <p style='font-family:Orbitron;color:#ff4b4b;font-size:12px;margin:0;letter-spacing:2px;'>🔴 TIDAK TERHUBUNG</p>
                <p style='color:#555;font-size:11px;margin:4px 0 0;'>Masukkan kredensial broker dan klik Connect</p>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Login form ────────────────────────────────────────────
    with st.expander("🔑 Login Broker", expanded=not connected):
        lc1, lc2 = st.columns(2)
        with lc1:
            login_num = st.text_input("Account Number", value=str(cfg.get("login", "")), key="mt5_login")
            server = st.text_input("Server Name", value=cfg.get("server", ""), key="mt5_server",
                                   placeholder="Contoh: BrokerName-Live, ICMarkets-Live01")
        with lc2:
            password = st.text_input("Password", type="password", key="mt5_password")
            suffix = st.text_input("Symbol Suffix (opsional)", value=cfg.get("symbol_suffix", ""),
                                   key="mt5_suffix", placeholder="Contoh: m (untuk EURUSDm)")

        st.caption("⚠️ Password tidak disimpan ke disk. Perlu diisi ulang setiap restart app.")

        if st.button("🔌 Connect ke MT5", use_container_width=True, type="primary", key="mt5_connect"):
            if not login_num or not password or not server:
                st.error("Login number, password, dan server name wajib diisi.")
            else:
                with st.spinner("Menghubungkan ke MT5..."):
                    ok, msg = connect(int(login_num), password, server)
                if ok:
                    # Save config (tanpa password)
                    cfg["login"] = int(login_num)
                    cfg["server"] = server
                    cfg["symbol_suffix"] = suffix
                    save_mt5_config(cfg)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # ── Live Mode toggle per profil ───────────────────────────
    st.markdown("<p style='font-family:Orbitron;color:#FFD700;font-size:10px;letter-spacing:2px;margin-top:8px;'>⚡ LIVE MODE PER PROFIL</p>", unsafe_allow_html=True)

    username = st.session_state.get("username", "")
    profiles = get_profiles(username)

    if not profiles:
        st.info("Belum ada profil auto trader. Buat profil dulu di tab Profil Manager.")
    else:
        for p in profiles:
            live = p.get("live_mode", False)
            live_color = "#ff4b4b" if live else "#555"
            live_label = "🔴 LIVE" if live else "⚫ SIM"

            pc1, pc2, pc3 = st.columns([3, 1, 1])
            with pc1:
                st.markdown(f"""
                    <div style='padding:10px 14px;background:rgba(255,255,255,0.02);border:1px solid #1a1a1a;border-radius:8px;'>
                        <span style='font-family:Orbitron;color:#eee;font-size:12px;'>{p['name']}</span>
                        <span style='font-family:Orbitron;font-size:9px;color:{live_color};margin-left:10px;
                                     background:{live_color}22;padding:2px 8px;border-radius:10px;'>{live_label}</span>
                        <p style='font-size:10px;color:#444;margin:2px 0 0;'>{p['lot_size']} lot · {len(p.get("pairs",[]))} pairs</p>
                    </div>
                """, unsafe_allow_html=True)
            with pc2:
                if not connected and not live:
                    st.button("Toggle Live", key=f"live_tog_{p['id']}", disabled=True, help="Connect ke MT5 dulu")
                else:
                    if st.button("🔴 LIVE" if not live else "⚫ SIM", key=f"live_tog_{p['id']}", use_container_width=True):
                        if not live and not connected:
                            st.error("MT5 harus terhubung untuk aktifkan Live Mode.")
                        else:
                            update_profile(p["id"], live_mode=not live)
                            new_state = "LIVE" if not live else "SIM"
                            st.toast(f"Profil '{p['name']}' sekarang mode {new_state}", icon="⚡")
                            st.rerun()

        if any(p.get("live_mode") for p in profiles):
            st.warning(
                "⚠️ **Live Mode aktif** — setiap sinyal EXECUTE akan mengirim order ke broker secara nyata. "
                "Pastikan lot size, SL, dan TP sudah sesuai risk management kamu.",
                icon="🚨"
            )

    st.divider()

    # ── Open Positions dari MT5 ───────────────────────────────
    from mt5_bridge import MT5_MAGIC
    st.markdown(f"<p style='font-family:Orbitron;color:#888;font-size:10px;letter-spacing:2px;'>📡 POSISI OPEN DI BROKER (Magic #{MT5_MAGIC})</p>", unsafe_allow_html=True)

    if connected:
        col_ref, col_hist = st.columns(2)
        with col_ref:
            if st.button("🔄 Refresh Posisi", use_container_width=True, key="mt5_refresh"):
                st.rerun()
        with col_hist:
            show_hist = st.button("📋 Riwayat 7 Hari", use_container_width=True, key="mt5_hist")

        positions = get_open_positions()

        if not positions:
            st.markdown("<div class='at-card' style='text-align:center;padding:20px;'><p style='color:#555;font-size:12px;'>Tidak ada posisi open dari bot ini</p></div>", unsafe_allow_html=True)
        else:
            for pos in positions:
                pnl_col = "#00ffcc" if pos["profit"] >= 0 else "#ff4b4b"
                pnl_sign = "+" if pos["profit"] >= 0 else ""
                dir_color = "#00ffcc" if pos["direction"] == "BUY" else "#ff4b4b"

                st.markdown(f"""
                    <div class='at-card' style='border-left:3px solid {pnl_col};'>
                        <div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;'>
                            <div>
                                <span style='font-family:Orbitron;color:#eee;font-size:14px;font-weight:900;'>{pos['symbol']}</span>
                                <span style='font-family:Orbitron;font-size:9px;color:{dir_color};margin-left:8px;background:{dir_color}22;padding:2px 8px;border-radius:10px;'>▲ {pos['direction']}</span>
                                <span style='font-size:10px;color:#555;margin-left:8px;'>Ticket #{pos['ticket']}</span>
                            </div>
                            <p style='font-family:JetBrains Mono;font-size:18px;color:{pnl_col};margin:0;font-weight:700;'>{pnl_sign}${pos['profit']:.2f}</p>
                        </div>
                        <div style='display:flex;gap:20px;margin-top:10px;font-size:11px;color:#888;flex-wrap:wrap;'>
                            <span>Entry: <b style='color:#eee;'>{pos['open_price']}</b></span>
                            <span>Current: <b style='color:#FFD700;'>{pos['current']}</b></span>
                            <span>SL: <b style='color:#ff4b4b;'>{pos['sl'] or '—'}</b></span>
                            <span>TP: <b style='color:#00ffcc;'>{pos['tp'] or '—'}</b></span>
                            <span>Lot: <b style='color:#aaa;'>{pos['volume']}</b></span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                if st.button(f"❌ Close #{pos['ticket']}", key=f"mt5_close_{pos['ticket']}"):
                    from mt5_bridge import close_position
                    ok, msg = close_position(pos["ticket"])
                    if ok:
                        st.toast(msg, icon="✅")
                    else:
                        st.error(msg)
                    st.rerun()

        if show_hist:
            history = get_trade_history(days=7)
            if history:
                st.markdown("<p style='font-family:Orbitron;color:#888;font-size:10px;letter-spacing:2px;margin-top:12px;'>RIWAYAT TRADE (7 HARI)</p>", unsafe_allow_html=True)
                for h in history:
                    pnl_col = "#00ffcc" if h["profit"] >= 0 else "#ff4b4b"
                    sign = "+" if h["profit"] >= 0 else ""
                    from datetime import datetime
                    t_str = datetime.fromtimestamp(h["time"]).strftime("%m/%d %H:%M")
                    st.markdown(f"""
                        <div class='at-row'>
                            <span style='font-family:Orbitron;font-size:11px;color:#eee;'>{h['symbol']} {h['direction']}</span>
                            <span style='font-size:10px;color:#555;'>{h['volume']} lot @ {h['price']} · {t_str}</span>
                            <span style='font-family:JetBrains Mono;color:{pnl_col};font-weight:700;'>{sign}${h['profit']:.2f}</span>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Belum ada history trade dari bot dalam 7 hari terakhir.")
    else:
        st.info("Connect ke MT5 dulu untuk melihat posisi broker.")

    # ── Symbol mapping editor ─────────────────────────────────
    with st.expander("🗺️ Edit Symbol Mapping (jika broker pakai nama berbeda)"):
        st.markdown("<p style='font-size:11px;color:#888;'>Beberapa broker pakai nama berbeda, misal XAUUSD → GOLDm, atau USOIL → CRUDE.</p>", unsafe_allow_html=True)
        st.caption("Format: yfinance_ticker = MT5_symbol_name")

        symbol_map = cfg.get("symbol_map", DEFAULT_SYMBOL_MAP)
        updated_map = {}
        pairs_to_show = list(DEFAULT_SYMBOL_MAP.keys())

        col_a, col_b = st.columns(2)
        for i, yticker in enumerate(pairs_to_show):
            col = col_a if i % 2 == 0 else col_b
            with col:
                val = st.text_input(
                    yticker,
                    value=symbol_map.get(yticker, DEFAULT_SYMBOL_MAP[yticker]),
                    key=f"symmap_{yticker}"
                )
                updated_map[yticker] = val.strip()

        if st.button("💾 Simpan Symbol Map", use_container_width=True, key="mt5_save_map"):
            cfg["symbol_map"] = updated_map
            save_mt5_config(cfg)
            st.success("Symbol mapping disimpan!")
            st.rerun()


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

    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ PROFIL MANAGER", "📡 MONITOR LIVE", "📊 STATISTIK", "🔌 BROKER MT5"])

    with tab1:
        _tab_profiles(username)
    with tab2:
        _tab_monitor(username)
    with tab3:
        _tab_stats(username)
    with tab4:
        _tab_broker()
