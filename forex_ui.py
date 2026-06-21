import streamlit as st
from data_provider import get_forex_list, fetch_forex_data, get_market_sentiment, fetch_macro_data, FOREX_PAIRS, get_mtf_scores
from engine import hitung_indikator_lengkap, get_detailed_scores_v12, calculate_fibonacci_levels, deteksi_smc_v2
from ai_hub import generate_ai_judgment
from auth import has_pair_access


def render_forex_scanner(tf="1h", category="Forex"):
    """
    Renders scanner grid.
    """

    macro      = fetch_macro_data()
    raw_list = get_forex_list()
    
    # Filter by user access
    username = st.session_state.get("username", "")
    raw_list = [t for t in raw_list if has_pair_access(username, t)]
    
    # Filter by category. Forex now includes merged Metals (Gold/Silver) and Energy (Oil).
    if category == "Crypto":
        forex_list = [t for t in raw_list if FOREX_PAIRS.get(t, {}).get('group') == "Crypto"]
    else:
        forex_list = [t for t in raw_list if FOREX_PAIRS.get(t, {}).get('group') in ("Major", "Minor", "Metals", "Energy")]

    results = []
    prog = st.progress(0, text="Scanning forex markets...")

    for i, ticker in enumerate(forex_list):
        info = FOREX_PAIRS.get(ticker, {})
        try:
            df_raw = fetch_forex_data(ticker, period="30d", interval=tf)
            if df_raw is None or df_raw.empty:
                results.append({"ticker": ticker, "info": info, "error": True})
                continue

            df       = hitung_indikator_lengkap(df_raw)
            si, sd, _ = get_market_sentiment(ticker)
            fib      = calculate_fibonacci_levels(df)

            htf_tf   = "4h" if tf in ("15m", "1h") else ("1d" if tf == "4h" else "1wk")
            df_htf   = fetch_forex_data(ticker, period="60d", interval=htf_tf)
            htf_bias = 0
            if df_htf is not None and not df_htf.empty:
                df_htf   = hitung_indikator_lengkap(df_htf)
                htf_bias = 1 if df_htf.iloc[-1]['Close'] > df_htf.iloc[-1]['EMA50'] else -1

            score_res  = get_detailed_scores_v12(df, macro, si, fib, htf_bias, ticker=ticker)
            smc_zones  = deteksi_smc_v2(df)
            last_close = float(df.iloc[-1]['Close'])
            prev_close = float(df.iloc[-2]['Close'])
            pct        = ((last_close - prev_close) / prev_close) * 100
            last_atr   = float(df.iloc[-1].get('ATR', 0)) if 'ATR' in df.columns else None
            ai         = generate_ai_judgment(score_res, fib, smc_zones, last_close, atr=last_atr, ticker=ticker)
            mtf        = get_mtf_scores(ticker, macro, si)

            if last_close > float(df.iloc[-1].get('EMA200', 0)) and last_close > float(df.iloc[-1].get('EMA50', 0)):
                smc_trend = "Bullish"
            elif last_close < float(df.iloc[-1].get('EMA200', 999999)) and last_close < float(df.iloc[-1].get('EMA50', 999999)):
                smc_trend = "Bearish"
            else:
                smc_trend = "Neutral"

            results.append({
                "ticker": ticker,
                "info":   info,
                "score":  score_res['total'],
                "close":  last_close,
                "pct":    pct,
                "ai":     ai,
                "mtf":    mtf,
                "atr":    last_atr,
                "smc":    smc_trend,
                "error":  False,
            })
        except Exception as e:
            results.append({"ticker": ticker, "info": info, "error": True, "err_msg": str(e)})

        prog.progress((i + 1) / len(forex_list), text=f"Scanning {info.get('name', ticker)}...")

    prog.empty()

    if not results:
        st.info("No assets found for this category.")
        return

    # ── Group by category ────────────────────────────────────
    groups = {}
    for r in results:
        if r.get('error'):
            msg = r.get("err_msg", "Empty DataFrame")
            st.warning(f"Data unavailable for {r.get('ticker')} | Error: {msg}")
            continue
        g = r['info'].get('group', 'Other')
        groups.setdefault(g, []).append(r)

    group_order  = ["Major", "Minor", "Metals", "Energy", "Crypto", "Other"]
    group_labels = {
        "Major": "⚛️ MAJOR PAIRS",
        "Minor": "🔀 MINOR / CROSS",
        "Metals": "🥇 METALS",
        "Energy": "⚡ ENERGY",
        "Crypto": "🪙 CRYPTO",
        "Other": "📁 OTHER"
    }

    for g in group_order:
        rows = groups.get(g, [])
        if not rows:
            continue

        st.markdown(f"""
            <p style='font-family:Orbitron;font-size:9px;color:#555;letter-spacing:3px;
                      margin-top:22px;margin-bottom:10px;border-bottom:1px solid #1a1a1a;padding-bottom:6px;'>
                {group_labels.get(g, g)}
            </p>
        """, unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        for i, r in enumerate(rows):
            col = col_a if i % 2 == 0 else col_b
            with col:
                _render_forex_card(r)


def _render_forex_card(r):
    """Single forex pair card for the scanner grid."""
    if r.get('error'):
        st.markdown(f"""<div style="background:rgba(255,255,255,0.02);border:1px solid #1a1a1a;
                                    border-radius:12px;padding:14px;margin-bottom:10px;">
            <p style="color:#444;font-family:'Orbitron';font-size:10px;">
                {r['info'].get('name', r['ticker'])} — Data Unavailable
            </p>
        </div>""", unsafe_allow_html=True)
        return

    score     = r['score']
    decision  = r['ai']['decision']
    ai_color  = r['ai']['color']
    pct_color = "#00ffcc" if r['pct'] >= 0 else "#ff4b4b"
    pct_sym   = "▲" if r['pct'] >= 0 else "▼"
    score_color = "#00ffcc" if score >= 6 else ("#ff4b4b" if score <= -6 else ("#FFD700" if abs(score) >= 3 else "#555"))

    entry = r['info'].get('name', r['ticker'])
    close = r['close']
    atr   = r.get('atr', 0)
    smc   = r.get('smc', 'Neutral')
    smc_color = "#00ffcc" if smc == "Bullish" else ("#ff4b4b" if smc == "Bearish" else "#FFD700")
    
    # Detect JPY/Commodity pairs for decimal formatting
    if close > 10:
        close_fmt = f"{close:,.3f}"
        atr_fmt   = f"{atr:,.3f}" if atr else "-"
    else:
        close_fmt = f"{close:,.5f}"
        atr_fmt   = f"{atr:,.5f}" if atr else "-"

    mtf = r.get('mtf', {})
    mtf_html = ""
    scores_list = [mtf.get(tf_key, 0) for tf_key in ["15m", "1h", "4h", "1d"]]
    
    for tf_key in ["15m", "1h", "4h", "1d"]:
        s = mtf.get(tf_key, 0)
        c = "#00ffcc" if s >= 4 else ("#ff4b4b" if s <= -4 else "#555")
        sym = f"<b style='color:{c};'>{s:+}</b>" if s != 0 else "<b style='color:#555;'>0</b>"
        mtf_html += f"""<div style="flex:1;background:rgba(255,255,255,0.02);border:1px solid #222;border-radius:4px;text-align:center;padding:6px 0;">
            <span style="font-family:'Orbitron';font-size:9px;color:#888;">{tf_key.upper()}</span><br>
            <span style="font-size:12px;">{sym}</span>
        </div>"""

    # Check alignment for glow
    glow_css = ""
    if all(s >= 4 for s in scores_list):
        glow_css = "box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); border-color: #00ffcc;"
    elif all(s <= -4 for s in scores_list):
        glow_css = "box-shadow: 0 0 15px rgba(255, 75, 75, 0.4); border-color: #ff4b4b;"

    # Retain session_token in URL
    token = st.query_params.get("session_token", "")
    href_url = f"?ticker={r['ticker']}&session_token={token}" if token else f"?ticker={r['ticker']}"

    st.markdown(f"""<a href="{href_url}" target="_self" style="text-decoration:none; display:block;">
<div style="background:rgba(255,255,255,0.03);border:1px solid #222;border-left:4px solid {ai_color};border-radius:8px;padding:16px;margin-bottom:8px;transition:0.2s; {glow_css}">
    <!-- Row 1: Name + Price -->
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <h3 style="color:#eee;margin:0;font-family:'Orbitron';font-size:18px;letter-spacing:1px;font-weight:900;">{entry}</h3>
            <span style="font-size:11px;color:{pct_color};font-weight:600;">{pct_sym} {abs(r['pct']):.2f}%</span>
        </div>
        <div style="text-align:right;">
            <b style="font-family:'JetBrains Mono';font-size:18px;color:#fff;">{close_fmt}</b><br>
            <span style="font-size:10px;color:#888;font-family:'Orbitron';letter-spacing:1px;">{r['info'].get('group','').upper()}</span>
        </div>
    </div>
    <!-- Row 1.5: Info Details -->
    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-bottom:12px;border-bottom:1px solid #222;">
        <div>
            <span style="font-size:9px;color:#666;font-family:'Orbitron';letter-spacing:1px;">DAILY ATR</span><br>
            <span style="font-family:'JetBrains Mono';font-size:12px;color:#ccc;">{atr_fmt}</span>
        </div>
        <div style="text-align:right;">
            <span style="font-size:9px;color:#666;font-family:'Orbitron';letter-spacing:1px;">SMC TREND</span><br>
            <span style="font-family:'Orbitron';font-size:11px;color:{smc_color};letter-spacing:1px;">{smc.upper()}</span>
        </div>
    </div>
    <!-- Row 2: MTF Grid -->
    <div style="margin-top:12px;display:flex;justify-content:space-between;gap:6px;">
        {mtf_html}
    </div>
    <!-- Row 3: AI Verdict Banner -->
    <div style="margin-top:8px;">
        <div style="font-family:'Orbitron';font-size:10px;color:{ai_color};font-weight:700;background:{ai_color}15;padding:6px;border-radius:4px;text-align:center;border:1px solid {ai_color}33;letter-spacing:1px;">
            {decision}
        </div>
    </div>
</div></a>""", unsafe_allow_html=True)
