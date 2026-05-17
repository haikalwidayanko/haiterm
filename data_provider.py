import pandas as pd
import yfinance as yf
import streamlit as st
import requests
from datetime import datetime
from gnews import GNews
from textblob import TextBlob

# ============================================================
# ASSET REGISTRY
# ============================================================
FOREX_PAIRS = {
    # --- MAJOR (7) ---
    "EURUSD=X": {"name": "EUR/USD",         "group": "Major"},
    "GBPUSD=X": {"name": "GBP/USD",         "group": "Major"},
    "USDJPY=X": {"name": "USD/JPY",         "group": "Major"},
    "AUDUSD=X": {"name": "AUD/USD",         "group": "Major"},
    "USDCAD=X": {"name": "USD/CAD",         "group": "Major"},
    "USDCHF=X": {"name": "USD/CHF",         "group": "Major"},
    "NZDUSD=X": {"name": "NZD/USD",         "group": "Major"},
    # --- MINOR / CROSS (5) ---
    "EURGBP=X": {"name": "EUR/GBP",         "group": "Minor"},
    "EURJPY=X": {"name": "EUR/JPY",         "group": "Minor"},
    "GBPJPY=X": {"name": "GBP/JPY",         "group": "Minor"},
    "EURAUD=X": {"name": "EUR/AUD",         "group": "Minor"},
    "GBPAUD=X": {"name": "GBP/AUD",         "group": "Minor"},
    # --- METALS (3) ---
    "GC=F":     {"name": "XAU/USD (Gold)",   "group": "Metals"},
    "SI=F":     {"name": "XAG/USD (Silver)", "group": "Metals"},
    "HG=F":     {"name": "Copper",           "group": "Metals"},
    # --- ENERGY (2) ---
    "CL=F":     {"name": "Crude Oil (WTI)",  "group": "Energy"},
    "NG=F":     {"name": "Natural Gas",      "group": "Energy"},
    # --- AGRICULTURE (3) ---
    "ZW=F":     {"name": "Wheat",            "group": "Agriculture"},
    "KC=F":     {"name": "Coffee",           "group": "Agriculture"},
    "CC=F":     {"name": "Cocoa",            "group": "Agriculture"},
    # --- CRYPTO (5) ---
    "BTC-USD":  {"name": "Bitcoin (BTC)",     "group": "Crypto"},
    "ETH-USD":  {"name": "Ethereum (ETH)",    "group": "Crypto"},
    "SOL-USD":  {"name": "Solana (SOL)",      "group": "Crypto"},
    "AVAX-USD": {"name": "Avalanche (AVAX)",  "group": "Crypto"},
    "SUI20947-USD": {"name": "Sui (SUI)",      "group": "Crypto"},
}

TICKER_SEARCH_MAP = {
    "EURUSD=X": "EUR USD euro dollar forex",  "GBPUSD=X": "GBP USD pound dollar forex",
    "USDJPY=X": "USD JPY dollar yen forex",   "AUDUSD=X": "AUD USD australian dollar forex",
    "USDCAD=X": "USD CAD canadian dollar",    "USDCHF=X": "USD CHF swiss franc forex",
    "NZDUSD=X": "NZD USD new zealand forex",  "EURGBP=X": "EUR GBP euro pound",
    "EURJPY=X": "EUR JPY euro yen",           "GBPJPY=X": "GBP JPY pound yen",
    "EURAUD=X": "EUR AUD euro australian",    "GBPAUD=X": "GBP AUD pound australian",
    "GC=F":     "gold price XAU commodity",   "SI=F":     "silver price XAG commodity",
    "HG=F":     "copper price commodity",     
    "CL=F":     "crude oil WTI price",        
    "NG=F":     "natural gas price energy",   
    "ZW=F":     "wheat price agriculture",    
    "KC=F":     "coffee price commodity",
    "CC=F":     "cocoa price agriculture",
    "BTC-USD":  "bitcoin BTC crypto price",
    "ETH-USD":  "ethereum ETH crypto price",
    "SOL-USD":  "solana SOL crypto price",
    "AVAX-USD": "avalanche AVAX crypto defi",
    "SUI20947-USD": "sui SUI crypto blockchain",
}


def _translate_to_id(text):
    """Auto-translate text to Indonesian using free Google Translate API."""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "en", "tl": "id", "dt": "t", "q": text}
        r = requests.get(url, params=params, timeout=3)
        if r.status_code == 200:
            return r.json()[0][0][0]
    except Exception:
        pass
    return text


def _get_search_query(ticker):
    return TICKER_SEARCH_MAP.get(ticker, ticker.replace("=X", "").replace("=F", "").replace("-USD", ""))


def get_forex_list():
    return list(FOREX_PAIRS.keys())


def get_ticker_display_name(ticker):
    if ticker in FOREX_PAIRS:
        return FOREX_PAIRS[ticker]['name']
    return ticker.replace("=X", "").replace("=F", "")


def get_ticker_group(ticker):
    if ticker in FOREX_PAIRS:
        return FOREX_PAIRS[ticker]['group']
    if ticker in CRYPTO_PAIRS:
        return "Crypto"
    return "Unknown"


def send_telegram_alert(message):
    try:
        token = st.secrets["telegram_token"]
        chat_id = st.secrets["telegram_chat_id"]
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")


@st.cache_data(ttl=120, show_spinner=False)
def fetch_macro_data():
    try:
        dxy = yf.download("DX-Y.NYB", period="5d", interval="1d", progress=False, auto_adjust=True)
        if not dxy.empty:
            if isinstance(dxy.columns, pd.MultiIndex):
                dxy.columns = dxy.columns.get_level_values(0)
            close = dxy['Close']
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            val  = float(close.iloc[-1])
            prev = float(close.iloc[-2])
            return {"dxy_val": val, "dxy_rel": val > prev, "is_real": True}
    except Exception as e:
        print(f"DXY Fetch Error: {e}")
    return {"dxy_val": 0.0, "dxy_rel": False, "is_real": False}


@st.cache_data(ttl=60, show_spinner=False)
def fetch_forex_data(ticker, period="30d", interval="1h"):
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if data.empty:
            return None
        df = data.copy()
        # Flatten multi-index columns (yfinance v0.2+ returns MultiIndex even for single tickers)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # Remove any duplicate columns
        df = df.loc[:, ~df.columns.duplicated()]
        # Ensure OHLCV columns are Series (not DataFrames)
        required = ['Open', 'High', 'Low', 'Close']
        if not all(c in df.columns for c in required):
            return None
        for col in required + ['Volume']:
            if col in df.columns and isinstance(df[col], pd.DataFrame):
                df[col] = df[col].iloc[:, 0]
        df = df.ffill().bfill()
        return df
    except Exception as e:
        print(f"Fetch Error [{ticker}]: {e}")
        return None


@st.cache_data(ttl=60, show_spinner=False)
def fetch_crypto_data(ticker, period="30d", interval="1h"):
    return fetch_forex_data(ticker, period=period, interval=interval)


@st.cache_data(ttl=600, show_spinner=False)
def check_news_shield(ticker):
    """Cache 10 min — high-impact news events don't change by the second."""
    try:
        query = _get_search_query(ticker)
        google_news = GNews(language='en', period='12h', max_results=5)
        raw_news = google_news.get_news(f"{query} news")
        red_flags = ["NFP", "FOMC", "CPI", "FED", "INTEREST RATE", "PAYROLLS",
                     "ECB", "BOJ", "RBA", "BOE", "GDP", "EMPLOYMENT", "INFLATION",
                     "HACK", "CRASH", "BANKRUPT", "SEC", "REGULATION", "BAN"]
        return [n['title'] for n in raw_news if any(k in n['title'].upper() for k in red_flags)]
    except:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_market_sentiment(ticker):
    """Cache 5 min — GNews API is slow; sentiment doesn't flip every second."""
    try:
        query = _get_search_query(ticker)
        google_news = GNews(language='en', period='24h', max_results=8)
        raw_news = google_news.get_news(f"{query} market outlook")
        if not raw_news:
            return 0, "NEUTRAL", []
        score = 0
        for idx, n in enumerate(raw_news):
            pol = TextBlob(n['title']).sentiment.polarity
            w = 1.5 if idx < 3 else 1.0
            score += w if pol > 0.05 else (-w if pol < -0.05 else 0)
        if score >= 2:
            return (2 if score >= 4 else 1), "BULLISH", raw_news[:5]
        elif score <= -2:
            return (-2 if score <= -4 else -1), "BEARISH", raw_news[:5]
        return 0, "NEUTRAL", raw_news[:5]
    except:
        return 0, "NEUTRAL", []


@st.cache_data(ttl=300, show_spinner=False)
def fetch_ticker_news(ticker, max_results=8):
    try:
        query = _get_search_query(ticker)
        gn = GNews(language='en', period='7d', max_results=max_results)
        raw_news = gn.get_news(query) or []
        articles = []
        for n in raw_news:
            title = _translate_to_id(n.get('title', 'No Title'))
            source = n.get('publisher', {})
            source_name = source.get('title', 'Unknown') if isinstance(source, dict) else str(source)
            pol = TextBlob(title).sentiment.polarity
            articles.append({
                'title': title,
                'source': source_name,
                'published': n.get('published date', n.get('published', '')),
                'sentiment_score': pol,
                'sentiment_label': "BULLISH" if pol > 0.05 else ("BEARISH" if pol < -0.05 else "NEUTRAL"),
                'url': n.get('url', '#'),
            })
        return articles
    except Exception as e:
        print(f"News Fetch Error: {e}")
        return []


def get_market_sessions():
    import pytz
    now = datetime.now(pytz.utc)
    if now.weekday() >= 5:
        return ["CLOSED"], None, "MARKET CLOSED (WEEKEND)", "#ff4b4b"
        
    h = now.hour
    sessions = []
    if 0 <= h < 9:   sessions.append("TOKYO")
    if 7 <= h < 16:  sessions.append("LONDON")
    if 13 <= h < 22: sessions.append("NEW YORK")
    if not sessions:  sessions.append("SYDNEY")
    colors = {"TOKYO": "#FF6B6B", "LONDON": "#4ECDC4", "NEW YORK": "#45B7D1", "SYDNEY": "#96CEB4"}
    main = sessions[0]
    return sessions, None, " + ".join(sessions), colors.get(main, "#888")


@st.cache_data(ttl=120, show_spinner=False)
def get_mtf_scores(ticker, macro, si):
    """Fetch exact Quantum Score across 4 key timeframes for confluence scanner."""
    from engine import hitung_indikator_lengkap, get_detailed_scores_v12, calculate_fibonacci_levels
    tfs = ["15m", "1h", "4h", "1d"]
    scores = {}
    
    for tf in tfs:
        try:
            df = fetch_forex_data(ticker, period="30d", interval=tf)
            if df is not None and not df.empty:
                df_ind = hitung_indikator_lengkap(df)
                fib = calculate_fibonacci_levels(df_ind)
                
                htf_tf = "4h" if tf in ("15m", "1h") else ("1d" if tf == "4h" else "1wk")
                df_htf = fetch_forex_data(ticker, period="60d", interval=htf_tf)
                htf_bias = 0
                if df_htf is not None and not df_htf.empty:
                    df_htf = hitung_indikator_lengkap(df_htf)
                    htf_bias = 1 if df_htf.iloc[-1]['Close'] > df_htf.iloc[-1]['EMA50'] else -1

                res = get_detailed_scores_v12(df_ind, macro, si, fib, htf_bias)
                scores[tf] = res['total']
            else:
                scores[tf] = 0
        except:
            scores[tf] = 0
    return scores