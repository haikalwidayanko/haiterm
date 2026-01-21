import pandas as pd


def generate_strategic_verdict(ticker, score_res, fib_data, p_now, news_alerts):
    """
    Intelligence Logic: Sensitive threshold +/- 6.
    Fix: UnboundLocalError by initializing variables at the start.
    """
    # 1. INITIALIZATION (Biar nggak error lagi)
    q_score = score_res.get('total', 0)
    golden_ratio = fib_data.get('61.8% (Golden)', 0)

    verdict = "NEUTRAL / MONITORING"
    color = "#888888"
    action = "Wait for Bias"
    news_brief = "News Shield: Stable. No Red Flags."  # Definisikan di awal

    # Jarak toleransi Golden Ratio (0.1%)
    proximity_threshold = 0.001
    is_near_golden = abs(p_now - golden_ratio) / golden_ratio < proximity_threshold

    # 2. DECISION MATRIX (THRESHOLD +/- 6)
    if q_score >= 6:
        # Range 6 - 8: Sedikit Positif
        if q_score <= 8:
            verdict = "SEDIKIT POSITIF"
            color = "#a3ffeb"  # Hijau soft
        # Range > 8: Extreme
        else:
            verdict = "EXTREME POSITIVE / CONFIRMED"
            color = "#00ffcc"  # Hijau neon

        action = "READY TO BUY" if is_near_golden else "Wait for Golden Area"

    elif q_score <= -6:
        # Range -6 s/d -8: Sedikit Negatif
        if q_score >= -8:
            verdict = "SEDIKIT NEGATIF"
            color = "#ff8585"  # Merah soft
        # Range < -8: Extreme
        else:
            verdict = "EXTREME NEGATIVE / CONFIRMED"
            color = "#ff4b4b"  # Merah neon

        action = "READY TO SELL" if is_near_golden else "Wait for Golden Area"

    # 3. NEWS IMPACT OVERRIDE
    if news_alerts:
        news_brief = f"⚠️ WARNING: {len(news_alerts)} High-Impact news active."

    return {
        "verdict": verdict,
        "color": color,
        "action": action,
        "summary": f"Bias {verdict} detect with score {q_score:+}.",
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