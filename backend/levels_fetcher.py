"""
Price Fetcher + Key Levels Calculator (v5 — Yahoo Finance)
Récupère les prix via yfinance (données précises, gratuit, pas de clé)
Basé sur : NRNR Playbook, Read Through The Smoke, Trading à Sens Unique
"""

import json
import os
import time
from datetime import datetime, timedelta

import yfinance as yf

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Symbol mapping → liste de tickers Yahoo Finance à essayer dans l'ordre
# On essaye d'abord le spot, puis les futures en fallback, puis l'ETF
SYMBOL_MAP = {
    # Forex (spot) — suffixe "=X"
    "EUR/USD": ["EURUSD=X"],
    "GBP/USD": ["GBPUSD=X"],
    "USD/JPY": ["USDJPY=X"],
    "USD/CHF": ["USDCHF=X"],
    "USD/CAD": ["USDCAD=X"],
    "AUD/USD": ["AUDUSD=X"],
    "NZD/USD": ["NZDUSD=X"],
    # Metals — SPOT d'abord (matche TradingView FOREX.com), futures en fallback
    "Gold": ["XAUUSD=X", "GC=F", "GLD"],
    "Silver": ["XAGUSD=X", "SI=F", "SLV"],
    # Indices (vrais indices, préfixe "^")
    "S&P 500": ["^GSPC"],
    "Nasdaq 100": ["^NDX"],
    "Dow Jones": ["^DJI"],
    # Crypto (suffixe "-USD")
    "Bitcoin": ["BTC-USD"],
    "Ethereum": ["ETH-USD"],
    # Commodities (futures, seul choix gratuit)
    "Crude Oil WTI": ["CL=F"],
    "Natural Gas": ["NG=F"],
    "Copper": ["HG=F"],
    "Corn": ["ZC=F"],
    "Wheat": ["ZW=F"],
    "Soybeans": ["ZS=F"],
}


def fetch_price_data(symbol, yf_symbols, period="6mo", interval="1d"):
    """
    Fetch OHLCV data depuis Yahoo Finance.
    yf_symbols : liste de tickers à essayer dans l'ordre (spot puis fallbacks).
    Retourne la première liste de candles valide, ou None si tous échouent.
    """
    if isinstance(yf_symbols, str):
        yf_symbols = [yf_symbols]

    for yf_symbol in yf_symbols:
        try:
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=period, interval=interval, auto_adjust=False)

            if df.empty or len(df) < 20:
                continue  # Essaye le ticker suivant

            candles = []
            for date, row in df.iterrows():
                candles.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row.get("Volume", 0)) if row.get("Volume") else 0,
                })

            candles.reverse()  # plus récent en premier
            # Log quel ticker a fonctionné (utile pour debug)
            if yf_symbol != yf_symbols[0]:
                print(f"(via {yf_symbol})", end=" ", flush=True)
            return candles

        except Exception as e:
            print(f"[{yf_symbol}: {str(e)[:40]}]", end=" ", flush=True)
            continue

    return None



def generate_fallback_levels(symbol):
    """Generate realistic key levels when API is unavailable.
    Prix avril 2026 (basés sur TradingView au 17 avr. 2026)."""
    base_prices = {
        # Forex (spot) — avril 2026
        "EUR/USD": 1.1700, "GBP/USD": 1.3500, "USD/JPY": 158.00,
        "USD/CHF": 0.8600, "USD/CAD": 1.4000, "AUD/USD": 0.6500,
        "NZD/USD": 0.5900,
        # Metals (futures - prix proches du spot)
        "Gold": 4800.00,         # GC=F ≈ XAU/USD
        "Silver": 80.00,         # SI=F ≈ XAG/USD
        # Vrais indices (pas les ETFs)
        "S&P 500": 5400.00,      # ^GSPC S&P 500 index
        "Nasdaq 100": 19000.00,  # ^NDX Nasdaq 100 index
        "Dow Jones": 42000.00,   # ^DJI Dow Jones Industrial
        # Crypto
        "Bitcoin": 95000.00, "Ethereum": 3500.00,
        # Commodities (vraies futures)
        "Crude Oil WTI": 72.00,  # CL=F
        "Natural Gas": 3.50,     # NG=F
        "Copper": 4.20,          # HG=F (prix par livre)
        "Corn": 445.00,          # ZC=F (cents par bushel)
        "Wheat": 560.00,         # ZW=F
        "Soybeans": 1180.00,     # ZS=F
    }

    price = base_prices.get(symbol, 100.0)

    # ATR percentages adaptés au type d'asset
    if symbol in ["Bitcoin", "Ethereum"]:
        atr_pct = 0.035
    elif symbol in ["Gold", "Silver"]:
        atr_pct = 0.020
    elif symbol in ["S&P 500", "Nasdaq 100", "Dow Jones"]:
        atr_pct = 0.015
    elif symbol in ["Crude Oil WTI", "Natural Gas", "Copper", "Corn", "Wheat", "Soybeans"]:
        atr_pct = 0.025
    else:
        atr_pct = 0.008  # Forex

    atr = price * atr_pct

    return {
        "current_price": price,
        "atr_14": round(atr, 5),
        "weekly_high": round(price + atr * 1.2, 5),
        "weekly_low": round(price - atr * 1.5, 5),
        "monthly_high": round(price + atr * 3, 5),
        "monthly_low": round(price - atr * 3.5, 5),
        "resistance_1": round(price + atr * 0.8, 5),
        "resistance_2": round(price + atr * 1.8, 5),
        "resistance_3": round(price + atr * 3.0, 5),
        "support_1": round(price - atr * 0.8, 5),
        "support_2": round(price - atr * 1.8, 5),
        "support_3": round(price - atr * 3.0, 5),
        "pivot": round(price, 5),
        "data_source": "fallback",
    }


# ============================================================
# KEY LEVELS CALCULATOR
# ============================================================

def calculate_key_levels(candles, symbol):
    """
    Calculate institutional key levels based on:
    - NRNR Playbook: Inside bars, Morning Doji, Staircase patterns
    - Read Through The Smoke: Institutional traps, fake breakouts
    - Trading à Sens Unique: S/R zones, pivot points, ATR levels
    """
    if not candles or len(candles) < 20:
        return generate_fallback_levels(symbol)

    # Sort chronologically (oldest first)
    candles = list(reversed(candles))

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    opens = [c["open"] for c in candles]

    current = closes[-1]

    # ATR (14 periods)
    atr_14 = calculate_atr(candles, 14)

    # Weekly / Monthly ranges basés sur les VRAIES dates calendaires
    # (et non pas sur un nombre fixe de candles, ce qui donnait des ranges faux en milieu de semaine)
    now = datetime.now()
    monday_iso = now - timedelta(days=now.weekday())        # lundi de la semaine courante
    month_start = now.replace(day=1)                         # 1er jour du mois courant

    # Helper : parser la date de la candle (format "YYYY-MM-DD" ou "YYYY-MM-DD HH:MM:SS")
    def parse_candle_date(c):
        d = c.get("date", "")
        try:
            return datetime.fromisoformat(d.split(" ")[0])
        except Exception:
            try:
                return datetime.strptime(d[:10], "%Y-%m-%d")
            except Exception:
                return None

    # Collecter les candles de cette semaine
    week_candles = []
    month_candles = []
    for c in candles:
        cd = parse_candle_date(c)
        if cd is None:
            continue
        if cd >= monday_iso.replace(hour=0, minute=0, second=0, microsecond=0):
            week_candles.append(c)
        if cd >= month_start.replace(hour=0, minute=0, second=0, microsecond=0):
            month_candles.append(c)

    # Fallback si parsing échoue (garde le comportement précédent avec [-5:] et [-22:])
    if not week_candles:
        week_candles = candles[-5:]
    if not month_candles:
        month_candles = candles[-22:]

    week_high = max(c["high"] for c in week_candles)
    week_low = min(c["low"] for c in week_candles)
    month_high = max(c["high"] for c in month_candles)
    month_low = min(c["low"] for c in month_candles)

    # Classic pivot points (floor method)
    prev = candles[-2]
    pivot = (prev["high"] + prev["low"] + prev["close"]) / 3
    r1 = 2 * pivot - prev["low"]
    r2 = pivot + (prev["high"] - prev["low"])
    r3 = prev["high"] + 2 * (pivot - prev["low"])
    s1 = 2 * pivot - prev["high"]
    s2 = pivot - (prev["high"] - prev["low"])
    s3 = prev["low"] - 2 * (prev["high"] - pivot)



    # ============================================================
    # SMOKE ZONES (from Read Through The Smoke)
    # ============================================================
    smoke_zones = []

    # Identify zones where price reversed sharply (institutional manipulation)
    for i in range(1, len(candles) - 1):
        body_prev = candles[i - 1]["close"] - candles[i - 1]["open"]
        body_curr = candles[i]["close"] - candles[i]["open"]

        # Sharp reversal: opposite direction with increased range
        if (body_prev * body_curr < 0 and  # Opposite direction
                abs(body_curr) > abs(body_prev) * 1.5):  # Larger body
            zone_high = max(candles[i - 1]["high"], candles[i]["high"])
            zone_low = min(candles[i - 1]["low"], candles[i]["low"])
            smoke_zones.append({
                "high": round(zone_high, 5),
                "low": round(zone_low, 5),
                "date": candles[i]["date"],
                "type": "Smoke Zone",
                "description": "Zone de manipulation institutionnelle — retournement brutal",
            })

    # Keep only last 5 smoke zones
    smoke_zones = smoke_zones[-5:]

    # ============================================================
    # SMART MONEY LEVELS (from COT data)
    # ============================================================
    cot_levels = calculate_cot_levels(symbol)

    return {
        "symbol": symbol,
        "current_price": round(current, 5),
        "atr_14": round(atr_14, 5),
        "weekly_high": round(week_high, 5),
        "weekly_low": round(week_low, 5),
        "monthly_high": round(month_high, 5),
        "monthly_low": round(month_low, 5),
        "pivot": round(pivot, 5),
        "resistance_1": round(r1, 5),
        "resistance_2": round(r2, 5),
        "resistance_3": round(r3, 5),
        "support_1": round(s1, 5),
        "support_2": round(s2, 5),
        "support_3": round(s3, 5),
        
        "smoke_zones": smoke_zones,
        "cot_levels": cot_levels,
        "data_source": "twelvedata",
    }


def calculate_atr(candles, period=14):
    """Average True Range."""
    if len(candles) < period + 1:
        return 0

    trs = []
    for i in range(1, len(candles)):
        tr = max(
            candles[i]["high"] - candles[i]["low"],
            abs(candles[i]["high"] - candles[i - 1]["close"]),
            abs(candles[i]["low"] - candles[i - 1]["close"])
        )
        trs.append(tr)

    return sum(trs[-period:]) / period


def calculate_cot_levels(symbol):
    """
    Cross-reference COT data to identify Smart Money accumulation zones.
    When SM significantly increased positions, those price levels become key.
    """
    cot_path = os.path.join(DATA_DIR, "cot_data.json")
    if not os.path.exists(cot_path):
        return {}

    with open(cot_path, "r") as f:
        cot_data = json.load(f)

    sym_data = cot_data.get("data", {}).get(symbol, {})
    if not sym_data:
        return {}

    history = sym_data.get("history", [])
    if len(history) < 3:
        return {}

    # Find weeks where SM changed position significantly
    accumulation_weeks = []
    for i in range(1, len(history)):
        curr = history[i]
        prev = history[i - 1]
        sm_change = curr["smart_money"]["net"] - prev["smart_money"]["net"]
        oi = curr.get("open_interest", 1)

        if oi > 0:
            change_pct = abs(sm_change) / oi * 100
            if change_pct > 1:  # Significant change (>1% of OI)
                accumulation_weeks.append({
                    "date": curr["date"],
                    "sm_change": sm_change,
                    "direction": "ACCUMULATION" if sm_change > 0 else "DISTRIBUTION",
                    "magnitude": round(change_pct, 2),
                })

    return {
        "accumulation_weeks": accumulation_weeks[:5],
        "current_sm_net": sym_data.get("smart_money_net", 0),
        "sm_bias": sym_data.get("bias", "NEUTRAL"),
    }


# ============================================================
# MAIN
# ============================================================

def save_results(all_levels):
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, "levels_data.json")

    output = {
        "last_updated": datetime.now().isoformat(),
        "count": len(all_levels),
        "data": all_levels,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  [LEVELS] Sauvegardé: {filepath}")
    return filepath


def run():
    print("=" * 55)
    print("  KEY LEVELS CALCULATOR — Trading Dashboard")
    print("=" * 55)

    # Charge le cache précédent pour fallback intelligent
    cache_file = os.path.join(DATA_DIR, "levels_data.json")
    cached_levels = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                cached_levels = cached_data.get("levels", {})
        except Exception:
            pass

    all_levels = {}
    n_symbols = len(SYMBOL_MAP)
    n_live, n_cached, n_fallback = 0, 0, 0

    for i, (symbol, yf_tickers) in enumerate(SYMBOL_MAP.items()):
        primary = yf_tickers[0] if isinstance(yf_tickers, list) else yf_tickers
        print(f"  [LEVELS] [{i+1}/{n_symbols}] {symbol} ({primary})...", end=" ", flush=True)

        candles = fetch_price_data(symbol, yf_tickers)
        if candles and len(candles) >= 20:
            levels = calculate_key_levels(candles, symbol)
            levels["data_source"] = "yahoo"
            print(f"✓ LIVE ({len(candles)} candles)")
            n_live += 1
        else:
            # Fetch a échoué → essayer le cache précédent (dernières données LIVE réussies)
            prev = cached_levels.get(symbol, {})
            if prev.get("data_source") in ("yahoo", "cached", "twelvedata"):
                levels = dict(prev)
                levels["data_source"] = "cached"
                print(f"⚠ CACHED (dernières données LIVE)")
                n_cached += 1
            else:
                levels = generate_fallback_levels(symbol)
                print(f"✗ FALLBACK (aucun cache)")
                n_fallback += 1

        all_levels[symbol] = levels

        # Petit délai pour éviter de spammer Yahoo (pas de vrai rate limit mais prudent)
        if i < n_symbols - 1:
            time.sleep(0.5)

    # Summary
    total_smoke = sum(len(l.get("smoke_zones", [])) for l in all_levels.values())

    print(f"\n  {'─' * 50}")
    print(f"  {len(all_levels)} symboles | {total_smoke} smoke zones")
    print(f"  LIVE: {n_live}  |  CACHED: {n_cached}  |  FALLBACK: {n_fallback}")
    print(f"  {'─' * 50}")

    save_results(all_levels)
    print(f"\n{'=' * 55}")
    return all_levels


if __name__ == "__main__":
    run()
