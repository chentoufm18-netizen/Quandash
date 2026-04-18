"""
Price Fetcher + Key Levels Calculator
Récupère les prix via Twelve Data (gratuit) et calcule les niveaux clés
Basé sur : NRNR Playbook, Read Through The Smoke, Trading à Sens Unique
Place ce fichier dans : ~/trading-dashboard/backend/levels_fetcher.py
"""

import requests
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Twelve Data free tier: 800 requests/day, 8 per minute
# Sign up at https://twelvedata.com for a free API key
API_KEY = os.environ.get("TWELVE_DATA_KEY", "demo")

# Symbol mapping for Twelve Data
SYMBOL_MAP = {
    "EUR/USD": "EUR/USD",
    "GBP/USD": "GBP/USD",
    "USD/JPY": "USD/JPY",
    "USD/CHF": "USD/CHF",
    "USD/CAD": "USD/CAD",
    "AUD/USD": "AUD/USD",
    "NZD/USD": "NZD/USD",
    "Gold": "XAU/USD",
    "Silver": "XAG/USD",
    "S&P 500": "SPX",
    "Nasdaq 100": "NDX",
    "Dow Jones": "DJI",
    "Bitcoin": "BTC/USD",
    "Ethereum": "ETH/USD",
    "Crude Oil WTI": "CL",
    "Natural Gas": "NG",
    "Copper": "HG",
    "Corn": "ZC",
    "Wheat": "ZW",
    "Soybeans": "ZS",
}


def fetch_price_data(symbol, td_symbol, interval="1day", outputsize=100):
    """Fetch OHLCV data from Twelve Data."""
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": td_symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
        "format": "JSON",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        if "values" not in data:
            return None

        candles = []
        for v in data["values"]:
            candles.append({
                "date": v["datetime"],
                "open": float(v["open"]),
                "high": float(v["high"]),
                "low": float(v["low"]),
                "close": float(v["close"]),
                "volume": int(v.get("volume", 0)),
            })

        return candles

    except Exception as e:
        print(f"  [PRICE] Error fetching {symbol}: {e}")
        return None


def generate_fallback_levels(symbol):
    """Generate realistic key levels when API is unavailable."""
    # Base prices by symbol (approximate current levels)
    base_prices = {
        "EUR/USD": 1.0850, "GBP/USD": 1.2650, "USD/JPY": 154.50,
        "USD/CHF": 0.8820, "USD/CAD": 1.3750, "AUD/USD": 0.6450,
        "NZD/USD": 0.5950, "Gold": 2350.00, "Silver": 28.50,
        "S&P 500": 5200.00, "Nasdaq 100": 18100.00, "Dow Jones": 38500.00,
        "Bitcoin": 65000.00, "Ethereum": 3200.00, "Crude Oil WTI": 78.50,
        "Natural Gas": 2.15, "Copper": 4.25, "Corn": 445.00,
        "Wheat": 560.00, "Soybeans": 1180.00,
    }

    price = base_prices.get(symbol, 100.0)

    # Calculate levels based on typical ATR percentages
    if symbol in ["Gold", "Silver", "S&P 500", "Nasdaq 100", "Dow Jones", "Bitcoin", "Ethereum"]:
        atr_pct = 0.015  # 1.5% for volatile assets
    elif symbol in ["Crude Oil WTI", "Natural Gas"]:
        atr_pct = 0.025  # 2.5% for commodities
    else:
        atr_pct = 0.008  # 0.8% for forex

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

    # Weekly high/low (last 5 candles on daily)
    week_high = max(highs[-5:])
    week_low = min(lows[-5:])

    # Monthly high/low (last 22 candles)
    month_high = max(highs[-22:])
    month_low = min(lows[-22:])

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

    all_levels = {}

    for symbol, td_symbol in SYMBOL_MAP.items():
        print(f"  [LEVELS] {symbol}...", end=" ")

        if API_KEY != "demo":
            candles = fetch_price_data(symbol, td_symbol)
            if candles:
                levels = calculate_key_levels(candles, symbol)
                print(f"✓ {len(candles)} candles, {len(levels.get('patterns', []))} patterns")
            else:
                levels = generate_fallback_levels(symbol)
                print("fallback (no data)")
        else:
            levels = generate_fallback_levels(symbol)
            print("fallback (demo key)")

        all_levels[symbol] = levels

    # Summary
    total_patterns = sum(len(l.get("patterns", [])) for l in all_levels.values())
    total_smoke = sum(len(l.get("smoke_zones", [])) for l in all_levels.values())

    print(f"\n  {'─' * 50}")
    print(f"  {len(all_levels)} symboles | {total_patterns} patterns | {total_smoke} smoke zones")
    print(f"  {'─' * 50}")

    for sym, l in all_levels.items():
        patterns = l.get("patterns", [])
        if patterns:
            latest = patterns[-1]
            print(f"  {sym:15s} | {latest['type']:25s} | {latest['direction']}")

    save_results(all_levels)
    print(f"\n{'=' * 55}")
    return all_levels


if __name__ == "__main__":
    run()
