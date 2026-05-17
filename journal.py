import json
import os
import uuid
import pytz
from datetime import datetime

from db_client import get_supabase_client

JOURNAL_FILE = "trade_journal.json"
tz_jkt = pytz.timezone("Asia/Jakarta")

def _load_journal() -> list:
    client = get_supabase_client()
    if client:
        try:
            res = client.table("trade_journal").select("*").order("created_at", desc=True).execute()
            return res.data
        except Exception as e:
            print(f"[Supabase] _load_journal error: {e}")

    if not os.path.exists(JOURNAL_FILE):
        return []
    with open(JOURNAL_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def _save_local_journal(data: list):
    with open(JOURNAL_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def log_signal(ticker, pair_name, decision, confidence, q_score, pa_signal, plan, price):
    """Log a new EXECUTE signal to the trade journal (status=PENDING until user decides)."""
    journal = _load_journal()

    # Prevent duplicate logging for same ticker+candle
    for t in journal[:10]:
        if t.get("ticker") == ticker and t.get("entry_price") == plan.get("entry", price):
            if t.get("status") in ("PENDING", "OPEN", "SKIPPED"):
                return t["id"]

    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now(tz_jkt).strftime("%Y-%m-%d %H:%M WIB"),
        "opened_at_iso": datetime.now(tz_jkt).isoformat(),
        "ticker": ticker,
        "pair_name": pair_name,
        "decision": decision,  # EXECUTE BUY / EXECUTE SELL
        "direction": "BUY" if "BUY" in decision else "SELL",
        "confidence": confidence,
        "q_score": q_score,
        "pa_signal": pa_signal,
        "entry_price": plan.get("entry", price),
        "sl": plan.get("sl", 0),
        "tp1": plan.get("tp1", 0),
        "tp2": plan.get("tp2", 0),
        "tp3": plan.get("tp3", 0),
        "rr": plan.get("rr2", 0),
        "status": "PENDING",  # PENDING → user decides → OPEN or SKIPPED
        "exit_price": None,
        "pips_result": None,
        "closed_at": None,
        "closed_at_candle": None,
        "close_reason": None,  # SL_HIT / TP1_HIT / TP2_HIT / MANUAL
        "notes": "",
    }
    
    client = get_supabase_client()
    if client:
        try:
            db_entry = entry.copy()
            if "rr" in db_entry:
                del db_entry["rr"] # RR is not in our SQL schema
            if "opened_at_iso" in db_entry:
                del db_entry["opened_at_iso"]
            client.table("trade_journal").insert(db_entry)
        except Exception as e:
            print(f"[Supabase] log_signal error: {e}")
            
    journal.insert(0, entry)
    _save_local_journal(journal)
    return entry["id"]


def follow_signal(trade_id):
    """User decides to follow the recommendation → status OPEN."""
    journal = _load_journal()
    for t in journal:
        if t["id"] == trade_id and t["status"] == "PENDING":
            client = get_supabase_client()
            if client:
                try:
                    client.table("trade_journal").eq("id", trade_id).update({"status": "OPEN"})
                except Exception as e:
                    print(f"[Supabase] follow_signal error: {e}")
            t["status"] = "OPEN"
            _save_local_journal(journal)
            return True
    return False


def skip_signal(trade_id):
    """User decides NOT to follow → status SKIPPED."""
    journal = _load_journal()
    for t in journal:
        if t["id"] == trade_id and t["status"] == "PENDING":
            client = get_supabase_client()
            if client:
                try:
                    client.table("trade_journal").eq("id", trade_id).update({"status": "SKIPPED"})
                except Exception as e:
                    print(f"[Supabase] skip_signal error: {e}")
            t["status"] = "SKIPPED"
            _save_local_journal(journal)
            return True
    return False


def close_trade(trade_id, result, exit_price, pips_result, notes="", reason="MANUAL"):
    """Close an OPEN trade with result (WIN/LOSS/BE)."""
    journal = _load_journal()
    closed_time = datetime.now(tz_jkt).strftime("%Y-%m-%d %H:%M WIB")
    for t in journal:
        if t["id"] == trade_id and t["status"] == "OPEN":
            client = get_supabase_client()
            if client:
                try:
                    client.table("trade_journal").eq("id", trade_id).update({
                        "status": result,
                        "exit_price": exit_price,
                        "pips_result": pips_result,
                        "notes": notes,
                        "close_reason": reason,
                        "closed_at": closed_time
                    })
                except Exception as e:
                    print(f"[Supabase] close_trade error: {e}")
                    
            t["status"] = result
            t["exit_price"] = exit_price
            t["pips_result"] = pips_result
            t["notes"] = notes
            t["close_reason"] = reason
            t["closed_at"] = closed_time
            _save_local_journal(journal)
            return True
    return False


def delete_trade(trade_id):
    """Delete a trade entry."""
    client = get_supabase_client()
    if client:
        try:
            client.table("trade_journal").eq("id", trade_id).delete()
        except Exception as e:
            print(f"[Supabase] delete_trade error: {e}")
            
    journal = _load_journal()
    journal = [t for t in journal if t["id"] != trade_id]
    _save_local_journal(journal)


def sync_open_trades():
    """
    Sync all OPEN trades against historical price data.
    For each OPEN trade, fetch candle data from entry time to now,
    and check candle-by-candle if SL or TP was hit.
    """
    from data_provider import fetch_forex_data, FOREX_PAIRS

    journal = _load_journal()
    open_trades = [t for t in journal if t["status"] == "OPEN"]

    if not open_trades:
        return 0

    synced = 0
    for trade in open_trades:
        try:
            ticker = trade["ticker"]
            direction = trade.get("direction", "BUY")
            entry_price = trade.get("entry_price", 0)
            sl = trade.get("sl", 0)
            tp1 = trade.get("tp1", 0)
            tp2 = trade.get("tp2", 0)

            if not sl or not entry_price:
                continue

            # Fetch 4h candles covering the trade period
            df = fetch_forex_data(ticker, period="30d", interval="4h")
            if df is None or df.empty:
                continue

            # Find candles after trade entry
            entry_time = trade.get("opened_at_iso", "")
            if entry_time:
                try:
                    from datetime import datetime as _dt
                    et = _dt.fromisoformat(entry_time)
                    if et.tzinfo is None:
                        import pytz as _ptz
                        et = _ptz.timezone("Asia/Jakarta").localize(et)
                    # Filter candles after entry
                    df = df[df.index >= et]
                except Exception:
                    pass

            if df.empty:
                continue

            # Determine pip multiplier
            is_jpy = "JPY" in ticker
            is_commodity = ticker.endswith("=F")
            is_crypto = "-USD" in ticker

            if is_crypto:
                pip_mult = 1  # USD value
            elif is_jpy:
                pip_mult = 100
            elif is_commodity:
                pip_mult = 1
            else:
                pip_mult = 10000

            # Walk through each candle
            for idx, row in df.iterrows():
                high = float(row["High"])
                low = float(row["Low"])
                close = float(row["Close"])
                candle_date = idx.strftime("%Y-%m-%d %H:%M")

                if direction == "BUY":
                    # SL hit: price went below SL
                    if sl > 0 and low <= sl:
                        pips = (sl - entry_price) * pip_mult
                        _close_synced(trade, "LOSS", sl, pips, candle_date, "SL_HIT")
                        synced += 1
                        break
                    # TP2 hit: price went above TP2
                    if tp2 > 0 and high >= tp2:
                        pips = (tp2 - entry_price) * pip_mult
                        _close_synced(trade, "WIN", tp2, pips, candle_date, "TP2_HIT")
                        synced += 1
                        break
                    # TP1 hit: price went above TP1
                    if tp1 > 0 and high >= tp1:
                        pips = (tp1 - entry_price) * pip_mult
                        _close_synced(trade, "WIN", tp1, pips, candle_date, "TP1_HIT")
                        synced += 1
                        break

                else:  # SELL
                    # SL hit: price went above SL
                    if sl > 0 and high >= sl:
                        pips = (entry_price - sl) * pip_mult
                        _close_synced(trade, "LOSS", sl, pips, candle_date, "SL_HIT")
                        synced += 1
                        break
                    # TP2 hit: price went below TP2
                    if tp2 > 0 and low <= tp2:
                        pips = (entry_price - tp2) * pip_mult
                        _close_synced(trade, "WIN", tp2, pips, candle_date, "TP2_HIT")
                        synced += 1
                        break
                    # TP1 hit: price went below TP1
                    if tp1 > 0 and low <= tp1:
                        pips = (entry_price - tp1) * pip_mult
                        _close_synced(trade, "WIN", tp1, pips, candle_date, "TP1_HIT")
                        synced += 1
                        break

        except Exception as e:
            print(f"[JOURNAL SYNC] Error syncing {trade.get('ticker')}: {e}")
            continue

    # Save all changes
    _save_local_journal(journal)
    return synced


def _close_synced(trade, result, exit_price, pips, candle_date, reason):
    """Helper to close a trade during sync (modifies dict in-place and updates Supabase)."""
    trade["status"] = result
    trade["exit_price"] = exit_price
    trade["pips_result"] = round(pips, 1)
    trade["close_reason"] = reason
    trade["closed_at"] = candle_date
    trade["closed_at_candle"] = candle_date
    notes = f"Auto-sync: {reason} pada {candle_date}"
    trade["notes"] = notes
    
    client = get_supabase_client()
    if client:
        try:
            client.table("trade_journal").eq("id", trade["id"]).update({
                "status": result,
                "exit_price": exit_price,
                "pips_result": round(pips, 1),
                "close_reason": reason,
                "closed_at": candle_date,
                "closed_at_candle": candle_date,
                "notes": notes
            })
        except Exception as e:
            print(f"[Supabase] _close_synced error: {e}")


def get_journal_entries(limit=50, filter_ticker=None, filter_status=None):
    """Get journal entries with optional filters."""
    journal = _load_journal()
    if filter_ticker and filter_ticker != "ALL":
        journal = [t for t in journal if t["ticker"] == filter_ticker]
    if filter_status and filter_status != "ALL":
        journal = [t for t in journal if t["status"] == filter_status]
    return journal[:limit]


def get_journal_stats():
    """Calculate aggregate performance stats."""
    journal = _load_journal()
    closed = [t for t in journal if t["status"] in ("WIN", "LOSS", "BE")]
    followed = [t for t in journal if t["status"] in ("WIN", "LOSS", "BE", "OPEN")]
    skipped = [t for t in journal if t["status"] == "SKIPPED"]
    pending = [t for t in journal if t["status"] == "PENDING"]
    total_signals = len(journal)
    total_closed = len(closed)
    open_trades = len([t for t in journal if t["status"] == "OPEN"])

    if total_closed == 0:
        return {
            "total_signals": total_signals,
            "total_closed": 0,
            "open_trades": open_trades,
            "followed": len(followed),
            "skipped": len(skipped),
            "pending": len(pending),
            "wins": 0, "losses": 0, "be": 0,
            "win_rate": 0,
            "net_pips": 0,
            "avg_confidence": 0,
            "best_trade": None,
            "worst_trade": None,
            "current_streak": 0,
            "streak_type": "NONE",
            "pnl_curve": [],
        }

    wins = len([t for t in closed if t["status"] == "WIN"])
    losses = len([t for t in closed if t["status"] == "LOSS"])
    be = len([t for t in closed if t["status"] == "BE"])
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
    net_pips = sum(t.get("pips_result", 0) or 0 for t in closed)
    avg_conf = sum(t.get("confidence", 0) for t in journal) / max(len(journal), 1)

    # Best / Worst trade
    pips_list = [(t.get("pips_result", 0) or 0, t) for t in closed]
    best_trade = max(pips_list, key=lambda x: x[0])[1] if pips_list else None
    worst_trade = min(pips_list, key=lambda x: x[0])[1] if pips_list else None

    # Current streak
    streak = 0
    streak_type = "NONE"
    for t in closed:
        if streak == 0:
            streak_type = t["status"]
            streak = 1
        elif t["status"] == streak_type:
            streak += 1
        else:
            break

    # PnL curve (cumulative)
    pnl_curve = []
    cumulative = 0
    for t in reversed(closed):
        cumulative += t.get("pips_result", 0) or 0
        pnl_curve.append({"trade": t.get("pair_name", ""), "pnl": cumulative})

    return {
        "total_signals": total_signals,
        "total_closed": total_closed,
        "open_trades": open_trades,
        "followed": len(followed),
        "skipped": len(skipped),
        "pending": len(pending),
        "wins": wins, "losses": losses, "be": be,
        "win_rate": win_rate,
        "net_pips": net_pips,
        "avg_confidence": avg_conf,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "current_streak": streak,
        "streak_type": streak_type,
        "pnl_curve": pnl_curve,
    }
