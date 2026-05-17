def generate_ai_judgment(quantum_res, fib_data, smc_zones, p_now, atr=None):
    """
    AI Final Decision Engine V3 — Multi-layer confluence analysis.
    Outputs: EXECUTE BUY / EXECUTE SELL / STANDBY / DANGER ZONE
    Trade Plan: Minimum 3:1 R:R enforced. TP1 (1:1), TP2 (2:1), TP3 (3:1), TP4 (5:1).
    """
    q       = quantum_res.get('total', 0)
    details = quantum_res.get('details', {})
    audit   = quantum_res.get('audit', {})

    # Fibonacci Levels
    golden   = fib_data.get('61.8% (Golden)', 0)
    deep     = fib_data.get('78.6% (Deep)', 0)
    low_0    = fib_data.get('0% (Low)', 0)
    high_100 = fib_data.get('100% (High)', 0)
    tp1_ext  = fib_data.get('127.2% (T1)', 0)
    tp2_ext  = fib_data.get('161.8% (T2)', 0)
    fib_50   = fib_data.get('50.0%', 0)

    # Fibonacci proximity
    is_at_golden = golden > 0 and abs(p_now - golden) / golden < 0.003
    is_at_deep   = deep   > 0 and abs(p_now - deep)   / deep   < 0.003
    is_near_fib  = is_at_golden or is_at_deep

    # SMC Zones
    bull_fvg = [z for z in smc_zones if z.get('type') == 'BULL_FVG']
    bear_fvg = [z for z in smc_zones if z.get('type') == 'BEAR_FVG']

    # Price Action Data
    pa_s = details.get('PriceAction', 0)
    pa_data = quantum_res.get('pa_data', {})
    pa_signal = pa_data.get('signal', 'NONE')
    pa_reason = pa_data.get('reason', '')

    # ── CONFIDENCE SCORING (Max 100) ─────────────────────────
    conf = 0
    if   abs(q) >= 12: conf += 30
    elif abs(q) >= 9:  conf += 25
    elif abs(q) >= 6:  conf += 18
    elif abs(q) >= 3:  conf += 10
    else:              conf += 3

    if   is_at_golden: conf += 20
    elif is_near_fib:  conf += 12
    elif golden > 0 and abs(p_now - golden) / golden < 0.01: conf += 6
    else: conf += 2

    trend = details.get('Trend', 0)
    mom   = details.get('Momentum', 0)
    if (trend > 0 and mom > 0) or (trend < 0 and mom < 0): conf += 20
    elif (trend > 0 and mom < 0) or (trend < 0 and mom > 0): conf += 3
    else: conf += 10

    if   (q > 0 and bull_fvg) or (q < 0 and bear_fvg): conf += 15
    elif bull_fvg or bear_fvg: conf += 7
    else: conf += 2

    bb_s   = details.get('Bollinger', 0)
    vwap_s = details.get('VWAP', 0)
    if (q > 0 and bb_s >= 0 and vwap_s > 0) or (q < 0 and bb_s <= 0 and vwap_s < 0): conf += 15
    elif (bb_s != 0 or vwap_s != 0): conf += 7
    else: conf += 2

    # PA Confidence Bonus
    if (q > 0 and pa_s > 0) or (q < 0 and pa_s < 0): conf += 25
    elif pa_s != 0: conf += 5

    conf = min(conf, 97)

    # ── REASONING CHAIN ──────────────────────────────────────
    reasons = []
    if audit.get('Trend'):     reasons.append(f"📊 **Trend**: {audit['Trend']}")
    if audit.get('Momentum'):  reasons.append(f"⚡ **Momentum**: {audit['Momentum']}")
    if audit.get('Bollinger'): reasons.append(f"🎯 **Bollinger**: {audit['Bollinger']}")
    if audit.get('VWAP'):      reasons.append(f"🏦 **VWAP**: {audit['VWAP']}")
    if audit.get('ADX'):       reasons.append(f"💪 **Trend Power**: {audit['ADX']}")
    if audit.get('Macro'):     reasons.append(f"🌐 **Macro**: {audit['Macro']}")
    if audit.get('MTF'):       reasons.append(f"📡 **Multi-TF**: {audit['MTF']}")
    if audit.get('Sentiment'): reasons.append(f"📰 **Sentiment**: {audit['Sentiment']}")
    if is_at_golden:           reasons.append("✨ **Fibonacci**: Price at Golden Ratio 61.8% — High-precision entry zone")
    elif is_near_fib:          reasons.append("📐 **Fibonacci**: Near key Fibonacci support/resistance")
    if bull_fvg:               reasons.append(f"🔍 **SMC**: {len(bull_fvg)} Bullish FVG (Institutional Buy Gap) detected")
    if bear_fvg:               reasons.append(f"🔍 **SMC**: {len(bear_fvg)} Bearish FVG (Institutional Sell Gap) detected")
    if pa_s != 0:              reasons.append(f"🕯️ **Price Action**: {pa_reason}")

    # ── PLAN BUILDER — Minimum 3:1 R:R enforced ──────────────
    plan = {"entry": 0, "sl": 0, "tp1": 0, "tp2": 0, "tp3": 0, "tp4": 0,
            "pips_sl": 0, "pips_tp1": 0, "pips_tp2": 0, "pips_tp3": 0, "pips_tp4": 0,
            "rr1": 0, "rr2": 0, "rr3": 0, "rr4": 0,
            "risk_pips": 0, "atr_used": 0}

    # ── FINAL DECISION LOGIC ─────────────────────────────────
    is_danger = abs(q) >= 6 and not is_near_fib and not (bull_fvg or bear_fvg) and conf < 50

    if is_danger:
        decision = "DANGER ZONE"
        color    = "#FF8C00"
        action   = "Sinyal kuat tapi tidak ada konfirmasi Fibonacci + SMC. Tahan posisi."
        reasons.insert(0, "⚠️ **Warning**: High score tanpa konfluensi Fibonacci/SMC — risiko tinggi")

    elif q >= 6 and conf >= 60 and pa_s > 0:
        decision = "EXECUTE BUY"
        color    = "#00ffcc"
        action   = "Sinyal Buy terkonfirmasi oleh Candlestick/Sweep PA. Momentum Valid. Eksekusi sekarang."
        entry    = p_now
        sl_raw   = deep if (deep > 0 and deep < entry) else (low_0 if low_0 < entry else entry * 0.995)
        plan     = _build_plan_buy(entry, sl_raw, tp1_ext, tp2_ext, high_100, atr, p_now)

    elif q >= 5:
        decision = "BULLISH BIAS"
        color    = "#a3ffeb"
        if pa_s <= 0:
            action = "Momentum bullish tapi belum ada konfirmasi Price Action. Tunggu candle reject."
        else:
            action = "Kondisi bullish namun skor Quantum masih rendah. Entry kecil."
        entry    = golden if golden > 0 else p_now
        sl_raw   = low_0 if low_0 < entry else entry * 0.995
        plan     = _build_plan_buy(entry, sl_raw, tp1_ext, tp2_ext, high_100, atr, p_now)

    elif q <= -6 and conf >= 60 and pa_s < 0:
        decision = "EXECUTE SELL"
        color    = "#ff4b4b"
        action   = "Sinyal Sell terkonfirmasi oleh Candlestick/Sweep PA. Momentum Valid. Eksekusi sekarang."
        entry    = p_now
        sl_raw   = high_100 if high_100 > entry else entry * 1.005
        plan     = _build_plan_sell(entry, sl_raw, tp1_ext, tp2_ext, low_0, atr, p_now)

    elif q <= -5:
        decision = "BEARISH BIAS"
        color    = "#ff8585"
        if pa_s >= 0:
            action = "Tekanan jual tapi belum ada konfirmasi Price Action. Tunggu candle reject."
        else:
            action = "Kondisi bearish namun skor Quantum masih rendah. Short kecil."
        entry    = golden if golden > 0 else p_now
        sl_raw   = high_100 if high_100 > entry else entry * 1.005
        plan     = _build_plan_sell(entry, sl_raw, tp1_ext, tp2_ext, low_0, atr, p_now)

    else:
        decision = "STANDBY"
        color    = "#888888"
        action   = "Tidak ada sinyal jelas. Market dalam konsolidasi. Tunggu setup premium."
        conf     = max(conf - 25, 10)

    return {
        "decision":    decision,
        "color":       color,
        "action":      action,
        "confidence":  conf,
        "reasons":     reasons,
        "plan":        plan,
        "q_val":       q,
        "is_near_fib": is_near_fib,
        "bull_fvg":    len(bull_fvg),
        "bear_fvg":    len(bear_fvg),
        # Legacy compat
        "judgement":   decision,
        "smc_logic":   f"{len(bull_fvg)} Bull FVG | {len(bear_fvg)} Bear FVG",
        "is_floor":    is_at_golden,
        "pa_signal":   pa_signal,
        "pa_reason":   pa_reason,
        "pa_score":    pa_s,
    }


# ── PLAN BUILDERS ────────────────────────────────────────────────────────────

def _pip_value(price_a, price_b, entry):
    """Convert price diff to pip-equivalent value (5-decimal = 0.0001 pip unit)."""
    diff = abs(price_a - price_b)
    if entry > 100:      # JPY pairs, indices
        return round(diff * 100, 1)
    elif entry < 0.01:   # crypto < 1 cent (SHIB)
        return round(diff * 1_000_000, 1)
    elif entry < 1:      # crypto mid (sub-1 USD)
        return round(diff * 10_000, 1)
    elif entry > 1000:   # BTC, high-price crypto / gold
        return round(diff, 2)
    else:                # standard forex 0.xxxxx
        return round(diff * 10_000, 1)


def _build_plan_buy(entry, sl_raw, tp1_ext, tp2_ext, high_100, atr, p_now):
    """
    Build BUY trade plan. SL = below entry. TPs at 1:1, 2:1, 3:1, 5:1 R:R minimum.
    ATR used to ensure SL is not too tight. Minimum 3:1 on TP3.
    """
    # SL — use whichever is tighter but still below entry; ATR floor
    if sl_raw >= entry:
        sl_raw = entry * 0.995  # fallback

    risk = entry - sl_raw
    if atr and atr > 0:
        min_risk = atr * 1.0   # SL must be at least 1× ATR
        if risk < min_risk:
            sl_raw = entry - min_risk
            risk   = min_risk

    # TP levels — minimum distances enforced
    tp1 = entry + risk * 1.0   # 1:1
    tp2 = entry + risk * 2.0   # 2:1
    tp3 = entry + risk * 3.0   # 3:1  ← minimum target for trade validity
    tp4 = entry + risk * 5.0   # 5:1  ← premium runner target

    # Upgrade TP3/TP4 if fib extensions are further out
    if tp1_ext > tp3:
        tp3 = tp1_ext
        tp4 = max(tp4, tp2_ext) if tp2_ext > tp3 else tp3 + risk * 2
    if high_100 > tp2 and high_100 < tp3:
        tp3 = max(tp3, high_100 + risk * 0.5)

    return _pack_plan(entry, sl_raw, tp1, tp2, tp3, tp4, direction="BUY", p_now=p_now)


def _build_plan_sell(entry, sl_raw, tp1_ext, tp2_ext, low_0, atr, p_now):
    """
    Build SELL trade plan. SL = above entry. TPs at 1:1, 2:1, 3:1, 5:1 R:R minimum.
    """
    if sl_raw <= entry:
        sl_raw = entry * 1.005  # fallback

    risk = sl_raw - entry
    if atr and atr > 0:
        min_risk = atr * 1.0
        if risk < min_risk:
            sl_raw = entry + min_risk
            risk   = min_risk

    tp1 = entry - risk * 1.0
    tp2 = entry - risk * 2.0
    tp3 = entry - risk * 3.0   # 3:1
    tp4 = entry - risk * 5.0   # 5:1

    # Upgrade with fib extension if further down
    if low_0 > 0 and low_0 < tp3:
        tp3 = low_0
        tp4 = min(tp4, low_0 - risk * 2)

    return _pack_plan(entry, sl_raw, tp1, tp2, tp3, tp4, direction="SELL", p_now=p_now)


def _pack_plan(entry, sl, tp1, tp2, tp3, tp4, direction="BUY", p_now=0):
    """Pack plan dict with pip distances and R:R ratios."""
    risk = abs(entry - sl)
    if risk == 0:
        return {}

    sign = 1 if direction == "BUY" else -1
    dist_to_entry = abs(p_now - entry)
    
    if direction == "BUY":
        if p_now <= sl: status = "INVALID (Kena SL)"
        elif dist_to_entry <= risk * 0.3: status = "FRESH MEAT 🥩"
        elif p_now > entry and p_now < tp1: status = "IN PROGRESS"
        elif p_now >= tp1: status = "MISSED 🚀 (Ketinggalan)"
        else: status = "WAITING (Belum Masuk)"
    else:
        if p_now >= sl: status = "INVALID (Kena SL)"
        elif dist_to_entry <= risk * 0.3: status = "FRESH MEAT 🥩"
        elif p_now < entry and p_now > tp1: status = "IN PROGRESS"
        elif p_now <= tp1: status = "MISSED 🚀 (Ketinggalan)"
        else: status = "WAITING (Belum Masuk)"

    def rr(tp): return round(abs(tp - entry) / risk, 1)
    def pips(a, b): return _pip_value(a, b, entry)

    return {
        "direction": direction,
        "entry":     entry,
        "sl":        sl,
        "tp1":       tp1,
        "tp2":       tp2,
        "tp3":       tp3,
        "tp4":       tp4,
        "risk_pips": pips(entry, sl),
        "pips_sl":   pips(entry, sl),
        "pips_tp1":  pips(entry, tp1),
        "pips_tp2":  pips(entry, tp2),
        "pips_tp3":  pips(entry, tp3),
        "pips_tp4":  pips(entry, tp4),
        "rr1":       rr(tp1),   # should be 1.0
        "rr2":       rr(tp2),   # should be 2.0
        "rr3":       rr(tp3),   # should be ≥3.0
        "rr4":       rr(tp4),   # should be ≥5.0
        "rr_ratio":  rr(tp2),   # Make TP2 the headline RR
        "atr_used":  0,
        "entry_status": status,
    }