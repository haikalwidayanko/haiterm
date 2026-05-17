import traceback
import pytz
from datetime import datetime

from data_provider import fetch_macro_data, fetch_forex_data, check_news_shield, get_market_sentiment, get_market_sessions
from engine import hitung_indikator_lengkap, get_detailed_scores_v12, calculate_fibonacci_levels, deteksi_smc_v2
from ai_hub import generate_ai_judgment

try:
    active_ticker = "EURUSD=X"
    tf = "4h"

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

    htf_tf     = "1d"
    df_htf_raw = fetch_forex_data(active_ticker, "60d", htf_tf)
    df_htf     = hitung_indikator_lengkap(df_htf_raw)
    htf_bias   = 1 if df_htf.iloc[-1]['Close'] > df_htf.iloc[-1]['EMA50'] else -1

    score_res = get_detailed_scores_v12(df, macro, si, fib_levels, htf_bias, sent_exp)
    smc_zones = deteksi_smc_v2(df)
    last_atr  = float(df.iloc[-1].get('ATR', 0)) if 'ATR' in df.columns else None
    
    print("Calling generate_ai_judgment...")
    ai_data   = generate_ai_judgment(score_res, fib_levels, smc_zones, last_close, atr=last_atr)
    
    print("Testing render_forex_scanner...")
    import streamlit as st
    class MockSessionState(dict):
        def __getattr__(self, key): return self.get(key)
        def __setattr__(self, key, value): self[key] = value
    st.session_state = MockSessionState({"username": "admin", "app_view": "scanner"})
    st.query_params = {}
    
    from forex_ui import render_forex_scanner
    render_forex_scanner(tf="4h", category="Forex")
    
    print("Success!")
except Exception as e:
    print("ERROR CAUGHT:")
    traceback.print_exc()
