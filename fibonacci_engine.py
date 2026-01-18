import pandas as pd


def calculate_fibonacci_levels(df, period=100):
    """
    Mendeteksi Swing High/Low secara otomatis dan menghitung level Fibonacci Retracement.
    Formula:
    """
    # 1. Identifikasi Swing High & Swing Low dalam periode tertentu
    #
    recent_data = df.tail(period)
    swing_high = recent_data['High'].max()
    swing_low = recent_data['Low'].min()
    diff = swing_high - swing_low

    # 2. Kalkulasi Level Retracement (Standard Astronacci)
    # Formula: $$Level = High - (Percentage \times Diff)$$
    levels = {
        "0.0% (High)": swing_high,
        "23.6%": swing_high - (0.236 * diff),
        "38.2%": swing_high - (0.382 * diff),
        "50.0%": swing_high - (0.500 * diff),
        "61.8% (Golden)": swing_high - (0.618 * diff),
        "78.6%": swing_high - (0.786 * diff),
        "100.0% (Low)": swing_low
    }

    # 3. Kalkulasi Extension (Untuk Target Profit Jauh)
    extensions = {
        "161.8% EXT": swing_high + (0.618 * diff) if diff > 0 else swing_low - (0.618 * diff),
        "261.8% EXT": swing_high + (1.618 * diff) if diff > 0 else swing_low - (1.618 * diff)
    }

    return levels, extensions, swing_high, swing_low


def get_fibonacci_verdict(current_price, levels):
    """
    Memberikan vonis apakah harga sedang berada di area pantulan (Reversal Zone).
    """
    golden_ratio = levels["61.8% (Golden)"]
    # Toleransi area 0.5% untuk deteksi 'Touch'
    tolerance = golden_ratio * 0.0005

    if abs(current_price - golden_ratio) <= tolerance:
        return "⚠️ GOLDEN RATIO TOUCH: Potensi Reversal Tinggi!", "#00ffcc"
    elif current_price < levels["61.8% (Golden)"] and current_price > levels["78.6%"]:
        return "📥 BUYING ZONE (Deep Retracement)", "#ffa726"
    else:
        return "⚖️ PRICE IN TRANSIT", "#888"