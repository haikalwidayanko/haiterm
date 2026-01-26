import pandas as pd
import yfinance as yf
import streamlit as st
import requests
from datetime import datetime
from gnews import GNews
from textblob import TextBlob


def send_telegram_alert(message):
    """Mengirim pesan ke Telegram menggunakan Bot API."""
    token = st.secrets["telegram_token"]
    chat_id = st.secrets["telegram_chat_id"]

    # Format URL untuk Telegram API
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Gagal kirim Telegram: {e}")

# --- 1. ASSET LIST (YAHOO STYLE) ---
def get_forex_list():
    """
    Daftar Ticker format Yahoo Finance.
    Forex pake =X, Gold/Silver pake =F.
    """
    return [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X",
        "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X",
        "GC=F",  # Gold Futures (Paling stabil untuk Fibonacci)
        "SI=F",  # Silver Futures
        "BTC-USD",  # Crypto
        "ETH-USD"
    ]


# --- 2. MACRO DATA ENGINE ---

def fetch_macro_data():
    """Mengambil data DXY dengan proteksi kegagalan download."""
    try:
        # Ganti ticker ke DX-Y.NYB biar lebih stabil
        dxy = yf.download("DX-Y.NYB", period="5d", interval="1d", progress=False)

        if not dxy.empty:
            # Ambil harga closing terakhir yang asli
            val = float(dxy['Close'].iloc[-1])
            prev = float(dxy['Close'].iloc[-2])
            return {
                "dxy_val": val,
                "dxy_rel": val > prev,  # Cek apakah naik dibanding kemarin
                "is_real": True  # Penanda data asli
            }

        # Kalau gagal, kasih tau di log
        print("⚠️ DXY Download Empty, using Fallback!")
        return {"dxy_val": 0.0, "dxy_rel": False, "is_real": False}

    except Exception as e:
        print(f"DXY Fetch Error: {e}")
        return {"dxy_val": 0.0, "dxy_rel": False, "is_real": False}

# --- 3. FOREX DATA ENGINE (STABLE VERSION) ---
@st.cache_data(ttl=30)
def fetch_forex_data(ticker, period="60d", interval="1h"):
    """
    Menarik data OHLC dari Yahoo Finance dengan proteksi Multi-Index.
    """
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)

        if data.empty:
            return None

        df = data.copy()

        # --- FIX: Rata-kan Multi-Index Yahoo (Solusi Error Format String) ---
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Repair data jika ada NaN (Forward Fill)
        df = df.ffill()

        # Pastikan kolom standar tersedia
        required_cols = ['Open', 'High', 'Low', 'Close']
        if all(col in df.columns for col in required_cols):
            return df
        else:
            return None

    except Exception as e:
        print(f"Yahoo Fetch Error: {e}")
        return None


# --- 4. NEWS & SENTIMENT ENGINE ---

def check_news_shield(ticker):
    """Mendeteksi berita High Impact (Red Flags)."""
    try:
        clean_name = ticker.replace("=X", "").replace("=F", "")
        google_news = GNews(language='en', period='12h', max_results=5)
        raw_news = google_news.get_news(f"{clean_name} forex news")

        red_flags = ["NFP", "FOMC", "CPI", "FED", "INTEREST RATE", "PAYROLLS"]
        detected = [n['title'] for n in raw_news if any(key in n['title'].upper() for key in red_flags)]
        return detected
    except:
        return []


def get_market_sentiment(ticker):
    """Menganalisis bias psikologi pasar dari berita."""
    try:
        clean_name = ticker.replace("=X", "").replace("=F", "")
        google_news = GNews(language='en', period='12h', max_results=5)
        raw_news = google_news.get_news(f"{clean_name} market sentiment")

        if not raw_news:
            return 0, "NEUTRAL", []

        score = 0
        for n in raw_news:
            pol = TextBlob(n['title']).sentiment.polarity
            score += 1 if pol > 0.1 else (-1 if pol < -0.1 else 0)

        label = "BULLISH" if score > 0 else ("BEARISH" if score < 0 else "NEUTRAL")
        val = 1 if score > 0 else (-1 if score < 0 else 0)

        return val, label, [n['title'] for n in raw_news[:3]]
    except:
        return 0, "NEUTRAL", []