"""
auto_trader.py — Auto Trade Simulator Engine
Widayanko Terminal v2.0

Sistem paper trading otomatis yang:
1. Membaca profil user (modal, lot size, pairs, threshold)
2. Scan market pakai Quantum V12 Engine yang sudah ada
3. Otomatis place order simulasi jika sinyal valid
4. Hitung PnL berdasarkan price data real (yfinance)
5. Auto-close trade jika SL/TP kena (historis akurat candle-by-candle)
6. Kirim notifikasi Telegram saat order dibuka atau ditutup (SL/TP/Manual)
"""

import json
import os
import uuid
import pytz
from datetime import datetime
from typing import Optional

# ── Storage ──────────────────────────────────────────────────
PROFILES_FILE  = "auto_profiles.json"
SIM_TRADES_FILE = "sim_trades.json"
tz_jkt = pytz.timezone("Asia/Jakarta")

LOT_PRESETS = {
    "0.001 (Nano/Micro Account)": 0.001,
    "0.01 (Micro Lot)":           0.01,
    "0.1  (Mini Lot)":            0.1,
    "1.0  (Standard Lot)":        1.0,
    "Custom":                     None,
}

# Pip value per lot (standard 100k) for major forex
# For commodities / crypto these are approximate
PIP_VALUE_PER_LOT = {
    "default": 10.0,   # $10 per pip per standard lot (major USD pairs)
    "JPY":     9.0,    # JPY pairs slightly different
    "CRYPTO":  1.0,    # Per USD move per lot
    "COMMO":   1.0,    # Per point move per lot
}


# ============================================================
# PIP / SIZING / MARKET HELPERS
# ============================================================

def _pip_mult(ticker: str) -> int:
    """Price-difference → pips multiplier."""
    if "-USD" in ticker:        # crypto
        return 1
    if "JPY" in ticker:
        return 100
    if ticker.endswith("=F"):   # gold / silver / oil
        return 1
    return 10000


# Per-lot USD value untuk komoditas (perkiraan kontrak standar CFD).
# Penting untuk risk sizing supaya lot tidak meledak. Untuk LIVE, lot tetap
# di-clamp ke batas broker, tapi nilai ini menjaga estimasi risiko tetap waras.
COMMODITY_PIP_VALUE = {
    "GC=F": 100.0,   # Gold (XAUUSD): ~100 oz/lot → $1 gerak = ~$100/lot
    "SI=F": 50.0,    # Silver (XAGUSD): perkiraan konservatif
    "CL=F": 10.0,    # Crude Oil (WTI): perkiraan konservatif
}


def _pip_value_per_lot(ticker: str) -> float:
    """Approx USD value per pip per 1.0 lot."""
    if "-USD" in ticker:
        return PIP_VALUE_PER_LOT["CRYPTO"]
    if "JPY" in ticker:
        return PIP_VALUE_PER_LOT["JPY"]
    if ticker.endswith("=F"):
        return COMMODITY_PIP_VALUE.get(ticker, PIP_VALUE_PER_LOT["COMMO"])
    return PIP_VALUE_PER_LOT["default"]


def calc_position_size(capital, risk_percent, sl_price_distance, ticker, lot_fallback=0.01, max_lot=5.0):
    """
    Lot berdasarkan risiko: risk_amount / (sl_pips × pip_value_per_lot).
    Dibatasi minimal 0.01 lot dan maksimal max_lot (safety net). Fallback kalau tak valid.
    """
    try:
        risk_amount  = float(capital) * (float(risk_percent) / 100.0)
        sl_pips      = abs(sl_price_distance) * _pip_mult(ticker)
        risk_per_lot = sl_pips * _pip_value_per_lot(ticker)
        if risk_per_lot <= 0 or risk_amount <= 0:
            return lot_fallback
        lot = risk_amount / risk_per_lot
        return min(max(round(lot, 2), 0.01), max_lot)
    except Exception:
        return lot_fallback


def _is_market_open(ticker: str) -> bool:
    """Crypto 24/7. Forex/komoditas tutup di akhir pekan (perkiraan, basis UTC)."""
    if "-USD" in ticker:
        return True
    import pytz as _pytz
    now = datetime.now(_pytz.utc)
    wd, h = now.weekday(), now.hour   # Mon=0 .. Sun=6
    if wd == 5:                       # Sabtu
        return False
    if wd == 6 and h < 21:            # Minggu sebelum market buka (~21:00 UTC)
        return False
    if wd == 4 and h >= 21:           # Jumat setelah market tutup
        return False
    return True


# ============================================================
# CIRCUIT BREAKER / RISK GUARDS
# ============================================================

def get_today_realized_pnl(profile_id: str) -> float:
    """Total realized PnL (USD) untuk trade profil ini yang ditutup HARI INI (WIB)."""
    today = datetime.now(tz_jkt).strftime("%Y-%m-%d")
    total = 0.0
    for t in _load_sim_trades():
        if t.get("profile_id") != profile_id:
            continue
        if t.get("status") not in ("WIN", "LOSS", "BE"):
            continue
        if (t.get("closed_at", "") or "")[:10] == today:
            total += t.get("pnl_usd", 0) or 0
    return round(total, 2)


def get_loss_streak(profile_id: str) -> int:
    """Jumlah LOSS beruntun dihitung dari trade paling baru ditutup."""
    closed = [t for t in _load_sim_trades()
              if t.get("profile_id") == profile_id and t.get("status") in ("WIN", "LOSS", "BE")]
    closed.sort(key=lambda x: (x.get("closed_at", "") or ""), reverse=True)
    streak = 0
    for t in closed:
        if t.get("status") == "LOSS":
            streak += 1
        else:
            break
    return streak


def check_circuit_breaker(profile: dict) -> tuple:
    """
    Cek apakah auto-trade boleh jalan.
    Return (allowed: bool, reason: str).
    """
    capital   = profile.get("capital", 1000)
    max_dd    = profile.get("max_daily_loss_pct", 5.0)
    max_strk  = profile.get("max_loss_streak", 4)

    today_pnl = get_today_realized_pnl(profile["id"])
    loss_limit = -abs(capital * max_dd / 100.0)
    if today_pnl <= loss_limit:
        return False, f"🛑 Rugi harian ${today_pnl:.2f} ≥ batas ${loss_limit:.2f} — auto-trade dihentikan hari ini."

    streak = get_loss_streak(profile["id"])
    if streak >= max_strk:
        return False, f"🛑 {streak} LOSS beruntun ≥ batas {max_strk} — auto-trade dijeda."

    return True, ""


# ============================================================
# LOCAL FILE I/O
# ============================================================

def _load_profiles() -> list:
    if not os.path.exists(PROFILES_FILE):
        return []
    with open(PROFILES_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def _save_profiles(data: list):
    with open(PROFILES_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _load_sim_trades() -> list:
    if not os.path.exists(SIM_TRADES_FILE):
        return []
    with open(SIM_TRADES_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def _save_sim_trades(data: list):
    with open(SIM_TRADES_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


# ============================================================
# PROFILE MANAGEMENT
# ============================================================

def create_profile(
    owner: str,
    name: str,
    capital: float,
    lot_size: float,
    pairs: list,
    min_q_score: int = 8,
    max_open_trades: int = 3,
    sl_atr_mult: float = 1.5,
    tp_atr_mult: float = 4.5,
    use_risk_sizing: bool = True,
    risk_percent: float = 1.0,
    max_daily_loss_pct: float = 5.0,
    max_loss_streak: int = 4,
    live_mode: bool = False,
) -> dict:
    """Buat profil auto trading baru."""
    profiles = _load_profiles()
    now = datetime.now(tz_jkt).isoformat()

    profile = {
        "id":             str(uuid.uuid4())[:8],
        "owner":          owner,
        "name":           name,
        "capital":        float(capital),
        "lot_size":       float(lot_size),
        "pairs":          pairs,
        "min_q_score":    int(min_q_score),
        "max_open_trades": int(max_open_trades),
        "sl_atr_mult":    float(sl_atr_mult),
        "tp_atr_mult":    float(tp_atr_mult),
        # Risk management
        "use_risk_sizing":    bool(use_risk_sizing),   # lot dihitung dari risk% × modal
        "risk_percent":       float(risk_percent),     # % modal yang dirisiko per trade
        "max_daily_loss_pct": float(max_daily_loss_pct),
        "max_loss_streak":    int(max_loss_streak),
        "is_active":      True,
        "live_mode":      bool(live_mode),  # False = sim only, True = kirim ke MT5 juga
        "created_at":     now,
        "last_scan_at":   None,
        # Running totals
        "total_trades":   0,
        "total_wins":     0,
        "total_losses":   0,
        "net_pips":       0.0,
        "net_pnl_usd":    0.0,
    }

    profiles.append(profile)
    _save_profiles(profiles)
    return profile


def get_profiles(owner: str) -> list:
    """Ambil semua profil milik user."""
    return [p for p in _load_profiles() if p.get("owner") == owner]


def get_profile_by_id(profile_id: str) -> Optional[dict]:
    for p in _load_profiles():
        if p["id"] == profile_id:
            return p
    return None


def update_profile(profile_id: str, **kwargs) -> bool:
    profiles = _load_profiles()
    for p in profiles:
        if p["id"] == profile_id:
            for k, v in kwargs.items():
                p[k] = v
            _save_profiles(profiles)
            return True
    return False


def delete_profile(profile_id: str) -> bool:
    profiles = _load_profiles()
    new_profiles = [p for p in profiles if p["id"] != profile_id]
    if len(new_profiles) == len(profiles):
        return False
    _save_profiles(new_profiles)
    # Also delete related sim trades
    trades = _load_sim_trades()
    trades = [t for t in trades if t.get("profile_id") != profile_id]
    _save_sim_trades(trades)
    return True


def toggle_profile(profile_id: str) -> bool:
    """Toggle ON/OFF profil. Return new is_active state."""
    profiles = _load_profiles()
    for p in profiles:
        if p["id"] == profile_id:
            p["is_active"] = not p.get("is_active", True)
            _save_profiles(profiles)
            return p["is_active"]
    return False


# ============================================================
# SIM TRADE MANAGEMENT
# ============================================================

def get_sim_trades(profile_id: str, status_filter: str = None) -> list:
    """Ambil semua sim trade untuk sebuah profil."""
    trades = _load_sim_trades()
    result = [t for t in trades if t.get("profile_id") == profile_id]
    if status_filter:
        result = [t for t in result if t.get("status") == status_filter]
    return sorted(result, key=lambda x: x.get("opened_at", ""), reverse=True)


def get_all_open_sim_trades(owner: str) -> list:
    """Ambil semua trade OPEN dari semua profil milik owner."""
    profiles = get_profiles(owner)
    profile_ids = {p["id"] for p in profiles}
    trades = _load_sim_trades()
    return [t for t in trades if t.get("profile_id") in profile_ids and t.get("status") == "OPEN"]


def _fmt_p(v: float, ticker: str = "") -> str:
    """Format price untuk Telegram message."""
    if v is None or v == 0:
        return "—"
    if v > 100:
        return f"{v:,.3f}"
    return f"{v:,.5f}"


def _send_order_telegram(trade: dict):
    """Kirim notif Telegram saat sim order dibuka."""
    try:
        from data_provider import send_telegram_alert
        d   = trade['direction']
        p   = trade['pair_name']
        lot = trade['lot_size']
        tkr = trade['ticker']
        arrow = "🟢 BUY" if d == "BUY" else "🔴 SELL"
        msg = (
            f"🤖 *AUTO TRADE SIM — ORDER DIBUKA*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Pair: *{p}*\n"
            f"📌 Arah: *{arrow}*\n"
            f"💰 Entry: `{_fmt_p(trade['entry_price'], tkr)}`\n"
            f"🛑 SL:    `{_fmt_p(trade['sl'], tkr)}`\n"
            f"🎯 TP2:   `{_fmt_p(trade['tp2'], tkr)}`\n"
            f"📦 Lot:   {lot}\n"
            f"⚡ Q-Score: {trade.get('q_score', 0):+} | Conf: {trade.get('confidence', 0)}%\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Profil: {trade.get('profile_name', '')}\n"
            f"⏰ {trade.get('opened_at_str', '')}"
        )
        send_telegram_alert(msg)
    except Exception as e:
        print(f"[AUTO TRADER] Telegram open order error: {e}")


def _send_close_telegram(trade: dict, result: str, exit_price: float, pips: float, pnl_usd: float, reason: str):
    """Kirim notif Telegram saat sim trade ditutup."""
    try:
        from data_provider import send_telegram_alert
        d   = trade['direction']
        p   = trade['pair_name']
        tkr = trade['ticker']
        res_icon = "✅ WIN" if result == "WIN" else ("❌ LOSS" if result == "LOSS" else "⚖️ BE")
        pnl_sign = "+" if pnl_usd >= 0 else ""
        pips_sign = "+" if pips >= 0 else ""
        reason_map = {
            "TP2_HIT": "Target Profit (TP2) Kena",
            "SL_HIT":  "Stop Loss Kena",
            "MANUAL_CLOSE": "Ditutup Manual",
        }
        reason_str = reason_map.get(reason, reason)
        msg = (
            f"🤖 *AUTO TRADE SIM — TRADE DITUTUP*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{res_icon} | *{p}* ({d})\n"
            f"📌 Alasan: {reason_str}\n"
            f"💰 Entry: `{_fmt_p(trade['entry_price'], tkr)}` → Exit: `{_fmt_p(exit_price, tkr)}`\n"
            f"📈 Pips:  {pips_sign}{pips:.1f} pips\n"
            f"💵 PnL:   {pnl_sign}${pnl_usd:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Profil: {trade.get('profile_name', '')}\n"
            f"⏰ Ditutup: {datetime.now(tz_jkt).strftime('%Y-%m-%d %H:%M WIB')}"
        )
        send_telegram_alert(msg)
    except Exception as e:
        print(f"[AUTO TRADER] Telegram close trade error: {e}")


def _place_sim_order(
    profile: dict,
    ticker: str,
    pair_name: str,
    direction: str,
    entry_price: float,
    sl: float,
    tp1: float,
    tp2: float,
    tp3: float,
    q_score: int,
    confidence: int,
    atr: float,
    score_details: dict = None,
    score_audit: dict = None,
    ai_reasoning: list = None,
    pa_signal: str = "",
    lot_override: float = None,
) -> dict:
    """Buat sim trade baru dan kirim notif Telegram."""
    trades = _load_sim_trades()
    now = datetime.now(tz_jkt)

    lot = lot_override if (lot_override and lot_override > 0) else profile["lot_size"]

    trade = {
        "id":           str(uuid.uuid4())[:8],
        "profile_id":   profile["id"],
        "owner":        profile["owner"],
        "profile_name": profile["name"],
        "ticker":       ticker,
        "pair_name":    pair_name,
        "direction":    direction,      # "BUY" or "SELL"
        "lot_size":     lot,
        "capital":      profile["capital"],
        "entry_price":  entry_price,
        "sl":           sl,
        "tp1":          tp1,
        "tp2":          tp2,
        "tp3":          tp3,
        "atr":          atr,
        "q_score":      q_score,
        "confidence":   confidence,
        "status":       "OPEN",
        "exit_price":   None,
        "pips_result":  None,
        "pnl_usd":      None,
        "close_reason": None,
        "closed_at":    None,
        "opened_at":    now.isoformat(),
        "opened_at_str": now.strftime("%Y-%m-%d %H:%M WIB"),
        # MT5 live trade info
        "mt5_ticket":   None,
        "mt5_symbol":   None,
        "is_live":      False,
        # Snapshot analisis saat entry — untuk trade review
        "entry_score_details": score_details or {},
        "entry_score_audit":   score_audit or {},
        "entry_ai_reasoning":  ai_reasoning or [],
        "entry_pa_signal":     pa_signal,
    }

    trades.append(trade)
    _save_sim_trades(trades)

    # ── Kirim ke MT5 jika profil live_mode aktif ──────────────
    if profile.get("live_mode") and profile.get("is_active"):
        try:
            from mt5_bridge import place_order, load_mt5_config, get_mt5_symbol, is_connected
            if is_connected():
                cfg = load_mt5_config()
                ticket, msg = place_order(
                    ticker=ticker,
                    direction=direction,
                    lot=lot,
                    sl=sl,
                    tp=tp2,
                    comment=f"W-{trade['id']}",
                    config=cfg,
                )
                if ticket:
                    # Update trade dengan ticket MT5
                    for t in trades:
                        if t["id"] == trade["id"]:
                            t["mt5_ticket"] = ticket
                            t["mt5_symbol"] = get_mt5_symbol(ticker, cfg)
                            t["is_live"] = True
                            break
                    _save_sim_trades(trades)
                    trade["mt5_ticket"] = ticket
                    trade["is_live"] = True
                    print(f"[MT5] {msg}")
                else:
                    print(f"[MT5] Order gagal: {msg}")
            else:
                print("[MT5] Live mode aktif tapi MT5 tidak terhubung — trade disimpan sebagai sim")
        except Exception as e:
            print(f"[MT5] place_order error: {e}")

    # Update last activity timestamp. (total_trades is derived from the actual
    # trade list in get_profile_stats, so we don't increment a stale counter here —
    # doing so undercounted when multiple orders were placed in one scan.)
    update_profile(profile["id"], last_scan_at=now.isoformat())

    # Kirim notif Telegram
    _send_order_telegram(trade)

    return trade


def _close_sim_trade(trade: dict, result: str, exit_price: float, pips: float, reason: str,
                     pnl_override: float = None, close_mt5: bool = True):
    """
    Tutup trade simulasi, hitung PnL, dan kirim notif Telegram.
    pnl_override : pakai PnL aktual dari broker (rekonsiliasi MT5) alih-alih hitung sendiri.
    close_mt5    : kirim perintah close ke MT5 (False kalau posisi sudah tertutup di broker).
    """
    trades = _load_sim_trades()
    lot_size = trade.get("lot_size", 0.01)
    closed_at = datetime.now(tz_jkt).strftime("%Y-%m-%d %H:%M WIB")

    # Calculate PnL in USD
    ticker = trade.get("ticker", "")

    if pnl_override is not None:
        pnl_usd = round(pnl_override, 2)
    else:
        pnl_usd = round(pips * _pip_value_per_lot(ticker) * lot_size, 2)

    for t in trades:
        if t["id"] == trade["id"]:
            t["status"]       = result
            t["exit_price"]   = exit_price
            t["pips_result"]  = round(pips, 1)
            t["pnl_usd"]      = pnl_usd
            t["close_reason"] = reason
            t["closed_at"]    = closed_at
            break

    _save_sim_trades(trades)

    # ── Tutup posisi MT5 jika trade ini live ──────────────────
    mt5_ticket = trade.get("mt5_ticket")
    if close_mt5 and mt5_ticket and trade.get("is_live"):
        try:
            from mt5_bridge import close_position, is_connected
            if is_connected():
                ok, msg = close_position(int(mt5_ticket))
                print(f"[MT5] Close ticket #{mt5_ticket}: {msg}")
            else:
                print(f"[MT5] MT5 tidak terhubung — tidak bisa close ticket #{mt5_ticket}")
        except Exception as e:
            print(f"[MT5] close_position error: {e}")

    # Update profile totals
    profile = get_profile_by_id(trade["profile_id"])
    if profile:
        wins   = profile.get("total_wins", 0) + (1 if result == "WIN" else 0)
        losses = profile.get("total_losses", 0) + (1 if result == "LOSS" else 0)
        update_profile(
            profile["id"],
            total_wins=wins,
            total_losses=losses,
            net_pips=round(profile.get("net_pips", 0) + pips, 1),
            net_pnl_usd=round(profile.get("net_pnl_usd", 0) + pnl_usd, 2),
        )

    # Kirim notif Telegram
    _send_close_telegram(trade, result, exit_price, pips, pnl_usd, reason)


# ============================================================
# AUTO SCAN & ORDER PLACEMENT
# ============================================================

def run_auto_scan(profile: dict) -> dict:
    """
    Scan semua pair di profil, auto-place sim order jika sinyal valid.
    Return: dict berisi jumlah new_orders, skipped, error, details.
    """
    from data_provider import (
        fetch_macro_data, fetch_forex_data, get_market_sentiment,
        check_news_shield, FOREX_PAIRS
    )
    from engine import (
        hitung_indikator_lengkap, get_detailed_scores_v12,
        calculate_fibonacci_levels, deteksi_smc_v2
    )
    from ai_hub import generate_ai_judgment

    result = {
        "new_orders": 0,
        "skipped":    0,
        "errors":     0,
        "details":    [],
        "scan_time":  datetime.now(tz_jkt).strftime("%Y-%m-%d %H:%M WIB"),
    }

    if not profile.get("is_active"):
        result["details"].append("⏸️ Profil tidak aktif, scan dilewati.")
        return result

    # ── CIRCUIT BREAKER — stop kalau rugi harian / loss streak tembus batas ──
    allowed, cb_reason = check_circuit_breaker(profile)
    if not allowed:
        result["details"].append(cb_reason)
        result["halted"] = True
        return result

    min_q    = profile.get("min_q_score", 8)
    max_ot   = profile.get("max_open_trades", 3)
    pairs    = profile.get("pairs", [])
    sl_m     = profile.get("sl_atr_mult", 1.5)
    tp_m     = profile.get("tp_atr_mult", 4.5)
    capital  = profile.get("capital", 1000)
    use_risk = profile.get("use_risk_sizing", True)
    risk_pct = profile.get("risk_percent", 1.0)

    # Check global open count for this profile
    open_trades = get_sim_trades(profile["id"], status_filter="OPEN")
    open_tickers = {t["ticker"] for t in open_trades}

    if len(open_trades) >= max_ot:
        result["details"].append(f"⚠️ Max open trades ({max_ot}) tercapai. Scan ditunda.")
        result["skipped"] = len(pairs)
        return result

    # Fetch shared macro data once
    try:
        macro = fetch_macro_data()
    except Exception as e:
        macro = {}
        result["details"].append(f"⚠️ Macro data gagal: {e}")

    for ticker in pairs:
        # Skip if pair already has an open trade
        if ticker in open_tickers:
            result["skipped"] += 1
            result["details"].append(f"⏭️ {ticker} — sudah ada trade OPEN, skip.")
            continue

        # Skip if max trades already reached mid-scan
        if len(open_trades) + result["new_orders"] >= max_ot:
            result["skipped"] += 1
            result["details"].append(f"⏭️ {ticker} — max trades reached.")
            continue

        # Skip if market closed (weekend) for non-crypto
        if not _is_market_open(ticker):
            result["skipped"] += 1
            result["details"].append(f"🌙 {ticker} — Market tutup (weekend), skip.")
            continue

        # Profil LIVE: lewati pair yang tidak tersedia di broker (mis. crypto di broker forex)
        if profile.get("live_mode"):
            try:
                from mt5_bridge import symbol_exists, is_connected as _mt5_conn
                if _mt5_conn() and not symbol_exists(ticker):
                    result["skipped"] += 1
                    result["details"].append(f"🚫 {ticker} — tidak tersedia di broker, skip (live).")
                    continue
            except Exception:
                pass

        try:
            # Check news shield
            news_alerts = check_news_shield(ticker)
            if news_alerts:
                result["skipped"] += 1
                result["details"].append(f"📰 {ticker} — NEWS SHIELD aktif, skip.")
                continue

            # Fetch & calculate
            df_raw = fetch_forex_data(ticker, "30d", "4h")
            if df_raw is None or df_raw.empty:
                result["errors"] += 1
                result["details"].append(f"❌ {ticker} — Data tidak tersedia.")
                continue

            df = hitung_indikator_lengkap(df_raw)

            si, sd, _ = get_market_sentiment(ticker)
            fib = calculate_fibonacci_levels(df)

            # HTF bias
            df_htf_raw = fetch_forex_data(ticker, "60d", "1d")
            htf_bias = 0
            if df_htf_raw is not None and not df_htf_raw.empty:
                df_htf = hitung_indikator_lengkap(df_htf_raw)
                htf_bias = 1 if df_htf.iloc[-1]["Close"] > df_htf.iloc[-1]["EMA50"] else -1

            score_res = get_detailed_scores_v12(df, macro, si, fib, htf_bias, ticker=ticker)
            q_total = score_res.get("total", 0)

            # Check threshold
            if abs(q_total) < min_q:
                result["skipped"] += 1
                result["details"].append(
                    f"📊 {ticker} — Q-Score {q_total:+} < threshold ±{min_q}, skip."
                )
                continue

            smc_zones = deteksi_smc_v2(df)
            last_close = float(df.iloc[-1]["Close"])
            atr        = float(df.iloc[-1].get("ATR", last_close * 0.005))

            ai_data = generate_ai_judgment(score_res, fib, smc_zones, last_close, atr=atr, ticker=ticker)
            decision = ai_data.get("decision", "STANDBY")

            if decision not in ("EXECUTE BUY", "EXECUTE SELL"):
                result["skipped"] += 1
                result["details"].append(
                    f"🤔 {ticker} — AI Verdict: {decision}, tidak execute."
                )
                continue

            direction = "BUY" if "BUY" in decision else "SELL"
            plan = ai_data.get("plan", {})
            entry = plan.get("entry", last_close)

            # Auto-trader risk is governed by the profile's ATR multipliers
            # (deterministic risk management), NOT the discretionary fib-based
            # SL/TP from the AI plan. This makes the UI sliders actually control risk.
            if atr and atr > 0:
                risk   = sl_m * atr   # SL distance
                reward = tp_m * atr   # main target (TP2) distance
                if direction == "BUY":
                    sl  = entry - risk
                    tp1 = entry + reward * 0.5
                    tp2 = entry + reward
                    tp3 = entry + reward * 1.5
                else:
                    sl  = entry + risk
                    tp1 = entry - reward * 0.5
                    tp2 = entry - reward
                    tp3 = entry - reward * 1.5
            else:
                # ATR unavailable → fall back to AI plan levels
                sl    = plan.get("sl", entry * (0.995 if direction == "BUY" else 1.005))
                tp1   = plan.get("tp1", 0)
                tp2   = plan.get("tp2", 0)
                tp3   = plan.get("tp3", 0)

            pair_name = FOREX_PAIRS.get(ticker, {}).get("name", ticker.replace("=X", "").replace("=F", ""))

            # ── Risk-based position sizing ────────────────────────
            # Lot dihitung dari risk% × modal dibagi jarak SL → risiko $ konsisten.
            if use_risk:
                lot = calc_position_size(capital, risk_pct, abs(entry - sl), ticker,
                                         lot_fallback=profile.get("lot_size", 0.01))
            else:
                lot = profile.get("lot_size", 0.01)

            _place_sim_order(
                profile=profile,
                ticker=ticker,
                pair_name=pair_name,
                direction=direction,
                entry_price=entry,
                sl=sl,
                tp1=tp1,
                tp2=tp2,
                tp3=tp3,
                q_score=q_total,
                confidence=ai_data.get("confidence", 0),
                atr=atr,
                score_details=score_res.get("details", {}),
                score_audit=score_res.get("audit", {}),
                ai_reasoning=ai_data.get("reasons", []),
                pa_signal=score_res.get("pa_data", {}).get("signal", ""),
                lot_override=lot,
            )

            result["new_orders"] += 1
            result["details"].append(
                f"✅ {pair_name} — {direction} {lot} lot @ {entry:.5f} | Q={q_total:+} | Conf={ai_data.get('confidence',0)}%"
            )

        except Exception as e:
            result["errors"] += 1
            result["details"].append(f"❌ {ticker} — Error: {str(e)[:80]}")
            continue

    # Update last scan timestamp
    update_profile(profile["id"], last_scan_at=datetime.now(tz_jkt).isoformat())
    return result


# ============================================================
# AUTO SYNC (SL/TP Check)
# ============================================================

def sync_sim_trades(profile_id: str) -> int:
    """
    Periksa semua OPEN trade pada profil, auto-close jika SL atau TP2 sudah kena.
    Return jumlah trade yang berhasil di-close.
    """
    from data_provider import fetch_forex_data

    # Trade live ditutup di broker (SL/TP kena di MT5) → rekonsiliasi PnL aktual dulu.
    synced = reconcile_live_trades(profile_id)

    open_trades = get_sim_trades(profile_id, status_filter="OPEN")
    if not open_trades:
        return synced

    for trade in open_trades:
        ticker    = trade["ticker"]
        direction = trade.get("direction", "BUY")
        entry     = trade.get("entry_price", 0)
        sl        = trade.get("sl", 0)
        tp2       = trade.get("tp2", 0)

        if not sl or not entry:
            continue

        # Trade live yang masih open dikelola broker (SL/TP terpasang di MT5),
        # jangan disimulasikan pakai data yfinance — biar rekonsiliasi yang urus.
        if trade.get("is_live") and trade.get("mt5_ticket"):
            continue

        try:
            df = fetch_forex_data(ticker, period="30d", interval="15m")
            if df is None or df.empty:
                continue

            # Filter candles after entry
            opened_at_str = trade.get("opened_at", "")
            if opened_at_str:
                try:
                    et = datetime.fromisoformat(opened_at_str)
                    if et.tzinfo is None:
                        et = tz_jkt.localize(et)
                    
                    if df.index.tzinfo is not None:
                        et = et.astimezone(df.index.tzinfo)
                    else:
                        et = et.replace(tzinfo=None)
                        
                    df = df[df.index >= et]
                except Exception:
                    pass

            if df.empty:
                continue

            # Determine pip multiplier
            is_jpy    = "JPY" in ticker
            is_crypto = "-USD" in ticker
            is_commo  = ticker.endswith("=F")

            if is_crypto:
                pip_mult = 1
            elif is_jpy:
                pip_mult = 100
            elif is_commo:
                pip_mult = 1
            else:
                pip_mult = 10000

            # Spread/slippage buffer (harga) — hindari SL palsu dari wick tipis.
            # ~2 pips untuk forex/JPY, 0.05% untuk crypto/komoditas.
            if is_crypto or is_commo:
                buffer = entry * 0.0005
            else:
                buffer = 2.0 / pip_mult   # 2 pips dalam satuan harga

            for idx, row in df.iterrows():
                high  = float(row["High"])
                low   = float(row["Low"])
                candle = idx.strftime("%Y-%m-%d %H:%M")

                if direction == "BUY":
                    sl_hit = sl > 0 and low <= (sl - buffer)
                    tp_hit = tp2 > 0 and high >= tp2

                    if sl_hit and tp_hit:
                        # Ambiguous candle: assume worst case (SL hit first)
                        pips = (sl - entry) * pip_mult
                        _close_sim_trade(trade, "LOSS", sl, pips, "SL_HIT")
                        synced += 1
                        break
                    if tp_hit:
                        pips = (tp2 - entry) * pip_mult
                        _close_sim_trade(trade, "WIN", tp2, pips, "TP2_HIT")
                        synced += 1
                        break
                    if sl_hit:
                        pips = (sl - entry) * pip_mult
                        _close_sim_trade(trade, "LOSS", sl, pips, "SL_HIT")
                        synced += 1
                        break
                else:  # SELL
                    sl_hit = sl > 0 and high >= (sl + buffer)
                    tp_hit = tp2 > 0 and low <= tp2

                    if sl_hit and tp_hit:
                        # Ambiguous candle: assume worst case (SL hit first)
                        pips = (entry - sl) * pip_mult
                        _close_sim_trade(trade, "LOSS", sl, pips, "SL_HIT")
                        synced += 1
                        break
                    if tp_hit:
                        pips = (entry - tp2) * pip_mult
                        _close_sim_trade(trade, "WIN", tp2, pips, "TP2_HIT")
                        synced += 1
                        break
                    if sl_hit:
                        pips = (entry - sl) * pip_mult
                        _close_sim_trade(trade, "LOSS", sl, pips, "SL_HIT")
                        synced += 1
                        break

        except Exception as e:
            print(f"[SIM SYNC] Error {ticker}: {e}")
            continue

    return synced


def reconcile_live_trades(profile_id: str) -> int:
    """
    Untuk trade LIVE yang sudah ditutup di broker (SL/TP kena di MT5),
    update record sim dengan PnL & harga aktual dari riwayat MT5.
    Return jumlah trade yang berhasil direkonsiliasi.
    """
    try:
        from mt5_bridge import is_connected, get_open_positions, get_trade_history
    except Exception:
        return 0
    if not is_connected():
        return 0

    live_open = [t for t in get_sim_trades(profile_id, status_filter="OPEN")
                 if t.get("is_live") and t.get("mt5_ticket")]
    if not live_open:
        return 0

    open_tickets = {p["ticket"] for p in get_open_positions()}
    history = get_trade_history(days=30)
    reconciled = 0

    for t in live_open:
        try:
            ticket = int(t["mt5_ticket"])
        except (TypeError, ValueError):
            continue
        if ticket in open_tickets:
            continue  # masih open di broker

        # Cari deal penutup di history (cocokkan via position_id atau ticket)
        deal = next((h for h in history
                     if h.get("position_id") == ticket or h.get("ticket") == ticket), None)
        if not deal:
            continue

        profit     = deal.get("profit", 0)
        exit_price = deal.get("price", t.get("entry_price", 0))
        result     = "WIN" if profit > 0 else ("LOSS" if profit < 0 else "BE")
        entry      = t.get("entry_price", 0)
        pip_mult   = _pip_mult(t["ticker"])
        if t.get("direction") == "BUY":
            pips = (exit_price - entry) * pip_mult
        else:
            pips = (entry - exit_price) * pip_mult

        # close_mt5=False (posisi sudah tertutup di broker), pakai PnL aktual broker
        _close_sim_trade(t, result, exit_price, round(pips, 1), "MT5_RECONCILE",
                         pnl_override=profit, close_mt5=False)
        reconciled += 1

    return reconciled


def close_all_open_trades(profile_id: str) -> int:
    """Tutup semua trade OPEN profil ini (sim + posisi MT5 jika live). Return jumlah ditutup."""
    closed = 0
    for t in get_sim_trades(profile_id, status_filter="OPEN"):
        if manual_close_sim_trade(t["id"]):
            closed += 1
    return closed


# ============================================================
# PnL UTILITIES
# ============================================================

def get_unrealized_pnl(trade: dict, current_price: float) -> float:
    """Hitung unrealized PnL untuk trade yang masih OPEN."""
    entry     = trade.get("entry_price", 0)
    lot_size  = trade.get("lot_size", 0.01)
    direction = trade.get("direction", "BUY")
    ticker    = trade.get("ticker", "")

    is_jpy    = "JPY" in ticker
    is_crypto = "-USD" in ticker
    is_commo  = ticker.endswith("=F")

    if direction == "BUY":
        raw_move = current_price - entry
    else:
        raw_move = entry - current_price

    if is_crypto:
        pip_val = PIP_VALUE_PER_LOT["CRYPTO"] * lot_size
        return round(raw_move * pip_val, 2)
    elif is_jpy:
        pip_val = PIP_VALUE_PER_LOT["JPY"] * lot_size
        return round(raw_move * pip_val * 100, 2)
    elif is_commo:
        pip_val = PIP_VALUE_PER_LOT["COMMO"] * lot_size
        return round(raw_move * pip_val, 2)
    else:
        pip_val = PIP_VALUE_PER_LOT["default"] * lot_size
        return round(raw_move * pip_val * 10000, 2)


def get_profile_pl_summary(profile: dict) -> dict:
    """
    Ringkasan P/L ringan untuk kartu di halaman depan.
    realized = total PnL trade selesai; floating = PnL mengambang posisi LIVE (dari MT5).
    Sengaja TIDAK fetch harga yfinance per-trade agar halaman depan tetap cepat.
    """
    pid     = profile["id"]
    trades  = get_sim_trades(pid)
    closed  = [t for t in trades if t.get("status") in ("WIN", "LOSS", "BE")]
    open_t  = [t for t in trades if t.get("status") == "OPEN"]
    realized = round(sum(t.get("pnl_usd", 0) or 0 for t in closed), 2)
    wins = len([t for t in closed if t.get("status") == "WIN"])
    win_rate = round(wins / len(closed) * 100, 1) if closed else 0.0

    floating = 0.0
    has_live = any(t.get("is_live") for t in open_t)
    if has_live:
        try:
            from mt5_bridge import is_connected, get_open_positions
            if is_connected():
                live_tickets = {int(t["mt5_ticket"]) for t in open_t if t.get("mt5_ticket")}
                for p in get_open_positions():
                    if p["ticket"] in live_tickets:
                        floating += p["profit"]
        except Exception:
            pass

    return {
        "realized":     realized,
        "floating":     round(floating, 2),
        "open_count":   len(open_t),
        "closed_count": len(closed),
        "win_rate":     win_rate,
        "has_live":     has_live,
        "live_mode":    profile.get("live_mode", False),
    }


def get_profile_stats(profile_id: str) -> dict:
    """Hitung statistik lengkap untuk sebuah profil."""
    profile = get_profile_by_id(profile_id)
    if not profile:
        return {}

    trades  = get_sim_trades(profile_id)
    closed  = [t for t in trades if t.get("status") in ("WIN", "LOSS", "BE")]
    open_t  = [t for t in trades if t.get("status") == "OPEN"]
    wins    = [t for t in closed if t.get("status") == "WIN"]
    losses  = [t for t in closed if t.get("status") == "LOSS"]

    total_closed = len(closed)
    win_rate = (len(wins) / total_closed * 100) if total_closed > 0 else 0
    net_pips = sum(t.get("pips_result", 0) or 0 for t in closed)
    net_pnl  = sum(t.get("pnl_usd", 0) or 0 for t in closed)

    # Max drawdown (peak-to-trough on equity curve)
    equity_curve = []
    cum = 0
    for t in reversed(closed):
        cum += t.get("pnl_usd", 0) or 0
        equity_curve.append(cum)

    peak = 0
    max_dd = 0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

    return {
        "profile":      profile,
        "total_trades": len(trades),
        "open_trades":  len(open_t),
        "total_closed": total_closed,
        "wins":         len(wins),
        "losses":       len(losses),
        "win_rate":     round(win_rate, 1),
        "net_pips":     round(net_pips, 1),
        "net_pnl_usd":  round(net_pnl, 2),
        "max_drawdown": round(max_dd, 2),
        "equity_curve": equity_curve,
        "open_list":    open_t,
        "closed_list":  closed,
        "all_trades":   trades,
    }


def manual_close_sim_trade(trade_id: str) -> bool:
    """Manual close trade simulasi oleh user."""
    from data_provider import fetch_forex_data
    trades = _load_sim_trades()
    for t in trades:
        if t["id"] == trade_id and t["status"] == "OPEN":
            ticker = t["ticker"]
            entry  = t.get("entry_price", 0)
            direction = t.get("direction", "BUY")

            # Get current price
            try:
                df = fetch_forex_data(ticker, period="1d", interval="15m")
                cur_price = float(df.iloc[-1]["Close"]) if df is not None and not df.empty else entry
            except Exception:
                cur_price = entry

            is_jpy    = "JPY" in ticker
            is_crypto = "-USD" in ticker
            is_commo  = ticker.endswith("=F")
            pip_mult  = 1 if is_crypto else (100 if is_jpy else (1 if is_commo else 10000))

            if direction == "BUY":
                pips = (cur_price - entry) * pip_mult
            else:
                pips = (entry - cur_price) * pip_mult

            result = "WIN" if pips > 0 else ("LOSS" if pips < 0 else "BE")
            _close_sim_trade(t, result, cur_price, pips, "MANUAL_CLOSE")
            return True
    return False


# ============================================================
# TRADE REVIEW ENGINE
# ============================================================

def generate_trade_review(trade: dict) -> dict:
    """
    Generate post-trade review: breakdown indikator saat entry,
    analisis kenapa WIN/LOSS, dan lesson yang bisa dipelajari.
    """
    direction  = trade.get("direction", "BUY")
    result     = trade.get("status", "OPEN")
    details    = trade.get("entry_score_details", {})
    audit      = trade.get("entry_score_audit", {})
    reasoning  = trade.get("entry_ai_reasoning", [])
    pa_signal  = trade.get("entry_pa_signal", "")
    q_score    = trade.get("q_score", 0)
    confidence = trade.get("confidence", 0)
    close_rsn  = trade.get("close_reason", "")
    pips       = trade.get("pips_result", 0) or 0
    pnl        = trade.get("pnl_usd", 0) or 0

    # ── 1. Breakdown indikator per dimensi ────────────────
    INDICATOR_NAMES = {
        "Trend":       "📈 Trend (EMA Stack + Ichimoku)",
        "Momentum":    "⚡ Momentum (StochRSI + MACD + Williams %R)",
        "Bollinger":   "🔵 Bollinger Bands",
        "VWAP":        "🏦 VWAP Institutional Bias",
        "ADX":         "💪 ADX Trend Strength",
        "Volatility":  "🌊 ATR Volatility",
        "MTF":         "⏱️ Multi-Timeframe Alignment",
        "Macro":       "🌐 Macro DXY Correlation",
        "Sentiment":   "💬 Market Sentiment",
        "PriceAction": "🕯️ Price Action Pattern",
    }

    bullish_factors = []
    bearish_factors = []
    neutral_factors = []

    for key, label in INDICATOR_NAMES.items():
        val = details.get(key, 0)
        audit_text = audit.get(key, "")
        if val > 0:
            bullish_factors.append({"label": label, "score": val, "detail": audit_text})
        elif val < 0:
            bearish_factors.append({"label": label, "score": val, "detail": audit_text})
        else:
            neutral_factors.append({"label": label, "score": val, "detail": audit_text})

    # ── 2. Analisis alignment ─────────────────────────────
    # Apakah faktor bullish/bearish selaras dengan arah trade?
    dominant_bull = len(bullish_factors)
    dominant_bear = len(bearish_factors)

    if direction == "BUY":
        aligned   = bullish_factors
        counter   = bearish_factors
        aligned_label = "bullish"
        counter_label = "bearish"
    else:
        aligned   = bearish_factors
        counter   = bullish_factors
        aligned_label = "bearish"
        counter_label = "bullish"

    alignment_pct = round(len(aligned) / max(len(aligned) + len(counter), 1) * 100)

    # ── 3. Generate lesson ────────────────────────────────
    lessons = []

    if result == "WIN":
        if alignment_pct >= 70:
            lessons.append("✅ Confluence kuat — mayoritas indikator selaras dengan arah trade. Ini yang menyebabkan WIN.")
        if pa_signal in ("BULLISH_SWEEP", "BEARISH_SWEEP"):
            lessons.append("✅ Liquidity Sweep (SFP) terkonfirmasi — sinyal ini sangat kuat dan akurat untuk entry.")
        if pa_signal in ("BULLISH_ENGULFING", "BEARISH_ENGULFING"):
            lessons.append("✅ Bullish/Bearish Engulfing sebagai katalis — pola candlestick ini mendukung momentum.")
        if trade.get("entry_score_details", {}).get("MTF", 0) > 0:
            lessons.append("✅ Multi-Timeframe alignment bonus aktif — HTF dan LTF searah. Faktor ini meningkatkan win probability.")
    elif result == "LOSS":
        if alignment_pct < 60:
            lessons.append("⚠️ Confluence kurang kuat — banyak indikator berlawanan dengan arah trade. Perlu filter lebih ketat.")
        if len(counter) >= 3:
            lessons.append(f"⚠️ Ada {len(counter)} faktor {counter_label} yang melawan arah — sinyal tidak murni, risiko higher.")
        if close_rsn == "SL_HIT":
            if details.get("ADX", 0) < 0:
                lessons.append("⚠️ ADX rendah (ranging market) — entry di pasar sideways lebih berisiko kena SL.")
            if details.get("MTF", 0) == 0:
                lessons.append("⚠️ Tidak ada MTF alignment — timeframe higher tidak mendukung arah trade.")
            if details.get("Macro", 0) * (-1 if direction == "BUY" else 1) > 0:
                lessons.append("⚠️ Macro/DXY berlawanan — kondisi fundamental tidak mendukung arah trade.")
        if pa_signal == "NONE":
            lessons.append("⚠️ Tidak ada konfirmasi Price Action — entry tanpa PA signal lebih berisiko.")

    if not lessons:
        lessons.append("ℹ️ Trade ditutup dengan hasil normal sesuai kondisi pasar saat entry.")

    # ── 4. Signal quality assessment ─────────────────────
    if q_score >= 10:
        quality = "🔥 SANGAT KUAT"
        quality_color = "#00ffcc"
    elif q_score >= 7:
        quality = "✅ KUAT"
        quality_color = "#a3ffeb"
    elif q_score >= 5:
        quality = "⚡ MODERAT"
        quality_color = "#FFD700"
    else:
        quality = "⚠️ LEMAH"
        quality_color = "#ff8585"

    return {
        "direction":       direction,
        "result":          result,
        "q_score":         q_score,
        "confidence":      confidence,
        "signal_quality":  quality,
        "quality_color":   quality_color,
        "alignment_pct":   alignment_pct,
        "bullish_factors": bullish_factors,
        "bearish_factors": bearish_factors,
        "neutral_factors": neutral_factors,
        "aligned_factors": aligned,
        "counter_factors": counter,
        "aligned_label":   aligned_label,
        "counter_label":   counter_label,
        "pa_signal":       pa_signal,
        "reasoning":       reasoning,
        "lessons":         lessons,
        "pips":            pips,
        "pnl_usd":         pnl,
        "close_reason":    close_rsn,
    }
