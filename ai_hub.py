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


def generate_ai_judgment(quantum_res, fib_data, smc_zones, p_now):
    q_score = quantum_res.get('total', 0)

    # Ambil Level dari Engine
    low_0 = fib_data.get('0% (Low)', 0)
    high_100 = fib_data.get('100% (High)', 0)
    golden = fib_data.get('61.8% (Golden)', 0)
    deep_fib = fib_data.get('78.6% (Deep)', 0)
    tp1 = fib_data.get('127.2% (T1)', 0)
    tp2 = fib_data.get('161.8% (T2)', 0)

    # Deteksi FVG (Smart Money)
    unfilled_bull = [z for z in smc_zones if z['type'] == 'BULLISH FVG' and z['status'] == 'Unfilled']
    unfilled_bear = [z for z in smc_zones if z['type'] == 'BEARISH FVG' and z['status'] == 'Unfilled']

    # Ringkasan SMC untuk UI
    if unfilled_bull:
        smc_desc = "INSTITUTIONAL BUY GAP"
    elif unfilled_bear:
        smc_desc = "INSTITUTIONAL SELL GAP"
    else:
        smc_desc = "EFFICIENT MARKET"

    plan = {"entry": 0, "sl": 0, "tp1": 0, "tp2": 0}

    # --- LOGIKA BULLISH (BUY) ---
    if q_score >= 4:
        judgement = "HIGH CONVICTION BUY" if q_score >= 7 else "BULLISH BIAS"
        color = "#00ffcc"

        # ENTRY: Pilih yang paling rasional antara FVG Mid atau Golden Ratio
        plan['entry'] = unfilled_bull[0]['mid'] if unfilled_bull else golden

        # STOP LOSS (SAFETY FIX): Harus di bawah Entry!
        # Kita ambil level terendah antara Deep Fib atau Low 0.
        # Kalau masih lebih tinggi dari Entry, kita paksa SL 0.5% di bawah Entry.
        potential_sl = deep_fib if (deep_fib > 0 and deep_fib < plan['entry']) else (
            low_0 if low_0 < plan['entry'] else plan['entry'] * 0.995)
        plan['sl'] = potential_sl

        plan['tp1'] = tp1 if tp1 > plan['entry'] else high_100
        plan['tp2'] = tp2 if tp2 > plan['tp1'] else (plan['tp1'] * 1.01)
        action = "Institutions are loading. Set buy limits at the gap."

    # --- LOGIKA BEARISH (SELL) ---
    elif q_score <= -4:
        judgement = "HIGH CONVICTION SELL" if q_score <= -7 else "BEARISH BIAS"
        color = "#ff4b4b"

        plan['entry'] = unfilled_bear[0]['mid'] if unfilled_bear else golden

        # STOP LOSS (SAFETY FIX): Harus di atas Entry!
        potential_sl = deep_fib if (deep_fib > plan['entry']) else (
            high_100 if high_100 > plan['entry'] else plan['entry'] * 1.005)
        plan['sl'] = potential_sl

        # Target TP ke arah bawah (0% Fib atau extension bawah)
        plan['tp1'] = low_0
        plan['tp2'] = low_0 - (abs(tp1 - tp2))
        action = "Heavy supply detected. Short the bounces."

    else:
        judgement = "NO TRADE ZONE"
        color = "#888888"
        smc_desc = "NO FOOTPRINTS"
        action = "Conflicting signals. Wait for a clearer setup."

    return {
        "judgement": judgement,
        "confidence": 90 if (q_score >= 7 and abs(p_now - golden) / golden < 0.002) else 50,
        "color": color,
        "action": action,
        "q_val": q_score,
        "plan": plan,
        "smc_logic": smc_desc,
        "is_floor": abs(p_now - golden) / golden < 0.002 if golden > 0 else False
    }