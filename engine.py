import pandas as pd
import numpy as np


# --- 1. CORE TECHNICAL ENGINE ---
def hitung_indikator_lengkap(df):
    """
    Menghitung indikator teknikal utama: Trend, Momentum, Volatilitas, dan MACD.
    """
    if df is None or df.empty:
        return df

    df = df.copy()
    # Mengisi data kosong (linear interpolation)
    df = df.ffill().bfill()

    # A. TREND FOUNDATION (EMA)
    df['MA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['MA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['MA200'] = df['Close'].ewm(span=200, adjust=False).mean()

    # B. MOMENTUM (RSI 14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

    # C. MACD (DIBERESIN BIAR GAK NAME ERROR)
    #
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


# --- 2. MULTI-TIMEFRAME (MTF) CONFLUENCE ---
def check_mtf_alignment(df_15m, df_1h, df_4h):
    """Mengecek keselarasan tren di berbagai timeframe."""
    try:
        def get_direction(df):
            last = df.iloc[-1]
            if last['Close'] > last['MA50']: return 1
            if last['Close'] < last['MA50']: return -1
            return 0

        t15 = get_direction(df_15m)
        t1h = get_direction(df_1h)
        t4h = get_direction(df_4h)

        if t15 == t1h == t4h == 1:
            return "ALIGNED BULLISH", 2
        elif t15 == t1h == t4h == -1:
            return "ALIGNED BEARISH", -2
        else:
            return "MIXED / DIVERGENCE", 0
    except:
        return "DATA INCOMPLETE", 0


# --- 3. QUANTUM SCORING V10 (SINKRON DENGAN UI) ---
def get_detailed_scores_v10(df, macro_data, sentiment_score, mtf_bonus):
    """
    Menghitung skor Quantum dengan rincian audit yang sinkron dengan quantum_ui.py.
    """
    try:
        last = df.iloc[-1]
        p_now = float(last['Close'])

        # PILAR 1: STRUKTUR TREN (Max 4)
        if p_now > last['MA50'] > last['MA200']:
            s_trend = 4
        elif p_now < last['MA50'] < last['MA200']:
            s_trend = -4
        elif p_now > last['MA50']:
            s_trend = 2
        else:
            s_trend = -2

        # PILAR 2: RELATIVE MACRO (Max 2)
        dxy_rel = macro_data.get('dxy_rel', False)
        tnx_rel = macro_data.get('tnx_rel', False)

        # Logika: Bias Bullish jika USD Lemah
        usd_weak = (not dxy_rel) and (not tnx_rel)
        usd_strong = dxy_rel and tnx_rel
        s_macro = 2 if usd_weak else (-2 if usd_strong else 0)

        # PILAR 3: MOMENTUM (Max 2)
        if last['RSI'] < 35:
            s_mom = 2
        elif last['RSI'] > 65:
            s_mom = -2
        else:
            s_mom = 0

        # PILAR 4: SENTIMENT (Max 2)
        s_sent = int(sentiment_score * 2)

        # TOTAL SCORE
        total_final = max(-10, min(10, s_trend + s_macro + s_mom + s_sent + mtf_bonus))

        # RETURN FORMAT SESUAI UI
        return {
            "total": total_final,
            "details": {
                "trend": s_trend,
                "macro": s_macro,
                "momentum": s_mom,
                "sentiment": s_sent,
                "mtf_bonus": mtf_bonus
            }
        }
    except Exception as e:
        print(f"Scoring Error: {e}")
        return {
            "total": 0,
            "details": {"trend": 0, "macro": 0, "momentum": 0, "sentiment": 0, "mtf_bonus": 0}
        }


# --- 4. HELPER FUNCTIONS ---
def hitung_adx_manual(df, window=14):
    """Menghitung Average Directional Index untuk mengukur kekuatan tren."""
    df = df.copy()
    df['TR'] = pd.concat([
        df['High'] - df['Low'],
        abs(df['High'] - df['Close'].shift()),
        abs(df['Low'] - df['Close'].shift())
    ], axis=1).max(axis=1)

    df['+DM'] = df['High'].diff().clip(lower=0)
    df['-DM'] = df['Low'].diff().apply(lambda x: -x).clip(lower=0)

    tr_s = df['TR'].rolling(window).mean()
    di_p = 100 * (df['+DM'].rolling(window).mean() / tr_s)
    di_m = 100 * (df['-DM'].rolling(window).mean() / tr_s)

    dx = 100 * (abs(di_p - di_m) / (di_p + di_m + 1e-9))
    return dx.rolling(window).mean()


def calculate_fibonacci_levels(df):
    """
    Menghitung level Fibonacci Retracement berdasarkan
    High dan Low dalam periode data 60 hari terakhir.
    """
    #
    recent_data = df.tail(60)
    highest_high = recent_data['High'].max()
    lowest_low = recent_data['Low'].min()
    diff = highest_high - lowest_low

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
    """Deteksi sederhana Fair Value Gaps (FVG) untuk Smart Money Concepts."""
    fvg = []
    subset = df.tail(50)
    for i in range(2, len(subset)):
        # Bullish FVG
        if subset['Low'].iloc[i] > subset['High'].iloc[i - 2]:
            fvg.append({
                'type': 'BULL_FVG',
                'top': subset['Low'].iloc[i],
                'bottom': subset['High'].iloc[i - 2]
            })
        # Bearish FVG
        elif subset['High'].iloc[i] < subset['Low'].iloc[i - 2]:
            fvg.append({
                'type': 'BEAR_FVG',
                'top': subset['Low'].iloc[i - 2],
                'bottom': subset['High'].iloc[i]
            })
    return fvg