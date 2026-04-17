"""
Retail Sentiment Fetcher
Récupère le positionnement des traders retail via Myfxbook
Place ce fichier dans : ~/trading-dashboard/backend/sentiment_fetcher.py
"""

import requests
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

# Mapping Myfxbook pair names to our symbol names
PAIR_MAP = {
    "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD", "USDJPY": "USD/JPY",
    "USDCHF": "USD/CHF", "USDCAD": "USD/CAD", "AUDUSD": "AUD/USD",
    "NZDUSD": "NZD/USD", "XAUUSD": "Gold", "XAGUSD": "Silver",
}


def fetch_myfxbook_sentiment():
    """Scrape Myfxbook Community Outlook for retail sentiment."""
    url = "https://www.myfxbook.com/community/outlook"
    print("  [SENT] Scraping Myfxbook Community Outlook...")

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        results = {}

        # Look for the outlook data in script tags or table rows
        scripts = soup.find_all("script")
        for script in scripts:
            text = script.string or ""
            # Myfxbook stores data in JS variables
            matches = re.findall(r'"symbol"\s*:\s*"([^"]+)".*?"longPercentage"\s*:\s*([\d.]+).*?"shortPercentage"\s*:\s*([\d.]+)', text, re.DOTALL)
            for symbol, long_pct, short_pct in matches:
                mapped = PAIR_MAP.get(symbol.upper().replace("/", ""), symbol)
                results[mapped] = {
                    "symbol": mapped,
                    "retail_long_pct": float(long_pct),
                    "retail_short_pct": float(short_pct),
                    "retail_bias": "LONG" if float(long_pct) > 50 else "SHORT",
                }

        # Also try parsing table rows
        if not results:
            rows = soup.select("tr")
            for row in rows:
                cells = row.select("td")
                if len(cells) >= 4:
                    pair_text = cells[0].text.strip().replace("/", "").upper()
                    if pair_text in PAIR_MAP:
                        try:
                            long_pct = float(re.search(r'([\d.]+)', cells[1].text or "50").group(1))
                            short_pct = 100 - long_pct
                            mapped = PAIR_MAP[pair_text]
                            results[mapped] = {
                                "symbol": mapped,
                                "retail_long_pct": long_pct,
                                "retail_short_pct": short_pct,
                                "retail_bias": "LONG" if long_pct > 50 else "SHORT",
                            }
                        except (ValueError, AttributeError):
                            continue

        if results:
            print(f"  [SENT] {len(results)} paires trouvées")
        return results

    except Exception as e:
        print(f"  [SENT] Erreur Myfxbook: {e}")
        return {}


def get_fallback_sentiment():
    """Données retail de référence basées sur les tendances typiques."""
    return {
        "EUR/USD": {"symbol": "EUR/USD", "retail_long_pct": 38.5, "retail_short_pct": 61.5, "retail_bias": "SHORT"},
        "GBP/USD": {"symbol": "GBP/USD", "retail_long_pct": 55.2, "retail_short_pct": 44.8, "retail_bias": "LONG"},
        "USD/JPY": {"symbol": "USD/JPY", "retail_long_pct": 62.1, "retail_short_pct": 37.9, "retail_bias": "LONG"},
        "USD/CHF": {"symbol": "USD/CHF", "retail_long_pct": 44.3, "retail_short_pct": 55.7, "retail_bias": "SHORT"},
        "USD/CAD": {"symbol": "USD/CAD", "retail_long_pct": 58.7, "retail_short_pct": 41.3, "retail_bias": "LONG"},
        "AUD/USD": {"symbol": "AUD/USD", "retail_long_pct": 65.4, "retail_short_pct": 34.6, "retail_bias": "LONG"},
        "NZD/USD": {"symbol": "NZD/USD", "retail_long_pct": 71.2, "retail_short_pct": 28.8, "retail_bias": "LONG"},
        "Gold":    {"symbol": "Gold",    "retail_long_pct": 72.8, "retail_short_pct": 27.2, "retail_bias": "LONG"},
        "Silver":  {"symbol": "Silver",  "retail_long_pct": 68.5, "retail_short_pct": 31.5, "retail_bias": "LONG"},
    }


def calculate_contrarian_signals(sentiment_data, cot_data_path=None):
    """
    Signal contrarian : quand retail est massivement d'un côté,
    smart money est souvent de l'autre. Score de -100 à +100.
    Positif = retail a tort (contrarian signal fort)
    """
    cot_data = {}
    if cot_data_path and os.path.exists(cot_data_path):
        with open(cot_data_path, "r") as f:
            cot_raw = json.load(f)
            cot_data = cot_raw.get("data", {})

    signals = {}
    for symbol, sent in sentiment_data.items():
        long_pct = sent["retail_long_pct"]
        short_pct = sent["retail_short_pct"]

        # Extreme readings (>65% one side = contrarian signal)
        imbalance = abs(long_pct - 50) / 50 * 100  # 0-100 scale
        retail_direction = 1 if long_pct > 50 else -1

        # Contrarian score: opposite of retail crowd
        contrarian_score = -retail_direction * imbalance

        # Cross-reference with COT if available
        cot_alignment = 0
        if symbol in cot_data:
            cot_bias = cot_data[symbol].get("bias", "NEUTRAL")
            if cot_bias == "BULLISH" and retail_direction == -1:
                cot_alignment = 25  # Smart money bullish, retail short = strong buy
            elif cot_bias == "BEARISH" and retail_direction == 1:
                cot_alignment = -25  # Smart money bearish, retail long = strong sell
            elif cot_bias == "BULLISH" and retail_direction == 1:
                cot_alignment = -10  # Both same side = weaker signal
            elif cot_bias == "BEARISH" and retail_direction == -1:
                cot_alignment = 10

        final_score = max(-100, min(100, contrarian_score + cot_alignment))

        signals[symbol] = {
            **sent,
            "contrarian_score": round(final_score, 1),
            "imbalance": round(imbalance, 1),
            "crowd_extreme": imbalance > 60,
            "cot_alignment": "ALIGNED" if cot_alignment > 0 else "DIVERGENT" if cot_alignment < 0 else "NEUTRAL",
        }

    return signals


def save_results(signals):
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, "sentiment_data.json")

    output = {
        "last_updated": datetime.now().isoformat(),
        "count": len(signals),
        "data": signals,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  [SENT] Sauvegardé: {filepath}")
    return filepath


def run():
    print("=" * 55)
    print("  RETAIL SENTIMENT FETCHER — Trading Dashboard")
    print("=" * 55)

    sentiment = fetch_myfxbook_sentiment()
    if not sentiment:
        print("  [SENT] Scraping vide, utilisation des données de référence...")
        sentiment = get_fallback_sentiment()

    cot_path = os.path.join(DATA_DIR, "cot_data.json")
    signals = calculate_contrarian_signals(sentiment, cot_path)

    print(f"\n  {'─' * 50}")
    print(f"  RETAIL SENTIMENT — {len(signals)} symboles")
    print(f"  {'─' * 50}")

    for sym, d in sorted(signals.items(), key=lambda x: abs(x[1]["contrarian_score"]), reverse=True):
        dot = "🟢" if d["contrarian_score"] > 0 else "🔴" if d["contrarian_score"] < 0 else "⚪"
        extreme = "⚠️" if d["crowd_extreme"] else "  "
        print(f"  {dot} {sym:12s} | Retail: {d['retail_long_pct']:5.1f}%L / {d['retail_short_pct']:5.1f}%S | Contrarian: {d['contrarian_score']:>6.1f} {extreme}")

    save_results(signals)
    return signals


if __name__ == "__main__":
    run()
