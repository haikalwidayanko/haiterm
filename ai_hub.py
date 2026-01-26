import pandas as pd


def generate_ai_judgment(quantum_res, fib_data, smc_zones, p_now):
    """
    Final Judgment Engine: Mengkombinasi Quantum, Astro, dan SMC.
    Pastikan nama fungsi ini 'generate_ai_judgment' agar tidak ImportError.
    """
    # 1. Ambil skor Quantum (fallback ke 0 jika kosong)
    q_score = quantum_res.get('total', 0)

    # 2. Ambil Level Astro (Golden Ratio)
    golden_ratio = fib_data.get('61.8% (Golden)', 0)

    # Proteksi pembagian nol & Hitung kedekatan harga
    if golden_ratio > 0:
        dist_to_golden = abs(p_now - golden_ratio) / (golden_ratio + 1e-9)
        is_at_floor = dist_to_golden < 0.0018  # Toleransi 0.18%
    else:
        is_at_floor = False

    # 3. Deteksi Jejak SMC (FVG)
    unfilled_bull = [z for z in smc_zones if z['type'] == 'BULLISH FVG' and z['status'] == 'Unfilled']
    unfilled_bear = [z for z in smc_zones if z['type'] == 'BEARISH FVG' and z['status'] == 'Unfilled']

    # Default State (Mencari Sinyal)
    confidence = 30
    judgement = "SCANNING MARKET"
    color = "#555555"
    action = "Market conditions are neutral. Waiting for confluence."

    # --- LOGIKA KEPUTUSAN ---

    # KONDISI BULLISH (BUY)
    if q_score >= 6:
        if is_at_floor:
            judgement = "HIGH CONVICTION BUY"
            confidence = 90 if unfilled_bull else 75
            color = "#00ffcc"
            action = "Perfect alignment: Quantum Energy + Astro Floor."
        else:
            judgement = "BULLISH BIAS"
            confidence = 55
            color = "#00ccff"
            action = "Energy is up, but price is premium. Wait for retrace."

    # KONDISI BEARISH (SELL)
    elif q_score <= -6:
        if is_at_floor:  # Dekat resistance/reversal level
            judgement = "HIGH CONVICTION SELL"
            confidence = 90 if unfilled_bear else 75
            color = "#ff4b4b"
            action = "Heavy supply detected at key Fibonacci level."
        else:
            judgement = "BEARISH BIAS"
            confidence = 55
            color = "#ff8800"
            action = "Downside momentum exists. Watch for pullbacks."

    # KEAMANAN: NO TRADE ZONE
    if abs(q_score) < 4:
        confidence = 20
        judgement = "NO TRADE ZONE"
        color = "#333333"
        action = "Momentum is too weak. Capital preservation is priority."

    return {
        "judgement": judgement,
        "confidence": confidence,
        "color": color,
        "action": action,
        "q_val": q_score,
        "is_floor": is_at_floor,
        "fvg_found": len(unfilled_bull) > 0 or len(unfilled_bear) > 0
    }