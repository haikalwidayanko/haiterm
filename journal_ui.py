import streamlit as st
import pandas as pd
from journal import (
    get_journal_entries, get_journal_stats, close_trade, delete_trade,
    follow_signal, skip_signal, sync_open_trades
)


def render_journal_page():
    """Full Trade Journal page — simulation mode with auto-sync."""

    st.markdown("""
        <div style="padding:20px 0 10px;">
            <p style="font-family:'Orbitron';font-size:20px;color:#FFD700;letter-spacing:4px;margin:0;">
                📓 SIMULASI TRADING
            </p>
            <p style="color:#444;font-size:11px;margin:4px 0 0;">Paper Trade · SL/TP otomatis tersinkron dengan data historis</p>
        </div>
    """, unsafe_allow_html=True)

    # Auto-sync open trades on page load
    if "journal_synced" not in st.session_state:
        with st.spinner("🔄 Sinkronisasi trade terbuka dengan data pasar..."):
            synced = sync_open_trades()
        st.session_state.journal_synced = True
        if synced > 0:
            st.success(f"✅ {synced} trade otomatis ditutup berdasarkan data historis (SL/TP tercapai)")
            st.rerun()

    stats = get_journal_stats()

    # ── PERFORMANCE DASHBOARD ────────────────────────────────
    _render_stats_cards(stats)

    # ── EQUITY CURVE ─────────────────────────────────────────
    if stats["pnl_curve"]:
        st.markdown("<br><p style='font-family:Orbitron;font-size:10px;color:#444;letter-spacing:2px;'>EQUITY CURVE (KUMULATIF PIPS)</p>", unsafe_allow_html=True)
        df_pnl = pd.DataFrame(stats["pnl_curve"])
        st.line_chart(df_pnl.set_index("trade")["pnl"], color="#00ffcc")

    st.divider()

    # ── PENDING SIGNALS (User Decision) ──────────────────────
    _render_pending_signals()

    # ── TRADE LOG ────────────────────────────────────────────
    _render_trade_log()


def _render_stats_cards(stats):
    """Render the performance dashboard cards."""
    wr = stats["win_rate"]
    wr_color = "#00ffcc" if wr >= 55 else ("#FFD700" if wr >= 40 else "#ff4b4b")
    pnl_color = "#00ffcc" if stats["net_pips"] >= 0 else "#ff4b4b"
    streak_color = "#00ffcc" if stats["streak_type"] == "WIN" else ("#ff4b4b" if stats["streak_type"] == "LOSS" else "#888")

    def _card(label, value, sub="", color="#eee"):
        return f"""<div style="background:rgba(255,255,255,0.03);padding:16px;border-radius:12px;
                              border:1px solid #222;text-align:center;min-height:100px;">
            <p style="font-size:9px;color:#555;margin:0;font-family:'Orbitron';letter-spacing:1px;">{label}</p>
            <h2 style="margin:8px 0 4px;color:{color};font-family:'JetBrains Mono';font-size:28px;">{value}</h2>
            <p style="font-size:9px;color:#666;margin:0;">{sub}</p>
        </div>"""

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_card("TOTAL SINYAL", stats["total_signals"],
                          f"{stats['open_trades']} open · {stats['followed']} diikuti · {stats['skipped']} dilewat"), unsafe_allow_html=True)
    with c2:
        st.markdown(_card("WIN RATE", f"{wr:.1f}%",
                          f"{stats['wins']}W / {stats['losses']}L / {stats['be']}BE", wr_color), unsafe_allow_html=True)
    with c3:
        st.markdown(_card("NET P&L", f"{stats['net_pips']:+,.1f}",
                          "pips (trade selesai)", pnl_color), unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown(_card("RATA-RATA CONFIDENCE", f"{stats['avg_confidence']:.0f}%",
                          "semua sinyal"), unsafe_allow_html=True)
    with c5:
        best = stats.get("best_trade")
        best_txt = f"+{best['pips_result']:.1f}p" if best and best.get("pips_result") else "—"
        best_pair = best.get("pair_name", "") if best else ""
        st.markdown(_card("TRADE TERBAIK", best_txt, best_pair, "#00ffcc"), unsafe_allow_html=True)
    with c6:
        st.markdown(_card("STREAK", f"{stats['current_streak']}",
                          stats["streak_type"], streak_color), unsafe_allow_html=True)


def _render_pending_signals():
    """Render PENDING signals that need user decision."""
    from journal import get_journal_entries
    pending = get_journal_entries(limit=20, filter_status="PENDING")

    st.markdown("""
        <p style="font-family:'Orbitron';font-size:10px;color:#FFD700;letter-spacing:2px;margin-bottom:12px;">
            ⏳ SINYAL MENUNGGU KEPUTUSAN
        </p>
    """, unsafe_allow_html=True)

    if not pending:
        st.info("Belum ada sinyal AI baru. Saat AI mendeteksi EXECUTE BUY/SELL, sinyal akan muncul di sini untuk Anda setujui.")
        st.divider()
        return

    for t in pending:
        dec_color = "#00ffcc" if "BUY" in t.get("decision", "") else "#ff4b4b"
        entry_p = t.get("entry_price", 0)
        fmt = (lambda v: f"{v:,.3f}" if v else "—") if entry_p > 10 else (lambda v: f"{v:,.5f}" if v else "—")

        st.markdown(f"""
            <div style="background:rgba(255,215,0,0.06);border:1px solid #FFD70044;border-left:4px solid #FFD700;
                        border-radius:10px;padding:14px 16px;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                    <div>
                        <span style="font-family:'Orbitron';font-size:16px;color:#eee;font-weight:900;">
                            {t.get('pair_name', '')}
                        </span>
                        <span style="font-family:'Orbitron';font-size:10px;color:{dec_color};margin-left:8px;
                                     background:{dec_color}15;padding:2px 8px;border-radius:4px;">
                            {t.get('decision', '')}
                        </span>
                        <span style="font-size:10px;color:#555;margin-left:8px;">{t.get('timestamp', '')}</span>
                    </div>
                    <span style="font-family:'Orbitron';font-size:10px;color:#FFD700;">⏳ MENUNGGU</span>
                </div>
                <div style="display:flex;gap:16px;margin-top:8px;font-size:11px;color:#888;flex-wrap:wrap;">
                    <span>Entry: <b style="color:#ccc;">{fmt(entry_p)}</b></span>
                    <span>SL: <b style="color:#ff4b4b;">{fmt(t.get('sl'))}</b></span>
                    <span>TP1: <b style="color:#00ffcc;">{fmt(t.get('tp1'))}</b></span>
                    <span>TP2: <b style="color:#00ffcc;">{fmt(t.get('tp2'))}</b></span>
                    <span>Q: <b style="color:#ccc;">{t.get('q_score', 0):+}</b></span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button(f"✅ Ikut Rekomendasi", key=f"follow_{t['id']}", use_container_width=True):
                follow_signal(t["id"])
                st.toast(f"Trade {t.get('pair_name', '')} OPEN — simulasi dimulai!", icon="✅")
                st.rerun()
        with bc2:
            if st.button(f"⏭️ Tidak Ikut", key=f"skip_{t['id']}", use_container_width=True):
                skip_signal(t["id"])
                st.toast(f"Sinyal {t.get('pair_name', '')} dilewati", icon="⏭️")
                st.rerun()

    st.divider()


def _render_trade_log():
    """Render trade log table with filters."""
    st.markdown("<p style='font-family:Orbitron;font-size:10px;color:#444;letter-spacing:2px;'>RIWAYAT TRADE</p>", unsafe_allow_html=True)

    # Filters
    fc1, fc2 = st.columns(2)
    with fc1:
        filter_status = st.selectbox("Filter Status", ["ALL", "OPEN", "WIN", "LOSS", "BE", "SKIPPED"], key="j_filter_status")
    with fc2:
        # Manual sync button
        if st.button("🔄 Sinkronkan Sekarang", use_container_width=True):
            st.session_state.pop("journal_synced", None)
            with st.spinner("Sinkronisasi..."):
                synced = sync_open_trades()
            if synced > 0:
                st.success(f"✅ {synced} trade di-update!")
            else:
                st.info("Semua trade masih berjalan, belum ada SL/TP tercapai.")
            st.rerun()

    entries = get_journal_entries(limit=50, filter_status=filter_status if filter_status != "ALL" else None)

    # Exclude PENDING from main log (they have their own section)
    entries = [e for e in entries if e.get("status") != "PENDING"]

    if not entries:
        st.info("Belum ada trade tercatat. Sinyal akan otomatis masuk saat AI mengeluarkan rekomendasi EXECUTE.")
        return

    for t in entries:
        _render_trade_card(t)


def _render_trade_card(t):
    """Render a single trade entry card."""
    status = t.get("status", "OPEN")
    decision = t.get("decision", "")
    reason = t.get("close_reason", "")

    status_config = {
        "WIN":     ("#00ffcc", "rgba(0,255,204,0.04)", f"✅ WIN ({reason})" if reason else "✅ WIN"),
        "LOSS":    ("#ff4b4b", "rgba(255,75,75,0.04)", f"❌ LOSS ({reason})" if reason else "❌ LOSS"),
        "BE":      ("#FFD700", "rgba(255,215,0,0.04)", "⚖️ BREAKEVEN"),
        "OPEN":    ("#4ECDC4", "rgba(78,205,196,0.04)", "🟢 OPEN — Berjalan"),
        "SKIPPED": ("#555",    "rgba(255,255,255,0.02)", "⏭️ DILEWATI"),
    }
    border_color, bg, status_badge = status_config.get(status, ("#555", "rgba(255,255,255,0.02)", status))

    dec_color = "#00ffcc" if "BUY" in decision else "#ff4b4b"
    pips_txt = f"{t.get('pips_result', 0):+,.1f} pips" if t.get("pips_result") is not None else "—"
    pips_color = "#00ffcc" if (t.get("pips_result") or 0) >= 0 else "#ff4b4b"
    pa_txt = t.get("pa_signal", "NONE").replace("_", " ")

    # Price formatter
    entry_p = t.get("entry_price", 0)
    if entry_p > 10:
        fmt = lambda v: f"{v:,.3f}" if v else "—"
    else:
        fmt = lambda v: f"{v:,.5f}" if v else "—"

    closed_info = ""
    if t.get("closed_at"):
        closed_info = f"<span style='font-size:9px;color:#666;margin-left:8px;'>Ditutup: {t['closed_at']}</span>"

    st.markdown(f"""
        <div style="background:{bg};border:1px solid #222;border-left:4px solid {border_color};
                    border-radius:10px;padding:14px 16px;margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div>
                    <span style="font-family:'Orbitron';font-size:16px;color:#eee;font-weight:900;">
                        {t.get('pair_name', t.get('ticker', ''))}
                    </span>
                    <span style="font-family:'Orbitron';font-size:10px;color:{dec_color};margin-left:8px;
                                 background:{dec_color}15;padding:2px 8px;border-radius:4px;">
                        {decision}
                    </span>
                    <span style="font-size:10px;color:#555;margin-left:8px;">{t.get('timestamp', '')}</span>
                </div>
                <div style="text-align:right;">
                    <span style="font-family:'Orbitron';font-size:11px;color:{border_color};font-weight:700;">
                        {status_badge}
                    </span>
                    <span style="font-family:'JetBrains Mono';font-size:13px;color:{pips_color};margin-left:10px;">
                        {pips_txt}
                    </span>
                </div>
            </div>
            <div style="display:flex;gap:16px;margin-top:10px;font-size:11px;color:#888;flex-wrap:wrap;">
                <span>Entry: <b style="color:#ccc;">{fmt(entry_p)}</b></span>
                <span>SL: <b style="color:#ff4b4b;">{fmt(t.get('sl'))}</b></span>
                <span>TP1: <b style="color:#a3ffeb;">{fmt(t.get('tp1'))}</b></span>
                <span>TP2: <b style="color:#00ffcc;">{fmt(t.get('tp2'))}</b></span>
                <span>Q: <b style="color:#ccc;">{t.get('q_score', 0):+}</b></span>
                <span>Conf: <b style="color:#ccc;">{t.get('confidence', 0)}%</b></span>
                {closed_info}
            </div>
            {f'<p style="font-size:10px;color:#666;margin:6px 0 0;font-style:italic;">📝 {t.get("notes")}</p>' if t.get("notes") else ""}
        </div>
    """, unsafe_allow_html=True)

    # Manual close controls for OPEN trades
    if status == "OPEN":
        with st.expander(f"📝 Tutup Manual — {t['id']}", expanded=False):
            with st.form(f"close_{t['id']}"):
                rc1, rc2, rc3 = st.columns(3)
                with rc1:
                    result = st.selectbox("Hasil", ["WIN", "LOSS", "BE"], key=f"res_{t['id']}")
                with rc2:
                    exit_price = st.number_input("Harga Keluar", value=0.0, format="%.5f", key=f"exit_{t['id']}")
                with rc3:
                    pips = st.number_input("Pips +/-", value=0.0, step=0.1, key=f"pips_{t['id']}")
                notes = st.text_input("Catatan (opsional)", key=f"notes_{t['id']}")

                sc1, sc2 = st.columns(2)
                with sc1:
                    if st.form_submit_button("🏁 Selesaikan Trade", use_container_width=True):
                        from journal import close_trade
                        close_trade(t['id'], result, exit_price, pips, notes)
                        st.toast(f"Trade {t['id']} ditutup dengan hasil {result}", icon="🏁")
                        st.rerun()
                with sc2:
                    if st.form_submit_button("🗑️ Hapus", use_container_width=True):
                        delete_trade(t["id"])
                        st.toast(f"Trade {t['id']} dihapus", icon="🗑️")
                        st.rerun()
