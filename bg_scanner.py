import json
import os
import pytz
from datetime import datetime

from data_provider import (
    get_forex_list, fetch_forex_data, fetch_macro_data,
    get_market_sentiment, FOREX_PAIRS, send_telegram_alert,
    get_ticker_display_name, get_market_sessions
)
from engine import (
    hitung_indikator_lengkap, get_detailed_scores_v12,
    calculate_fibonacci_levels, deteksi_smc_v2
)
from ai_hub import generate_ai_judgment
from auth import has_pair_access
from journal import log_signal

SCAN_STATE_FILE = "scan_state.json"
tz_jkt = pytz.timezone("Asia/Jakarta")


def _load_scan_state() -> dict:
    if not os.path.exists(SCAN_STATE_FILE):
        return {"last_alerts": {}, "last_results": [], "last_scan_time": None}
    with open(SCAN_STATE_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return {"last_alerts": {}, "last_results": [], "last_scan_time": None}


def _save_scan_state(data: dict):
    with open(SCAN_STATE_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _should_alert(state, ticker, candle_key):
    """Check if we already alerted for this ticker + candle combo."""
    alerts = state.get("last_alerts", {})
    return alerts.get(ticker) != candle_key


def run_background_scan(username):
    """
    Scan all pairs accessible to the user. 
    For each EXECUTE signal, send Telegram alert + log to journal.
    Returns list of active signals.
    """
    state = _load_scan_state()
    macro = fetch_macro_data()
    raw_list = get_forex_list()
    user_pairs = [t for t in raw_list if has_pair_access(username, t)]

    tf = "4h"
    all_results = []
    signals = []
    sessions, _, m_note, _ = get_market_sessions()

    for ticker in user_pairs:
        try:
            df_raw = fetch_forex_data(ticker, period="30d", interval=tf)
            if df_raw is None or df_raw.empty:
                continue

            df = hitung_indikator_lengkap(df_raw)
            si, sd, _ = get_market_sentiment(ticker)
            fib = calculate_fibonacci_levels(df)

            htf_tf = "1d"
            df_htf = fetch_forex_data(ticker, period="60d", interval=htf_tf)
            htf_bias = 0
            if df_htf is not None and not df_htf.empty:
                df_htf = hitung_indikator_lengkap(df_htf)
                htf_bias = 1 if df_htf.iloc[-1]['Close'] > df_htf.iloc[-1]['EMA50'] else -1

            score_res = get_detailed_scores_v12(df, macro, si, fib, htf_bias)
            smc_zones = deteksi_smc_v2(df)
            last_close = float(df.iloc[-1]['Close'])
            last_atr = float(df.iloc[-1].get('ATR', 0)) if 'ATR' in df.columns else None
            ai = generate_ai_judgment(score_res, fib, smc_zones, last_close, atr=last_atr, ticker=ticker)

            decision = ai.get("decision", "STANDBY")
            pair_name = FOREX_PAIRS.get(ticker, {}).get("name", ticker)
            candle_key = str(df.index[-1])

            prev_close = float(df.iloc[-2]['Close']) if len(df) > 1 else last_close
            price_delta = last_close - prev_close
            pct_delta = (price_delta / prev_close) * 100 if prev_close else 0

            sig_entry = {
                "ticker": ticker,
                "pair_name": pair_name,
                "decision": decision,
                "confidence": ai.get("confidence", 0),
                "q_score": score_res.get("total", 0),
                "pa_signal": ai.get("pa_signal", "NONE"),
                "price": last_close,
                "price_delta": price_delta,
                "pct_delta": pct_delta,
                "color": ai.get("color", "#888"),
            }

            # Store ALL results for heatmap
            all_results.append(sig_entry)

            # Only alert for EXECUTE signals
            if decision in ("EXECUTE BUY", "EXECUTE SELL"):
                signals.append(sig_entry)

                # Check if we should alert (not already alerted for this candle)
                if _should_alert(state, ticker, candle_key):
                    plan = ai.get("plan", {})
                    _send_bg_alert(pair_name, last_close, ai, score_res, plan, m_note)
                    log_signal(
                        ticker=ticker,
                        pair_name=pair_name,
                        decision=decision,
                        confidence=ai.get("confidence", 0),
                        q_score=score_res.get("total", 0),
                        pa_signal=ai.get("pa_signal", "NONE"),
                        plan=plan,
                        price=last_close,
                    )
                    state.setdefault("last_alerts", {})[ticker] = candle_key

        except Exception as e:
            print(f"[BG_SCAN] Error scanning {ticker}: {e}")
            continue

    state["all_results"] = all_results
    state["last_results"] = signals
    state["last_scan_time"] = datetime.now(tz_jkt).strftime("%Y-%m-%d %H:%M WIB")
    _save_scan_state(state)
    return signals


def get_last_scan_results():
    """Get cached results from last background scan."""
    state = _load_scan_state()
    return state.get("last_results", []), state.get("last_scan_time")


def get_all_scan_results():
    """Get ALL pair results (for heatmap)."""
    state = _load_scan_state()
    return state.get("all_results", []), state.get("last_scan_time")


def _send_bg_alert(pair_name, price, ai, score_res, plan, session):
    """Send Telegram alert for a background-detected signal."""
    decision = ai.get("decision", "")
    conf = ai.get("confidence", 0)
    q = score_res.get("total", 0)
    pa = ai.get("pa_signal", "NONE").replace("_", " ")

    entry = plan.get("entry", 0)
    sl = plan.get("sl", 0)
    tp1 = plan.get("tp1", 0)
    tp2 = plan.get("tp2", 0)
    tp3 = plan.get("tp3", 0)
    rr2 = plan.get("rr2", 0)
    sl_pips = plan.get("pips_sl", 0)

    def _fmt(v):
        if v == 0:
            return "—"
        if price > 10:
            return f"{v:,.3f}"
        return f"{v:,.5f}"

    msg = (
        f"🔔 *WIDAYANKO — BG SCANNER ALERT*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Pair: *{pair_name}*\n"
        f"💰 Price: `{price:,.5f}`\n"
        f"🧠 Verdict: *{decision}*\n"
        f"📈 Confidence: {conf}%\n"
        f"⚡ Q-Score: {q:+} / ±15\n"
        f"🕯️ PA: {pa}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 Entry: `{_fmt(entry)}`\n"
        f"🛑 SL: `{_fmt(sl)}` ({sl_pips} pips)\n"
        f"TP1: `{_fmt(tp1)}`\n"
        f"TP2: `{_fmt(tp2)}` ← Target\n"
        f"TP3: `{_fmt(tp3)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📐 R:R: *1 : {rr2:.1f}*\n"
        f"⏰ Session: {session}\n"
        f"🤖 _Auto-detected by BG Scanner_"
    )
    send_telegram_alert(msg)
