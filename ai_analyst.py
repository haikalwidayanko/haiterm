import pandas as pd

def generate_strategic_verdict(ticker, score_res, fib_data, p_now, news_alerts):
    """
    Intelligence Logic: Sinkronisasi treshold Quantum +/- 10 dan Astro Area.
    """
    q_score = score_res.get('total', 0)
    golden_ratio = fib_data.get('61.8% (Golden)', 0)

    # 1. PENETUAN THRESHOLD (Sesuai aktual: Max +/- 10)
    is_strong_bias = abs(q_score) >= 8
    is_moderate_bias = abs(q_score) >= 5

    # Jarak toleransi Golden Ratio (0.1% untuk akurasi tinggi)
    proximity_threshold = 0.001
    is_near_golden = abs(p_now - golden_ratio) / golden_ratio < proximity_threshold

    # 2. DECISION MATRIX
    verdict = "NEUTRAL / MONITORING"
    color = "#888888"
    action = "Wait for High Conviction Score"

    # Kondisi POSITIVE (Score harus tinggi + Harga di atas Golden)
    if q_score >= 7 and p_now > golden_ratio:
        verdict = "POSITIVE / BULLISH BIAS"
        color = "#00ffcc"
        if q_score >= 10 and is_near_golden:
            verdict = "EXTREME POSITIVE / CONFIRMED"
            action = "Ready to Execute: HIGH CONVICTION BUY"
        else:
            action = "Build Position: Watch for Golden Ratio Rebound"

    # Kondisi NEGATIVE (Score harus rendah + Harga di bawah Golden)
    elif q_score <= -7 and p_now < golden_ratio:
        verdict = "NEGATIVE / BEARISH BIAS"
        color = "#ff4b4b"
        if q_score <= -10 and is_near_golden:
            verdict = "EXTREME NEGATIVE / CONFIRMED"
            action = "Ready to Execute: HIGH CONVICTION SELL"
        else:
            action = "Build Position: Watch for Golden Ratio Rejection"

    # 3. NEWS SHIELD IMPACT
    news_brief = "News Shield: Stable. No High-Impact Threats."
    if news_alerts:
        news_brief = f"⚠️ WARNING: {len(news_alerts)} High-Impact news active. Reduce Lot Size."
        if is_strong_bias:
            verdict = "CAUTIOUS " + verdict.split('/')[1]

    # 4. SUMMARY GENERATION
    summary = f"Instrument {ticker.replace('=X', '')} holding Quantum Score: {q_score:+}."
    if is_near_golden:
        summary += " Price action currently testing Astro Golden Ratio (61.8%)."
    else:
        summary += " Price is floating between levels. Institutional interest is low at current price."

    return {
        "verdict": verdict,
        "color": color,
        "action": action,
        "summary": summary,
        "news_brief": news_brief,
        "q_val": q_score,
        "is_near": is_near_golden
    }


def generate_narrative_v10(ticker, total_score, ctx):
    """
    Fungsi legacy/fallback untuk kompatibilitas sistem lama.
    """
    verdict = "NEUTRAL"
    if total_score > 5:
        verdict = "BULLISH"
    elif total_score < -5:
        verdict = "BEARISH"

    summary = f"Bias {verdict} terdeteksi dengan skor {total_score:+}. "
    summary += f"Indikator RSI berada di level {ctx.get('rsi', 50):.2f}. "

    return {
        "verdict": f"{verdict} MOMENTUM",
        "summary": summary,
        "action": "Check Fibonacci levels for entry.",
        "score_color": "green" if total_score > 0 else "red"
    }