import streamlit as st
from datetime import datetime
import pytz


def get_market_sessions():
    """
    Menghitung status operasional bursa forex utama berdasarkan waktu WIB (GMT+7)
    dan mendeteksi penutupan pasar saat akhir pekan (Weekend).
    """
    # Menggunakan timezone Jakarta untuk referensi WIB
    tz_jkt = pytz.timezone('Asia/Jakarta')
    now = datetime.now(tz_jkt)
    current_hour = now.hour
    current_day = now.weekday()  # 0:Senin, 5:Sabtu, 6:Minggu

    # Logika Weekend: Forex tutup dari Sabtu pagi (jam 04:00/05:00) hingga Senin pagi WIB
    # Untuk penyederhanaan terminal: Sabtu & Minggu dianggap tutup total
    is_weekend = current_day >= 5

    # Definisi Jam Operasional Bursa Utama (WIB)
    # Sydney: 05.00 - 14.00
    # Tokyo:  07.00 - 16.00
    # London: 14.00 - 23.00
    # New York: 19.00 - 04.00 (melewati tengah malam)
    sessions = {
        "SYDNEY": {"open": 5, "close": 14, "icon": "🇦🇺"},
        "TOKYO": {"open": 7, "close": 16, "icon": "🇯🇵"},
        "LONDON": {"open": 14, "close": 23, "icon": "🇬🇧"},
        "NEW YORK": {"open": 19, "close": 4, "icon": "🇺🇸"}
    }

    session_status = []
    for city, info in sessions.items():
        if is_weekend:
            is_open = False
        elif city == "NEW YORK":
            # Logika khusus NY karena operasionalnya melewati pergantian hari
            is_open = current_hour >= info["open"] or current_hour < info["close"]
        else:
            is_open = info["open"] <= current_hour < info["close"]

        status_text = "OPEN" if is_open else "CLOSED"
        status_color = "#00ffcc" if is_open else "#444444"

        session_status.append({
            "city": city,
            "status": status_text,
            "color": status_color,
            "icon": info["icon"]
        })

    # Menentukan Pesan Utama (Market Note)
    if is_weekend:
        note = "🛑 MARKET CLOSED (WEEKEND)"
        note_color = "#ff4b4b"
    elif 19 <= current_hour <= 23:
        note = "⚡ HIGH VOLATILITY (London/NY Overlap)"
        note_color = "#ff4b4b"
    elif 14 <= current_hour < 16:
        note = "⚡ MEDIUM VOLATILITY (Tokyo/London Overlap)"
        note_color = "#ffa726"
    else:
        note = "🟢 MARKET ACTIVE"
        note_color = "#00ffcc"

    return session_status, current_hour, note, note_color


def show_session_tracker():
    """
    Komponen UI untuk menampilkan status bursa pada dashboard.
    """
    statuses, hr, note, color = get_market_sessions()

    # Tampilan Status Utama (Note)
    st.markdown(f"""
        <div style="background: {color}15; border: 1px solid {color}44; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
            <span style="color: {color}; font-weight: 800; font-size: 13px; letter-spacing: 1px;">{note}</span>
        </div>
    """, unsafe_allow_html=True)

    # Grid 4 Kolom untuk Sesi Bursa
    cols = st.columns(4)
    for i, s in enumerate(statuses):
        with cols[i]:
            st.markdown(f"""
                <div style="text-align: center; background: #0a0a0a; padding: 10px; border-radius: 8px; border: 1px solid #222; border-bottom: 3px solid {s['color']};">
                    <div style="font-size: 10px; color: #666; margin-bottom: 5px;">{s['icon']} {s['city']}</div>
                    <div style="font-size: 12px; font-weight: 700; color: {s['color']};">
                        <span style="height: 6px; width: 6px; background-color: {s['color']}; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>
                        {s['status']}
                    </div>
                </div>
            """, unsafe_allow_html=True)