import pandas as pd
import numpy as np


# ============================================================
# INDICATOR CALCULATIONS
# ============================================================

def hitung_indikator_lengkap(df):
    """Quantum V12: Full indicator suite."""
    if df is None or df.empty:
        return df
    df = df.copy()
    # Flatten MultiIndex columns if yfinance returned them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.loc[:, ~df.columns.duplicated()]
    # Squeeze any column that is still a DataFrame to a Series
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df.columns and isinstance(df[col], pd.DataFrame):
            df[col] = df[col].iloc[:, 0]
    df = df.ffill().bfill()

    # A. EMA STACK (Trend Foundation)
    df['EMA20']  = df['Close'].ewm(span=20,  adjust=False).mean()
    df['EMA50']  = df['Close'].ewm(span=50,  adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    df['MA20'], df['MA50'], df['MA200'] = df['EMA20'], df['EMA50'], df['EMA200']

    # B. RSI 14
    delta = df['Close'].diff()
    gain  = delta.where(delta > 0, 0).rolling(14).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / (loss + 1e-9)))

    # C. STOCHASTIC RSI (StochRSI K/D)
    rsi_min = df['RSI'].rolling(14).min()
    rsi_max = df['RSI'].rolling(14).max()
    stoch_raw = (df['RSI'] - rsi_min) / (rsi_max - rsi_min + 1e-9)
    df['StochRSI_K'] = stoch_raw.rolling(3).mean() * 100
    df['StochRSI_D'] = df['StochRSI_K'].rolling(3).mean()

    # D. MACD (12, 26, 9)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD']        = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist']   = df['MACD'] - df['MACD_Signal']

    # E. BOLLINGER BANDS (20, 2σ)
    bb_mid = df['Close'].rolling(20).mean()
    bb_std = df['Close'].rolling(20).std()
    df['BB_Upper'] = bb_mid + 2 * bb_std
    df['BB_Lower'] = bb_mid - 2 * bb_std
    df['BB_Mid']   = bb_mid
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / (bb_mid + 1e-9)
    df['BB_PctB']  = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'] + 1e-9)

    # F. ATR 14 (Volatility)
    hl  = df['High'] - df['Low']
    hc  = np.abs(df['High'] - df['Close'].shift())
    lc  = np.abs(df['Low']  - df['Close'].shift())
    df['ATR'] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()

    # G. ADX (Trend Strength)
    df['ADX'] = hitung_adx_manual(df)

    # H. ICHIMOKU CLOUD
    df = _calc_ichimoku(df)

    # I. VWAP (Rolling 20)
    vol_col = 'Volume' if 'Volume' in df.columns else None
    if vol_col and df[vol_col].sum() > 0:
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (tp * df[vol_col]).rolling(20).sum() / (df[vol_col].rolling(20).sum() + 1e-9)
    else:
        df['VWAP'] = df['Close'].rolling(20).mean()

    # J. WILLIAMS %R (14)
    h14 = df['High'].rolling(14).max()
    l14 = df['Low'].rolling(14).min()
    df['Williams_R'] = ((h14 - df['Close']) / (h14 - l14 + 1e-9)) * -100

    return df.fillna(0)


def _calc_ichimoku(df):
    h9   = df['High'].rolling(9).max();  l9  = df['Low'].rolling(9).min()
    h26  = df['High'].rolling(26).max(); l26 = df['Low'].rolling(26).min()
    h52  = df['High'].rolling(52).max(); l52 = df['Low'].rolling(52).min()
    df['Ichi_Tenkan'] = (h9  + l9)  / 2
    df['Ichi_Kijun']  = (h26 + l26) / 2
    df['Ichi_SpanA']  = ((df['Ichi_Tenkan'] + df['Ichi_Kijun']) / 2).shift(26)
    df['Ichi_SpanB']  = ((h52 + l52) / 2).shift(26)
    df['Ichi_Chikou'] = df['Close'].shift(-26)
    return df


def hitung_adx_manual(df, window=14):
    d = df.copy()
    d['TR']  = pd.concat([d['High'] - d['Low'], (d['High'] - d['Close'].shift()).abs(), (d['Low'] - d['Close'].shift()).abs()], axis=1).max(axis=1)
    d['+DM'] = d['High'].diff().clip(lower=0)
    d['-DM'] = d['Low'].diff().apply(lambda x: -x).clip(lower=0)
    tr_s  = d['TR'].rolling(window).mean() + 1e-9
    di_p  = 100 * (d['+DM'].rolling(window).mean() / tr_s)
    di_m  = 100 * (d['-DM'].rolling(window).mean() / tr_s)
    dx    = 100 * ((di_p - di_m).abs() / (di_p + di_m + 1e-9))
    return dx.rolling(window).mean()


def calculate_fibonacci_levels(df):
    if df is None or len(df) < 60:
        return {}
    r    = df.tail(60)
    high = r['High'].max(); low = r['Low'].min()
    diff = high - low or 1e-9
    return {
        '0% (Low)':        low,
        '23.6%':           high - diff * 0.236,
        '38.2%':           high - diff * 0.382,
        '50.0%':           high - diff * 0.500,
        '61.8% (Golden)':  high - diff * 0.618,
        '78.6% (Deep)':    high - diff * 0.786,
        '100% (High)':     high,
        '127.2% (T1)':     high + diff * 0.272,
        '161.8% (T2)':     high + diff * 0.618,
    }


# ============================================================
# QUANTUM SCORING ENGINE V12
# ============================================================

def get_detailed_scores_v12(df, macro, sentiment_score, fib_data, htf_bias=0, sent_reason=""):
    """
    Quantum Engine V12 — 9-dimension confluence scoring.
    Indicators: EMA, StochRSI, MACD, Bollinger, Ichimoku, VWAP, Williams %R, ADX, ATR, Fibonacci, Macro
    Score range: capped at ±15. Signal threshold: ±6.
    """
    if df is None or df.empty:
        return {"total": 0, "details": {}, "audit": {}}

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    p    = last['Close']
    audit = {}

    # ── 1. TREND ENGINE (±6) ──────────────────────────────────
    t = 0; t_n = []
    # EMA 200 (+/-2)
    if p > last['EMA200']: t += 2; t_n.append("Price > EMA200 ✓ Bullish")
    else:                  t -= 2; t_n.append("Price < EMA200 ✗ Bearish")
    # EMA 50 (+/-1)
    if p > last['EMA50']:  t += 1; t_n.append("Above EMA50")
    else:                  t -= 1; t_n.append("Below EMA50")
    # EMA20 × EMA50 Crossover (+/-2)
    e20n, e50n = last['EMA20'], last['EMA50']
    e20p, e50p = prev['EMA20'], prev['EMA50']
    if   e20p <= e50p and e20n > e50n: t += 2; t_n.append("🔥 Golden Cross EMA20×50")
    elif e20p >= e50p and e20n < e50n: t -= 2; t_n.append("💀 Death Cross EMA20×50")
    else: t_n.append("EMA Slope " + ("Up" if e20n > e20p else "Down"))
    # Ichimoku Cloud (+/-1)
    span_a, span_b = last['Ichi_SpanA'], last['Ichi_SpanB']
    above_cloud = p > max(span_a, span_b)
    below_cloud = p < min(span_a, span_b)
    if   above_cloud: t += 1; t_n.append("Ichimoku: Above Cloud ✓")
    elif below_cloud: t -= 1; t_n.append("Ichimoku: Below Cloud ✗")
    else:             t_n.append("Ichimoku: Inside Cloud (Neutral)")
    audit['Trend'] = " | ".join(t_n)

    # ── 2. MOMENTUM ENGINE (±6) ───────────────────────────────
    m = 0; m_n = []
    # StochRSI K/D crossover (+/-2)
    sk, sd = last['StochRSI_K'], last['StochRSI_D']
    sk_p, sd_p = prev['StochRSI_K'], prev['StochRSI_D']
    if   sk_p <= sd_p and sk > sd: m += 2; m_n.append(f"StochRSI Bullish Cross K={sk:.1f}")
    elif sk_p >= sd_p and sk < sd: m -= 2; m_n.append(f"StochRSI Bearish Cross K={sk:.1f}")
    elif sk > 80: m += 1; m_n.append(f"StochRSI Overbought ({sk:.1f})")
    elif sk < 20: m -= 1; m_n.append(f"StochRSI Oversold ({sk:.1f})")
    else:         m_n.append(f"StochRSI Neutral ({sk:.1f})")
    # MACD Histogram (+/-2)
    mh, mh_p = last['MACD_Hist'], prev['MACD_Hist']
    if   mh > 0 and mh > mh_p: m += 2; m_n.append("MACD Hist ↑ Bullish Accel")
    elif mh > 0 and mh <= mh_p: m += 1; m_n.append("MACD Hist Slowing (Bullish)")
    elif mh < 0 and mh < mh_p: m -= 2; m_n.append("MACD Hist ↓ Bearish Accel")
    elif mh < 0 and mh >= mh_p: m -= 1; m_n.append("MACD Hist Rising (Bearish)")
    # Williams %R (+/-2)
    wr = last['Williams_R']
    if   wr > -20:  m += 2; m_n.append(f"Williams %R Overbought ({wr:.1f}) → Bullish")
    elif wr < -80:  m -= 2; m_n.append(f"Williams %R Oversold ({wr:.1f}) → Bearish")
    elif wr > -50:  m += 1; m_n.append(f"Williams %R Bullish Zone ({wr:.1f})")
    else:           m -= 1; m_n.append(f"Williams %R Bearish Zone ({wr:.1f})")
    audit['Momentum'] = " | ".join(m_n)

    # ── 3. BOLLINGER BANDS (±2) ───────────────────────────────
    bb = 0; bb_n = []
    pctb = last['BB_PctB']; width = last['BB_Width']
    avg_width = df['BB_Width'].tail(20).mean() if len(df) > 20 else width
    if   pctb > 1.0:  bb -= 1; bb_n.append("Price above BB Upper (Overbought)")
    elif pctb < 0.0:  bb += 1; bb_n.append("Price below BB Lower (Oversold)")
    elif pctb > 0.8:  bb += 1; bb_n.append(f"BB Upper Ride (%B={pctb:.2f})")
    elif pctb < 0.2:  bb -= 1; bb_n.append(f"BB Lower Ride (%B={pctb:.2f})")
    else:             bb_n.append(f"BB Mid Zone (%B={pctb:.2f})")
    if width < avg_width * 0.7: bb_n.append("⚡ Bollinger Squeeze (Breakout Incoming)")
    elif width > avg_width * 1.5: bb_n.append("Bollinger Expansion (High Volatility)")
    audit['Bollinger'] = " | ".join(bb_n)

    # ── 4. VWAP INSTITUTIONAL BIAS (±1) ──────────────────────
    vwap = last['VWAP']
    if   p > vwap * 1.001: vwap_s = 1; audit['VWAP'] = f"Price above VWAP ({vwap:.5f}) → Institutional Buy"
    elif p < vwap * 0.999: vwap_s = -1; audit['VWAP'] = f"Price below VWAP ({vwap:.5f}) → Institutional Sell"
    else:                   vwap_s = 0; audit['VWAP'] = "Price near VWAP (Equilibrium)"

    # ── 5. ADX TREND POWER (±1) ──────────────────────────────
    adx = last.get('ADX', 0)
    if   adx > 30: adx_s = 1;  audit['ADX'] = f"ADX {adx:.1f} (Strong Trend → Full Conviction)"
    elif adx > 20: adx_s = 0;  audit['ADX'] = f"ADX {adx:.1f} (Moderate Trend)"
    else:          adx_s = -1; audit['ADX'] = f"ADX {adx:.1f} (Ranging Market → Caution)"

    # ── 6. ATR VOLATILITY (±1) ───────────────────────────────
    atr = last.get('ATR', 0)
    atr_s = 0
    if len(df) > 20:
        atr_avg = df['ATR'].tail(20).mean()
        if atr > atr_avg * 1.3:
            if (t > 0 and m > 0) or (t < 0 and m < 0): atr_s = 1; audit['Volatility'] = "ATR Expanding + Trend Aligned (Breakout Mode)"
            else: audit['Volatility'] = "ATR Expanding but Divergent Signals"
        elif atr < atr_avg * 0.7: atr_s = -1; audit['Volatility'] = "ATR Squeeze (Fake Move Risk)"
        else: audit['Volatility'] = "ATR Normal Range"

    # ── 7. MTF ALIGNMENT BONUS (+2) ──────────────────────────
    mtf = 0
    if   htf_bias > 0 and (t + m) > 0: mtf = 2; audit['MTF'] = "HTF Bullish Aligned ✓ (+2 Bonus)"
    elif htf_bias < 0 and (t + m) < 0: mtf = 2; audit['MTF'] = "HTF Bearish Aligned ✓ (+2 Bonus)"
    else: audit['MTF'] = "Timeframes Divergent (No Bonus)"

    # ── 8. MACRO DXY CORRELATION (±2) ────────────────────────
    dxy = macro.get('dxy_val', 0)
    macro_s = (2 if dxy < 100 else -2) if dxy > 0 else 0
    audit['Macro'] = f"DXY {dxy:.2f} ({'Weak → Risk-On' if dxy < 100 else 'Strong → Risk-Off'})" if dxy > 0 else "DXY Unavailable"

    # ── 9. SENTIMENT NARRATIVE (±2) ──────────────────────────
    audit['Sentiment'] = (f"Bullish: {sent_reason}" if sentiment_score > 0 else
                          f"Bearish: {sent_reason}" if sentiment_score < 0 else "Neutral Narrative")

    # ── 10. PRICE ACTION ENGINE (±4) ─────────────────────────
    pa_data = deteksi_price_action(df)
    pa_s = pa_data['score']
    if pa_s > 0: audit['PriceAction'] = f"Bullish PA (+{pa_s}): {pa_data['reason']}"
    elif pa_s < 0: audit['PriceAction'] = f"Bearish PA ({pa_s}): {pa_data['reason']}"
    else: audit['PriceAction'] = "No Significant PA Pattern"

    total = t + m + bb + vwap_s + adx_s + atr_s + mtf + macro_s + sentiment_score + pa_s
    total = max(min(total, 15), -15)

    return {
        "total": total,
        "details": {
            "Trend":     t,
            "Momentum":  m,
            "Bollinger": bb,
            "VWAP":      vwap_s,
            "ADX":       adx_s,
            "Volatility": atr_s,
            "MTF":       mtf,
            "Macro":     macro_s,
            "Sentiment": sentiment_score,
            "PriceAction": pa_s,
        },
        "pa_data": pa_data,
        "audit": audit
    }


def deteksi_price_action(df):
    """
    Deteksi Price Action: Candlestick Rejection (Engulfing/Pin Bar) & Liquidity Sweeps.
    """
    if df is None or len(df) < 25:
        return {"signal": "NONE", "score": 0, "reason": "Not enough data"}
        
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    c, o, h, l = float(last['Close']), float(last['Open']), float(last['High']), float(last['Low'])
    pc, po = float(prev['Close']), float(prev['Open'])
    
    body = abs(c - o)
    upper_wick = h - max(c, o)
    lower_wick = min(c, o) - l
    total_len = h - l or 1e-9
    
    atr = float(last.get('ATR', total_len))
    
    signal = "NONE"
    score = 0
    reason = []

    # 1. Candlestick Patterns
    if pc < po and c > o and c > po and o < pc:
        signal = "BULLISH_ENGULFING"
        score += 3
        reason.append("Bullish Engulfing")
    elif pc > po and c < o and c < po and o > pc:
        signal = "BEARISH_ENGULFING"
        score -= 3
        reason.append("Bearish Engulfing")
    elif lower_wick > body * 2 and upper_wick < body * 0.5 and total_len > atr * 0.5:
        signal = "BULLISH_PINBAR"
        score += 2
        reason.append("Bullish Pin Bar Rejection")
    elif upper_wick > body * 2 and lower_wick < body * 0.5 and total_len > atr * 0.5:
        signal = "BEARISH_PINBAR"
        score -= 2
        reason.append("Bearish Pin Bar Rejection")

    # 2. Liquidity Sweep (SFP)
    lookback = df.iloc[-22:-2]
    swing_high = float(lookback['High'].max())
    swing_low = float(lookback['Low'].min())
    
    if l < swing_low and c > swing_low:
        signal = "BULLISH_SWEEP"
        score += 4
        reason.append(f"Bullish Liquidity Sweep (SFP) at {swing_low:.5f}")
    elif h > swing_high and c < swing_high:
        signal = "BEARISH_SWEEP"
        score -= 4
        reason.append(f"Bearish Liquidity Sweep (SFP) at {swing_high:.5f}")

    return {"signal": signal, "score": score, "reason": " | ".join(reason) if reason else "No PA Pattern"}


def deteksi_smc_v2(df):
    """Detect Fair Value Gaps (FVG) for Smart Money Concepts."""
    fvg = []
    subset = df.tail(50)
    for i in range(2, len(subset)):
        if subset['Low'].iloc[i] > subset['High'].iloc[i - 2]:
            fvg.append({'type': 'BULL_FVG', 'top': subset['Low'].iloc[i], 'bottom': subset['High'].iloc[i - 2],
                        'mid': (subset['Low'].iloc[i] + subset['High'].iloc[i - 2]) / 2})
        elif subset['High'].iloc[i] < subset['Low'].iloc[i - 2]:
            fvg.append({'type': 'BEAR_FVG', 'top': subset['Low'].iloc[i - 2], 'bottom': subset['High'].iloc[i],
                        'mid': (subset['Low'].iloc[i - 2] + subset['High'].iloc[i]) / 2})
    return fvg


# ============================================================
# BACKTESTING ENGINE
# ============================================================

def run_backtest(df):
    """
    Simulates trades based on technical Quantum Score signals over the provided historical dataframe.
    Entry logic: Technical Score >= 4 (Buy), <= -4 (Sell)
    Exit logic: SL = Entry ± 1.5 * ATR, TP = Entry ∓ 4.5 * ATR (3:1 R:R)
    """
    if df is None or len(df) < 50:
        return {"total_trades": 0, "win_rate": 0, "pips_net": 0, "history": []}
    
    trades = []
    in_trade = False
    entry_price = 0
    sl = 0
    tp = 0
    direction = 0 # 1 for Buy, -1 for Sell
    entry_time = None

    for i in range(50, len(df)):
        row = df.iloc[i]
        curr_time = df.index[i]
        c = float(row['Close'])
        h = float(row['High'])
        l = float(row['Low'])
        atr = float(row.get('ATR', c * 0.005))
        
        if in_trade:
            # Check exit conditions
            if direction == 1:
                if l <= sl:
                    trades.append({"entry_time": entry_time, "exit_time": curr_time, "type": "BUY", "result": "LOSS", "pips": (sl - entry_price)*10000})
                    in_trade = False
                elif h >= tp:
                    trades.append({"entry_time": entry_time, "exit_time": curr_time, "type": "BUY", "result": "WIN", "pips": (tp - entry_price)*10000})
                    in_trade = False
            else:
                if h >= sl:
                    trades.append({"entry_time": entry_time, "exit_time": curr_time, "type": "SELL", "result": "LOSS", "pips": (entry_price - sl)*10000})
                    in_trade = False
                elif l <= tp:
                    trades.append({"entry_time": entry_time, "exit_time": curr_time, "type": "SELL", "result": "WIN", "pips": (entry_price - tp)*10000})
                    in_trade = False
            continue
            
        # Entry Logic (Calculate Technical Score)
        score = 0
        
        # Trend
        if c > row['EMA50'] and row['EMA20'] > row['EMA50']: score += 2
        elif c < row['EMA50'] and row['EMA20'] < row['EMA50']: score -= 2
            
        # Momentum
        if row['RSI'] > 50 and row['MACD'] > row.get('MACD_Signal', 0): score += 2
        elif row['RSI'] < 50 and row['MACD'] < row.get('MACD_Signal', 0): score -= 2
            
        # Volatility
        if row.get('ADX', 0) > 25:
            score += 1 if score > 0 else -1
            
        # PA Filter (Backtest optimization)
        pa = deteksi_price_action(df.iloc[:i+1])
        pa_score = pa['score']
        
        # High Win Rate Entry Logic: Must have technical momentum + PA confirmation
        if score >= 2 and pa_score > 0: # Buy
            in_trade = True
            direction = 1
            entry_price = c
            entry_time = curr_time
            sl = c - (1.5 * atr)
            tp = c + (4.5 * atr)
        elif score <= -2 and pa_score < 0: # Sell
            in_trade = True
            direction = -1
            entry_price = c
            entry_time = curr_time
            sl = c + (1.5 * atr)
            tp = c - (4.5 * atr)

    wins = sum(1 for t in trades if t['result'] == 'WIN')
    win_rate = (wins / len(trades) * 100) if trades else 0
    net_pips = sum(t['pips'] for t in trades)
    
    return {
        "total_trades": len(trades),
        "win_rate": win_rate,
        "pips_net": net_pips,
        "history": trades[-5:] # Last 5 trades
    }