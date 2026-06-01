from engine import get_detailed_scores_v12, deteksi_price_action, run_backtest, hitung_indikator_lengkap
from data_provider import fetch_forex_data
import traceback

try:
    print("Fetching data...")
    df_raw = fetch_forex_data("EURUSD=X", "30d", "1h")
    df = hitung_indikator_lengkap(df_raw)
    
    print("Testing deteksi_price_action...")
    pa = deteksi_price_action(df)
    print("PA Result:", pa)

    print("Testing get_detailed_scores_v12...")
    res = get_detailed_scores_v12(df, {"dxy_val": 100}, 0, {})
    print("Score:", res["total"])

    from ai_hub import generate_ai_judgment
    print("Testing generate_ai_judgment...")
    ai_res = generate_ai_judgment(res, {}, [], float(df['Close'].iloc[-1]), atr=0.005, ticker="EURUSD=X")
    print("AI Decision:", ai_res['decision'])

    print("Testing run_backtest...")
    bt = run_backtest(df)
    print("Backtest trades:", bt["total_trades"])
except Exception as e:
    print("ERROR:")
    traceback.print_exc()
