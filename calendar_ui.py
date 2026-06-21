import streamlit as st
import requests
from datetime import datetime


CALENDAR_API = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# Indicators where a HIGHER actual is BAD for the currency (inverse correlation)
_INVERSE_INDICATORS = ("unemployment", "jobless", "claimant", "claims",
                       "inventories", "storage", "deficit")

# ── TRANSLATION MAP for common economic event titles ──
EVENT_TRANSLATE = {
    "CPI m/m": "Inflasi Bulanan (CPI)",
    "CPI y/y": "Inflasi Tahunan (CPI)",
    "Core CPI m/m": "Inflasi Inti Bulanan",
    "Core CPI y/y": "Inflasi Inti Tahunan",
    "PPI m/m": "Indeks Harga Produsen",
    "GDP q/q": "Pertumbuhan Ekonomi (PDB)",
    "GDP y/y": "Pertumbuhan Ekonomi Tahunan",
    "Unemployment Rate": "Tingkat Pengangguran",
    "Employment Change": "Perubahan Lapangan Kerja",
    "Non-Farm Employment Change": "Lapangan Kerja Non-Pertanian (NFP)",
    "FOMC Meeting Minutes": "Risalah Rapat The Fed (FOMC)",
    "FOMC Statement": "Pernyataan The Fed (FOMC)",
    "Federal Funds Rate": "Suku Bunga The Fed",
    "Interest Rate Decision": "Keputusan Suku Bunga",
    "Monetary Policy Statement": "Kebijakan Moneter",
    "Retail Sales m/m": "Penjualan Ritel Bulanan",
    "Core Retail Sales m/m": "Penjualan Ritel Inti",
    "Trade Balance": "Neraca Perdagangan",
    "Current Account": "Neraca Transaksi Berjalan",
    "PMI Manufacturing": "PMI Manufaktur",
    "PMI Services": "PMI Jasa",
    "Consumer Confidence": "Kepercayaan Konsumen",
    "Claimant Count Change": "Klaim Pengangguran Baru",
    "Average Hourly Earnings m/m": "Rata-rata Upah Per Jam",
    "ISM Manufacturing PMI": "PMI Manufaktur ISM",
    "ISM Services PMI": "PMI Jasa ISM",
    "Building Permits": "Izin Pembangunan",
    "Existing Home Sales": "Penjualan Rumah",
    "New Home Sales": "Penjualan Rumah Baru",
    "Crude Oil Inventories": "Stok Minyak Mentah",
    "Natural Gas Storage": "Stok Gas Alam",
    "BOJ Policy Rate": "Suku Bunga BOJ (Jepang)",
    "ECB Interest Rate Decision": "Suku Bunga ECB (Eropa)",
    "BOE Interest Rate Decision": "Suku Bunga BOE (Inggris)",
    "RBA Interest Rate Decision": "Suku Bunga RBA (Australia)",
    "BOC Interest Rate Decision": "Suku Bunga BOC (Kanada)",
    "SNB Interest Rate Decision": "Suku Bunga SNB (Swiss)",
    "RBNZ Interest Rate Decision": "Suku Bunga RBNZ (NZ)",
    "Inflation Rate y/y": "Tingkat Inflasi Tahunan",
    "Inflation Rate m/m": "Tingkat Inflasi Bulanan",
    "Industrial Production m/m": "Produksi Industri",
    "Preliminary GDP q/q": "PDB Awal Kuartalan",
    "Final GDP q/q": "PDB Final Kuartalan",
    "Flash Manufacturing PMI": "PMI Manufaktur Kilat",
    "Flash Services PMI": "PMI Jasa Kilat",
}


def _translate_event(title):
    """Translate event title to Indonesian using dictionary, fallback to original."""
    # Exact match
    if title in EVENT_TRANSLATE:
        return EVENT_TRANSLATE[title]
    # Partial match
    for eng, indo in EVENT_TRANSLATE.items():
        if eng.lower() in title.lower():
            return indo
    return title


def _parse_numeric(val):
    """Extract a float from values like '3.2%', '250K', '-0.3', '1.2M'. None if not parseable."""
    if val is None:
        return None
    s = str(val).strip().replace(",", "")
    if not s:
        return None
    if s.endswith("%"):
        s = s[:-1]
    mult = 1.0
    if s and s[-1] in "KkMmBbTt":
        mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[s[-1].upper()]
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return None


def _is_past_event(date_str):
    """True if the event datetime is already in the past."""
    try:
        dt = datetime.fromisoformat(date_str)
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        return dt < now
    except Exception:
        return False


def _event_effect(title, actual, forecast):
    """
    Interpret actual vs forecast → likely currency effect.
    Returns dict {badge, color, arrow, note} or None if not comparable numerically.
    """
    a = _parse_numeric(actual)
    f = _parse_numeric(forecast)
    if a is None or f is None:
        return None
    if abs(a - f) < 1e-9:
        return {"badge": "SESUAI", "color": "#888", "arrow": "➖",
                "note": "Hasil sesuai perkiraan — dampak ke pasar cenderung kecil."}
    higher = a > f
    inverse = any(k in title.lower() for k in _INVERSE_INDICATORS)
    bullish = (higher and not inverse) or (not higher and inverse)
    dir_txt = "lebih tinggi dari perkiraan" if higher else "lebih rendah dari perkiraan"
    if bullish:
        return {"badge": "BULLISH", "color": "#00ffcc", "arrow": "📈",
                "note": f"Aktual {dir_txt} → cenderung MENGUATKAN mata uang ini."}
    return {"badge": "BEARISH", "color": "#ff4b4b", "arrow": "📉",
            "note": f"Aktual {dir_txt} → cenderung MELEMAHKAN mata uang ini."}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_economic_calendar():
    """Fetch this week's economic calendar from ForexFactory (public API)."""
    try:
        resp = requests.get(CALENDAR_API, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Calendar fetch error: {e}")
    return []


def render_calendar_widget():
    """Render a compact economic calendar in the sidebar."""
    events = fetch_economic_calendar()
    if not events:
        st.caption("📅 Kalender ekonomi tidak tersedia")
        return

    flags = {"USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "JPY": "🇯🇵", "AUD": "🇦🇺",
             "CAD": "🇨🇦", "CHF": "🇨🇭", "NZD": "🇳🇿", "CNY": "🇨🇳"}

    # Filter HIGH impact
    high_impact = [e for e in events if e.get("impact", "").lower() == "high"]

    if not high_impact:
        st.caption("📅 Tidak ada event berdampak tinggi minggu ini ✓")
        return

    st.warning(f"⚠️ {len(high_impact)} EVENT BERDAMPAK TINGGI")
    for e in high_impact[:6]:
        title = _translate_event(e.get("title", "Unknown"))
        country = e.get("country", "")
        date_str = e.get("date", "")
        forecast = e.get("forecast", "") or "—"
        previous = e.get("previous", "") or "—"
        actual_raw = e.get("actual")
        flag = flags.get(country, "🌐")

        try:
            dt = datetime.fromisoformat(date_str)
            t_str = dt.strftime("%a %d · %H:%M")
        except Exception:
            t_str = date_str[:10] if date_str else "TBD"

        is_past = _is_past_event(date_str)
        if is_past and actual_raw not in (None, ""):
            eff = _event_effect(e.get("title", ""), actual_raw, forecast)
            arrow = eff["arrow"] if eff else "•"
            st.caption(f"{flag} **{title[:32]}**  \n{t_str} · {arrow} Aktual: **{actual_raw}** (perkiraan {forecast})")
        elif is_past:
            st.caption(f"{flag} **{title[:32]}**  \n{t_str} · ⏳ Menunggu rilis data aktual")
        else:
            st.caption(f"{flag} **{title[:32]}**  \n{t_str} · Perkiraan: {forecast} · Sebelumnya: {previous}")


def render_calendar_full():
    """Render full calendar view for a dedicated page/section."""
    st.markdown("""
        <div style="padding:20px 0 10px;">
            <p style="font-family:'Orbitron';font-size:20px;color:#ff4b4b;letter-spacing:4px;margin:0;">
                📅 KALENDER EKONOMI
            </p>
            <p style="color:#444;font-size:11px;margin:4px 0 0;">ForexFactory — Minggu Ini</p>
        </div>
    """, unsafe_allow_html=True)

    events = fetch_economic_calendar()
    if not events:
        st.info("Tidak dapat memuat data kalender ekonomi.")
        return

    # Impact filter
    impact_filter = st.radio("Filter Dampak:", ["SEMUA", "TINGGI", "SEDANG", "RENDAH"],
                              horizontal=True, label_visibility="collapsed")

    impact_map = {"TINGGI": "HIGH", "SEDANG": "MEDIUM", "RENDAH": "LOW"}
    if impact_filter != "SEMUA":
        eng_filter = impact_map.get(impact_filter, impact_filter)
        events = [e for e in events if e.get("impact", "").upper() == eng_filter]

    if not events:
        st.warning(f"Tidak ada event berdampak {impact_filter.lower()} ditemukan.")
        return

    impact_colors = {"High": "#ff4b4b", "Medium": "#FFD700", "Low": "#888", "Holiday": "#555"}
    impact_labels = {"High": "TINGGI", "Medium": "SEDANG", "Low": "RENDAH", "Holiday": "LIBUR"}
    flags = {"USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "JPY": "🇯🇵", "AUD": "🇦🇺",
             "CAD": "🇨🇦", "CHF": "🇨🇭", "NZD": "🇳🇿", "CNY": "🇨🇳"}

    released_count = 0
    for e in events:
        impact = e.get("impact", "Low")
        ic = impact_colors.get(impact, "#888")
        il = impact_labels.get(impact, impact)
        flag = flags.get(e.get("country", ""), "🌐")
        title = _translate_event(e.get("title", "Unknown"))
        date_str = e.get("date", "")
        forecast = e.get("forecast", "") or "—"
        previous = e.get("previous", "") or "—"
        actual_raw = e.get("actual")

        try:
            _d = datetime.fromisoformat(date_str)
            display_date = _d.strftime("%a %d %b")
            display_time = _d.strftime("%H:%M")
        except Exception:
            display_date = date_str[:10] if date_str else "TBD"
            display_time = ""

        is_past = _is_past_event(date_str)
        has_actual = actual_raw not in (None, "")
        eff = _event_effect(e.get("title", ""), actual_raw, forecast) if (is_past and has_actual) else None

        # Determine how to display the AKTUAL cell + status tag
        if has_actual:
            released_count += 1
            actual_disp = actual_raw
            actual_color = eff["color"] if eff else "#00ffcc"
            status_tag = f"<span style='font-size:8px;color:{actual_color};font-family:Orbitron;letter-spacing:1px;'>✓ RILIS</span>"
        elif is_past:
            actual_disp = "⏳"
            actual_color = "#777"
            status_tag = "<span style='font-size:8px;color:#777;font-family:Orbitron;letter-spacing:1px;'>⏳ MENUNGGU DATA</span>"
        else:
            actual_disp = "—"
            actual_color = "#555"
            status_tag = "<span style='font-size:8px;color:#555;font-family:Orbitron;letter-spacing:1px;'>🔜 AKAN DATANG</span>"

        effect_html = ""
        if eff:
            effect_html = f"""<div style="width:100%;margin-top:8px;padding-top:6px;border-top:1px dashed #1a1a1a;">
                <span style="font-family:'Orbitron';font-size:8px;color:{eff['color']};letter-spacing:1px;">{eff['arrow']} {eff['badge']}</span>
                <span style="font-size:10px;color:#999;margin-left:6px;">{eff['note']}</span>
            </div>"""

        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02);border:1px solid #1a1a1a;border-left:3px solid {ic};
                        border-radius:8px;padding:10px 14px;margin-bottom:6px;
                        display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
                <div style="flex:1;">
                    <span style="font-size:14px;">{flag}</span>
                    <span style="font-family:'Orbitron';font-size:9px;color:{ic};letter-spacing:1px;margin-left:6px;">
                        {il}
                    </span>
                    <br>
                    <span style="font-size:12px;color:#eee;font-weight:600;">{title}</span>
                    <br>
                    <span style="font-size:9px;color:#555;">{display_date} · {display_time}</span>
                    &nbsp; {status_tag}
                </div>
                <div style="display:flex;gap:14px;text-align:center;">
                    <div>
                        <span style="font-size:8px;color:#555;font-family:'Orbitron';">PERKIRAAN</span><br>
                        <span style="font-size:12px;color:#FFD700;font-family:'JetBrains Mono';">{forecast}</span>
                    </div>
                    <div>
                        <span style="font-size:8px;color:#555;font-family:'Orbitron';">SEBELUMNYA</span><br>
                        <span style="font-size:12px;color:#888;font-family:'JetBrains Mono';">{previous}</span>
                    </div>
                    <div>
                        <span style="font-size:8px;color:#555;font-family:'Orbitron';">AKTUAL</span><br>
                        <span style="font-size:13px;color:{actual_color};font-family:'JetBrains Mono';font-weight:700;">{actual_disp}</span>
                    </div>
                </div>
                {effect_html}
            </div>
        """, unsafe_allow_html=True)

    st.caption(f"Menampilkan {len(events)} event · {released_count} sudah rilis · Sumber: ForexFactory")
