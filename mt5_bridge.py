"""
mt5_bridge.py — MetaTrader 5 Live Trading Bridge
Widayanko Terminal v2.0

Koneksi langsung ke MT5 terminal yang sudah terinstall.
Requires: pip install MetaTrader5  (Windows only)
"""

import json
import os
from typing import Optional

MT5_CONFIG_FILE = "mt5_config.json"
MT5_MAGIC = 202501  # Magic number untuk identifikasi order dari bot ini

# ── Symbol Mapping: yfinance ticker → MT5 symbol ─────────────
# Tiap broker bisa punya nama berbeda (ada yang pakai suffix 'm', '.', dll)
DEFAULT_SYMBOL_MAP = {
    # Majors
    "EURUSD=X": "EURUSD",
    "GBPUSD=X": "GBPUSD",
    "USDJPY=X": "USDJPY",
    "USDCHF=X": "USDCHF",
    "USDCAD=X": "USDCAD",
    "AUDUSD=X": "AUDUSD",
    "NZDUSD=X": "NZDUSD",
    # Crosses
    "EURJPY=X": "EURJPY",
    "GBPJPY=X": "GBPJPY",
    "EURGBP=X": "EURGBP",
    "AUDJPY=X": "AUDJPY",
    "EURAUD=X": "EURAUD",
    "GBPAUD=X": "GBPAUD",
    "GBPCHF=X": "GBPCHF",
    "EURCHF=X": "EURCHF",
    "CADJPY=X": "CADJPY",
    "NZDJPY=X": "NZDJPY",
    "EURCAD=X": "EURCAD",
    "GBPCAD=X": "GBPCAD",
    "AUDCAD=X": "AUDCAD",
    "AUDNZD=X": "AUDNZD",
    "AUDCHF=X": "AUDCHF",
    "NZDCAD=X": "NZDCAD",
    "NZDCHF=X": "NZDCHF",
    "CHFJPY=X": "CHFJPY",
    "EURNZD=X": "EURNZD",
    "GBPNZD=X": "GBPNZD",
    # Commodities
    "GC=F":     "XAUUSD",
    "XAUUSD=X": "XAUUSD",
    "SI=F":     "XAGUSD",
    "CL=F":     "USOIL",
    # Crypto
    "BTC-USD":  "BTCUSD",
    "ETH-USD":  "ETHUSD",
    "SOL-USD":  "SOLUSD",
    "AVAX-USD": "AVAXUSD",
    "SUI20947-USD": "SUIUSD",
    "XRP-USD":  "XRPUSD",
    "BNB-USD":  "BNBUSD",
    "ADA-USD":  "ADAUSD",
    "DOGE-USD": "DOGEUSD",
    "LINK-USD": "LINKUSD",
    "DOT-USD":  "DOTUSD",
    "LTC-USD":  "LTCUSD",
    "TRX-USD":  "TRXUSD",
}


# ============================================================
# CONFIG
# ============================================================

def load_mt5_config() -> dict:
    if not os.path.exists(MT5_CONFIG_FILE):
        return {
            "login": "",
            "server": "",
            "symbol_map": DEFAULT_SYMBOL_MAP,
            "symbol_suffix": "",  # e.g., "m" for EURUSDm brokers
        }
    with open(MT5_CONFIG_FILE, "r") as f:
        try:
            cfg = json.load(f)
            # Ensure symbol_map always has defaults for new pairs
            base = DEFAULT_SYMBOL_MAP.copy()
            base.update(cfg.get("symbol_map", {}))
            cfg["symbol_map"] = base
            return cfg
        except Exception:
            return {"login": "", "server": "", "symbol_map": DEFAULT_SYMBOL_MAP, "symbol_suffix": ""}


def save_mt5_config(config: dict):
    """Save config — password intentionally NOT saved to disk."""
    safe = {k: v for k, v in config.items() if k != "password"}
    with open(MT5_CONFIG_FILE, "w") as f:
        json.dump(safe, f, indent=2)


def get_mt5_symbol(ticker: str, config: dict = None) -> str:
    """Convert yfinance ticker to MT5 symbol name (with broker suffix)."""
    if config is None:
        config = load_mt5_config()
    symbol_map = config.get("symbol_map", DEFAULT_SYMBOL_MAP)
    suffix = config.get("symbol_suffix", "")
    base = symbol_map.get(ticker, ticker.replace("=X", "").replace("=F", "").replace("-", ""))
    return f"{base}{suffix}"


# ============================================================
# CONNECTION
# ============================================================

def is_mt5_installed() -> bool:
    try:
        import MetaTrader5  # noqa
        return True
    except ImportError:
        return False


def is_connected() -> bool:
    if not is_mt5_installed():
        return False
    try:
        import MetaTrader5 as mt5
        return mt5.account_info() is not None
    except Exception:
        return False


def connect(login: int, password: str, server: str) -> tuple:
    """
    Initialize MT5 dan login ke akun broker.
    Returns: (success: bool, message: str)
    """
    if not is_mt5_installed():
        return False, "❌ Package MetaTrader5 belum terinstall.\nJalankan: pip install MetaTrader5"

    import MetaTrader5 as mt5

    if not mt5.initialize():
        return False, f"❌ MT5 gagal initialize: {mt5.last_error()}\nPastikan MT5 terminal sudah terbuka."

    authorized = mt5.login(login=int(login), password=password, server=server)
    if not authorized:
        err = mt5.last_error()
        mt5.shutdown()
        return False, f"❌ Login gagal: {err}\nCek login, password, dan server name."

    info = mt5.account_info()
    if info is None:
        mt5.shutdown()
        return False, "❌ Login berhasil tapi gagal ambil info akun."

    return True, (
        f"✅ Terhubung ke **{info.server}**\n"
        f"Akun: #{info.login} — {info.name}\n"
        f"Balance: {info.balance:.2f} {info.currency} | Leverage: 1:{info.leverage}"
    )


def auto_connect() -> tuple:
    """
    Auto-connect tanpa input manual:
      1. Kalau sudah terhubung → langsung pakai.
      2. Kalau ada kredensial di st.secrets['mt5'] → auto-login.
      3. Kalau terminal MT5 sudah jalan & login → nempel saja (tanpa password).
    Returns: (success: bool, message: str)
    """
    if not is_mt5_installed():
        return False, "MetaTrader5 tidak terinstall"

    import MetaTrader5 as mt5

    # 1) Sudah terhubung?
    try:
        if mt5.account_info() is not None:
            return True, "Sudah terhubung"
    except Exception:
        pass

    # 2) Kredensial dari secrets.toml → auto-login
    try:
        import streamlit as st
        if "mt5" in st.secrets:
            s = st.secrets["mt5"]
            return connect(int(s["login"]), s["password"], s["server"])
    except Exception:
        pass

    # 3) Nempel ke terminal MT5 yang sedang berjalan & sudah login
    try:
        if mt5.initialize() and mt5.account_info() is not None:
            return True, "Terhubung ke terminal MT5 yang sedang berjalan"
        mt5.shutdown()
    except Exception:
        pass

    return False, "Tidak ada terminal MT5 aktif / belum login"


def disconnect():
    if not is_mt5_installed():
        return
    try:
        import MetaTrader5 as mt5
        mt5.shutdown()
    except Exception:
        pass


def get_account_info() -> Optional[dict]:
    """Ambil info akun MT5 saat ini."""
    if not is_mt5_installed():
        return None
    try:
        import MetaTrader5 as mt5
        info = mt5.account_info()
        if info is None:
            return None
        return {
            "login":        info.login,
            "name":         info.name,
            "server":       info.server,
            "balance":      round(info.balance, 2),
            "equity":       round(info.equity, 2),
            "margin":       round(info.margin, 2),
            "free_margin":  round(info.margin_free, 2),
            "margin_level": round(info.margin_level, 2) if info.margin_level else 0,
            "profit":       round(info.profit, 2),
            "currency":     info.currency,
            "leverage":     info.leverage,
        }
    except Exception as e:
        print(f"[MT5] get_account_info error: {e}")
        return None


# ============================================================
# ORDER MANAGEMENT
# ============================================================

def place_order(
    ticker: str,
    direction: str,
    lot: float,
    sl: float,
    tp: float,
    comment: str = "WidayankoBot",
    config: dict = None,
) -> tuple:
    """
    Kirim market order ke broker via MT5.
    Returns: (ticket: int | None, message: str)
    """
    if not is_mt5_installed():
        return None, "MetaTrader5 package tidak terinstall"
    if not is_connected():
        return None, "MT5 tidak terhubung. Silakan login dulu."

    import MetaTrader5 as mt5

    if config is None:
        config = load_mt5_config()

    symbol = get_mt5_symbol(ticker, config)

    # Pastikan symbol tersedia di broker
    if not mt5.symbol_select(symbol, True):
        return None, f"Symbol '{symbol}' tidak ditemukan di broker ini."

    tick = mt5.symbol_info_tick(symbol)
    sym_info = mt5.symbol_info(symbol)
    if tick is None or sym_info is None:
        return None, f"Gagal ambil data harga untuk {symbol}"

    # Sesuaikan lot dengan constraint broker
    vol_step = sym_info.volume_step or 0.01
    lot = round(round(lot / vol_step) * vol_step, 8)
    lot = max(sym_info.volume_min, min(lot, sym_info.volume_max))

    digits = sym_info.digits

    if direction == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid

    sl_rounded = round(sl, digits) if sl and sl > 0 else 0.0
    tp_rounded = round(tp, digits) if tp and tp > 0 else 0.0

    # Validate SL/TP distance (minimal stop level)
    stop_level = sym_info.trade_stops_level * sym_info.point
    if sl_rounded > 0:
        sl_dist = abs(price - sl_rounded)
        if sl_dist < stop_level:
            return None, (
                f"SL terlalu dekat dari harga. Min jarak: {stop_level:.5f}, "
                f"jarak SL saat ini: {sl_dist:.5f}"
            )

    base_request = {
        "action":    mt5.TRADE_ACTION_DEAL,
        "symbol":    symbol,
        "volume":    lot,
        "type":      order_type,
        "price":     price,
        "sl":        sl_rounded,
        "tp":        tp_rounded,
        "deviation": 20,
        "magic":     MT5_MAGIC,
        "comment":   comment[:31],
        "type_time": mt5.ORDER_TIME_GTC,
    }

    # Coba beberapa filling mode sesuai dukungan broker (bitmask: 1=FOK, 2=IOC).
    # Banyak broker hanya terima salah satu → fallback otomatis biar order tidak ketolak.
    fmask = getattr(sym_info, "filling_mode", 0) or 0
    candidates = []
    if fmask & 2:
        candidates.append(mt5.ORDER_FILLING_IOC)
    if fmask & 1:
        candidates.append(mt5.ORDER_FILLING_FOK)
    for fm in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
        if fm not in candidates:
            candidates.append(fm)

    last_msg = ""
    for fmode in candidates:
        req = dict(base_request, type_filling=fmode)
        result = mt5.order_send(req)
        if result is None:
            last_msg = f"order_send gagal: {mt5.last_error()}"
            continue
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            return result.order, (
                f"✅ Order dikirim! Ticket #{result.order} | "
                f"{direction} {lot} lot {symbol} @ {price:.{digits}f} (fill={fmode})"
            )
        # 10030 = TRADE_RETCODE_INVALID_FILL → mode tak didukung, coba mode lain
        if result.retcode == 10030:
            last_msg = f"filling mode {fmode} ditolak (10030)"
            continue
        # Error lain (harga, margin, dll) → berhenti, jangan ulang
        return None, f"Order ditolak broker (retcode {result.retcode}): {result.comment}"

    return None, f"Order gagal di semua filling mode. {last_msg}"


def symbol_exists(ticker: str, config: dict = None) -> bool:
    """Cek apakah symbol (hasil mapping) tersedia di broker. True kalau tak bisa diverifikasi."""
    if not is_mt5_installed() or not is_connected():
        return True  # tidak bisa verifikasi → jangan blokir
    try:
        import MetaTrader5 as mt5
        if config is None:
            config = load_mt5_config()
        return mt5.symbol_info(get_mt5_symbol(ticker, config)) is not None
    except Exception:
        return True


def close_position(ticket: int) -> tuple:
    """
    Tutup posisi MT5 berdasarkan ticket.
    Returns: (success: bool, message: str)
    """
    if not is_mt5_installed():
        return False, "MetaTrader5 package tidak terinstall"
    if not is_connected():
        return False, "MT5 tidak terhubung"

    import MetaTrader5 as mt5

    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return False, f"Posisi ticket #{ticket} tidak ditemukan (mungkin sudah tertutup)"

    pos = positions[0]
    sym = pos.symbol
    vol = pos.volume

    tick = mt5.symbol_info_tick(sym)
    if tick is None:
        return False, f"Gagal ambil harga untuk close {sym}"

    if pos.type == mt5.POSITION_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       sym,
        "volume":       vol,
        "type":         order_type,
        "position":     ticket,
        "price":        price,
        "deviation":    20,
        "magic":        MT5_MAGIC,
        "comment":      "WidayankoBot_Close",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        err = result.comment if result else str(mt5.last_error())
        return False, f"Gagal close ticket #{ticket}: {err}"

    return True, f"✅ Posisi #{ticket} {sym} berhasil ditutup @ {price}"


def close_all_positions() -> tuple:
    """Tutup SEMUA posisi yang dibuka bot ini (magic number cocok). Return (jumlah, pesan)."""
    if not is_connected():
        return 0, "MT5 tidak terhubung"
    positions = get_open_positions()
    if not positions:
        return 0, "Tidak ada posisi terbuka"
    n = 0
    for p in positions:
        ok, _ = close_position(p["ticket"])
        if ok:
            n += 1
    return n, f"✅ {n}/{len(positions)} posisi ditutup"


def get_open_positions(config: dict = None) -> list:
    """
    Ambil semua posisi OPEN yang dibuka oleh bot ini (filter by magic number).
    """
    if not is_mt5_installed() or not is_connected():
        return []
    try:
        import MetaTrader5 as mt5
        positions = mt5.positions_get()
        if not positions:
            return []

        result = []
        for p in positions:
            if p.magic != MT5_MAGIC:
                continue
            result.append({
                "ticket":     p.ticket,
                "symbol":     p.symbol,
                "direction":  "BUY" if p.type == 0 else "SELL",
                "volume":     p.volume,
                "open_price": p.price_open,
                "current":    p.price_current,
                "sl":         p.sl,
                "tp":         p.tp,
                "profit":     round(p.profit, 2),
                "swap":       round(p.swap, 2),
                "open_time":  p.time,
                "comment":    p.comment,
            })
        return result
    except Exception as e:
        print(f"[MT5] get_open_positions error: {e}")
        return []


def get_trade_history(days: int = 7) -> list:
    """Ambil history trade yang sudah tertutup (untuk rekonsiliasi)."""
    if not is_mt5_installed() or not is_connected():
        return []
    try:
        import MetaTrader5 as mt5
        from datetime import datetime, timedelta
        date_from = datetime.now() - timedelta(days=days)
        deals = mt5.history_deals_get(date_from, datetime.now())
        if not deals:
            return []
        result = []
        for d in deals:
            if d.magic != MT5_MAGIC:
                continue
            if d.entry == mt5.DEAL_ENTRY_OUT:  # Only closed deals
                result.append({
                    "ticket":      d.order,
                    "position_id": d.position_id,
                    "symbol":      d.symbol,
                    "direction":   "BUY" if d.type == mt5.DEAL_TYPE_BUY else "SELL",
                    "volume":      d.volume,
                    "price":       d.price,
                    "profit":      round(d.profit, 2),
                    "swap":        round(d.swap, 2),
                    "time":        d.time,
                    "comment":     d.comment,
                })
        return result
    except Exception as e:
        print(f"[MT5] get_trade_history error: {e}")
        return []
