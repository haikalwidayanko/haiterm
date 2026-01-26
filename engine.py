import pandas as pd
import numpy as np


# --- 1. CORE TECHNICAL ENGINE ---
def hitung_indikator_lengkap(df):
    """
    Menghitung indikator teknikal utama dengan proteksi data kosong.
    """
    if df is None or df.empty:
        return df

    df = df.copy()
    # Mengisi data kosong agar tidak merusak perhitungan MA/RSI
    df = df.ffill().bfill()

    # A. TREND FOUNDATION (EMA)
    df['MA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['MA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['MA200'] = df['Close'].ewm(span=200, adjust=False).mean()

    # B. MOMENTUM (RSI 14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    # Proteksi pembagian dengan nol (1e-9)
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

    # C. MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

    # D. VOLATILITY (ATR 14)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = ranges.max(axis=1).rolling(window=14).mean()

    # E. TREND STRENGTH (ADX)
    df['ADX'] = hitung_adx_manual(df)

    return df.fillna(0)


# --- 2. QUANTUM SCORING V10 (OPTIMIZED) ---
def get_detailed_scores_v10(df, macro, sentiment_score, fib_data, htf_bias=0, sent_reason=""):
    """
    Quantum Engine V10: Logic yang jauh lebih peka terhadap reversal dan narasi pasar.
    """
    if df.empty: return {"total": 0, "details": {}, "audit": {}}

    last = df.iloc[-1]
    p_now = last['Close']
    audit = {}

    # --- 1. LAYERED TREND LOGIC (Max +4 / Min -4) ---
    t_score = 0
    t_notes = []
    # Major Trend (EMA 200) - Bobot Paling Gede
    if p_now > last['MA200']:
        t_score += 2
        t_notes.append("Major Bullish (Price > EMA200)")
    else:
        t_score -= 2
        t_notes.append("Major Bearish (Price < EMA200)")

    # Medium & Short Confirmation
    if p_now > last['MA50']: t_score += 1
    if p_now > last['MA20']: t_score += 1

    audit['Trend'] = " | ".join(t_notes) if t_notes else "Mixed Trend Detection"

    # --- 2. SMART MOMENTUM (RSI vs Fibonacci Floor) ---
    m_score = 0
    rsi = last['RSI']
    golden_ratio = fib_data.get('61.8% (Golden)', 0)
    # Toleransi 0.1% untuk area Golden Ratio
    is_near_golden = abs(p_now - golden_ratio) / (golden_ratio + 1e-9) < 0.001

    if rsi > 70:
        m_score = 1
        audit['Momentum'] = f"RSI {rsi:.1f} (Overbought - Waspada Koreksi)"
    elif 50 < rsi <= 70:
        m_score = 2
        audit['Momentum'] = f"RSI {rsi:.1f} (Strong Bullish Momentum)"
    elif 30 <= rsi <= 50:
        m_score = -2
        audit['Momentum'] = f"RSI {rsi:.1f} (Bearish Pressure)"
    elif rsi < 30:
        # LOGIKA REVERSAL: Jika RSI murah + nempel di lantai Fibonacci
        if is_near_golden:
            m_score = 4  # Golden Reversal
            audit['Momentum'] = f"RSI {rsi:.1f} + Golden Floor (High Conviction Reversal!)"
        else:
            m_score = -1  # Falling Knife
            audit['Momentum'] = f"RSI {rsi:.1f} (Oversold - Belum Ada Lantai Tahanan)"

    # --- 3. MTF BONUS LOGIC (+2) ---
    mtf_final = 0
    # Bonus jika timeframe besar (HTF) searah dengan sinyal saat ini
    if htf_bias > 0 and (t_score + m_score) > 0:
        mtf_final = 2
        audit['MTF Bonus'] = "Big Boss Confirmed (HTF Aligned Bullish)"
    elif htf_bias < 0 and (t_score + m_score) < 0:
        mtf_final = 2
        audit['MTF Bonus'] = "Big Boss Confirmed (HTF Aligned Bearish)"
    else:
        audit['MTF Bonus'] = "No HTF Confluence (Timeframes Divergent)"

    # --- 4. MACRO DXY CORRELATION (+2 / -2) ---
    dxy_val = macro.get('dxy_val', 100)
    macro_score = 2 if dxy_val < 100 else -2
    audit['Macro'] = f"DXY {dxy_val:.2f} ({'Supportive' if dxy_val < 100 else 'Pressuring'} USD)"

    # --- 5. SENTIMENT NARRATIVE ---
    if sentiment_score > 0:
        audit['Sentiment'] = f"Bullish: {sent_reason}" if sent_reason else "Positive Sentiment Detected"
    elif sentiment_score < 0:
        audit['Sentiment'] = f"Bearish: {sent_reason}" if sent_reason else "Negative Sentiment Detected"
    else:
        audit['Sentiment'] = "Neutral Market Narrative"

    # TOTAL CALCULATION (Capped +/- 10)
    total = t_score + m_score + macro_score + sentiment_score + mtf_final
    total = max(min(total, 10), -10)

    return {
        "total": total,
        "details": {
            "Trend": t_score,
            "Macro": macro_score,
            "Momentum": m_score,
            "Sentiment": sentiment_score,
            "MTF Bonus": mtf_final
        },
        "audit": audit
    }


# --- 3. ANALYTICAL HELPERS ---
def hitung_adx_manual(df, window=14):
    """Menghitung kekuatan tren dengan filter stabilitas."""
    df = df.copy()
    df['TR'] = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] - df['Close'].shift()),
        abs(df['Low'] - df['Close'].shift())
    ], axis=1).max(axis=1)

    df['+DM'] = df['High'].diff().clip(lower=0)
    df['-DM'] = df['Low'].diff().apply(lambda x: -x).clip(lower=0)

    # Menghindari noise dengan rolling mean
    tr_s = df['TR'].rolling(window).mean() + 1e-9
    di_p = 100 * (df['+DM'].rolling(window).mean() / tr_s)
    di_m = 100 * (df['-DM'].rolling(window).mean() / tr_s)

    dx = 100 * (abs(di_p - di_m) / (di_p + di_m + 1e-9))
    return dx.rolling(window).mean()


def calculate_fibonacci_levels(df):
    """
    Versi Anti-Crash: Menghitung Fibonacci dengan proteksi pembagian nol.
    """
    if df is None or len(df) < 60:
        return {}

    recent_data = df.tail(60)
    highest_high = recent_data['High'].max()
    lowest_low = recent_data['Low'].min()
    diff = highest_high - lowest_low

    # PROTEKSI: Jika harga flat (High == Low), diff jadi 0.
    # Kita kasih nilai sekecil mungkin agar tidak division by zero.
    if diff == 0:
        diff = 1e-9

    return {
        '0% (Low)': lowest_low,
        '23.6%': highest_high - (diff * 0.236),
        '38.2%': highest_high - (diff * 0.382),
        '50.0%': highest_high - (diff * 0.5),
        '61.8% (Golden)': highest_high - (diff * 0.618),
        '78.6%': highest_high - (diff * 0.786),
        '100% (High)': highest_high
    }


def deteksi_smc_v10(df):
    """Deteksi Fair Value Gaps (FVG) untuk Smart Money Concepts."""
    fvg = []
    subset = df.tail(50)
    for i in range(2, len(subset)):
        if subset['Low'].iloc[i] > subset['High'].iloc[i - 2]:
            fvg.append({'type': 'BULL_FVG', 'top': subset['Low'].iloc[i], 'bottom': subset['High'].iloc[i - 2]})
        elif subset['High'].iloc[i] < subset['Low'].iloc[i - 2]:
            fvg.append({'type': 'BEAR_FVG', 'top': subset['Low'].iloc[i - 2], 'bottom': subset['High'].iloc[i]})
    return fvg