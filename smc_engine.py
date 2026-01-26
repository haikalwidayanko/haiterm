import pandas as pd


def deteksi_smc_v10(df):
    """
    SMC Intelligence Engine:
    Mendeteksi Fair Value Gaps (FVG) sebagai jejak institusi/bank besar.
    Termasuk perhitungan Mid-Level (50%) untuk akurasi entry.
    """
    if df is None or len(df) < 5:
        return []

    fvg_zones = []
    # Kita cek 50 candle terakhir untuk mencari area ketidakseimbangan (Imbalance)
    # Gunakan copy agar tidak merusak dataframe asli
    subset = df.tail(50).copy()
    current_price = df['Close'].iloc[-1]
    atr_value = df['ATR'].iloc[-1] if 'ATR' in df.columns else 0

    # Loop mulai dari index ke-2 karena butuh data 3 candle berurutan
    for i in range(2, len(subset)):

        # --- 1. BULLISH FVG (Area Magnet untuk BUY) ---
        # Rumus: Low Candle Sekarang > High 2 Candle Lalu
        if subset['Low'].iloc[i] > subset['High'].iloc[i - 2]:
            top = subset['Low'].iloc[i]
            bottom = subset['High'].iloc[i - 2]
            mid = (top + bottom) / 2

            # Cek apakah FVG ini sudah tertutup (Mitigated) atau belum
            # Jika harga sekarang sudah turun menembus batas bawah FVG, dianggap 'Filled'
            status = "Unfilled" if current_price > bottom else "Filled"

            fvg_zones.append({
                'type': 'BULLISH FVG',
                'top': top,
                'bottom': bottom,
                'mid': mid,  # Harga entry "Golden" di tengah kotak
                'status': status,
                'strength': 'Strong' if (top - bottom) > (atr_value * 0.5) else 'Weak'
            })

        # --- 2. BEARISH FVG (Area Magnet untuk SELL) ---
        # Rumus: High Candle Sekarang < Low 2 Candle Lalu
        elif subset['High'].iloc[i] < subset['Low'].iloc[i - 2]:
            top = subset['Low'].iloc[i - 2]
            bottom = subset['High'].iloc[i]
            mid = (top + bottom) / 2

            # Jika harga sekarang sudah naik menembus batas atas FVG, dianggap 'Filled'
            status = "Unfilled" if current_price < top else "Filled"

            fvg_zones.append({
                'type': 'BEARISH FVG',
                'top': top,
                'bottom': bottom,
                'mid': mid,  # Harga entry "Golden" di tengah kotak
                'status': status,
                'strength': 'Strong' if (top - bottom) > (atr_value * 0.5) else 'Weak'
            })

    return fvg_zones