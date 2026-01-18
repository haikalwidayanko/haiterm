from datetime import datetime, timedelta


def get_astrology_status():
    """
    Menghitung fase bulan tanpa library eksternal (Math Based).
    Siklus Sinodik Bulan: ~29.53 hari.
    """
    # Referensi New Moon yang diketahui (11 Jan 2024)
    ref_new_moon = datetime(2024, 1, 11, 11, 57)
    now = datetime.now()

    # Selisih hari dari referensi
    diff = (now - ref_new_moon).total_seconds() / 86400
    # Posisi dalam siklus (0 - 29.53)
    cycle_pos = diff % 29.530588853

    # Menentukan Fase Terdekat
    if cycle_pos < 1.0 or cycle_pos > 28.5:
        phase = "NEW MOON (Potential Low)"
        days_to = 0
    elif 13.7 < cycle_pos < 15.8:
        phase = "FULL MOON (Potential High)"
        days_to = 0
    else:
        # Hitung sisa hari ke event terdekat
        if cycle_pos < 14.7:
            phase = "Waxing (Menuju Full Moon)"
            days_to = round(14.7 - cycle_pos)
        else:
            phase = "Waning (Menuju New Moon)"
            days_to = round(29.5 - cycle_pos)

    # Status Mercury (Simulasi Periodik - Merkurius Retrograde tiap ~4 bulan)
    # Untuk kejelasan, kita pakai indikator volatilitas umum
    is_volatile_season = 13 < cycle_pos < 16 or cycle_pos < 2 or cycle_pos > 28

    return {
        "next_event": phase,
        "days_left": days_to,
        "mercury_status": "HIGH VOLATILITY" if is_volatile_season else "STABLE MARKET",
        "intensity": "CRITICAL" if days_to <= 1 else "NORMAL",
        "cycle_percent": (cycle_pos / 29.53) * 100
    }