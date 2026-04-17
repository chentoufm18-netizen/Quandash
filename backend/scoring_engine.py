"""
Composite Scoring Engine
Combine COT + Economic + Retail Sentiment en un score final
Place ce fichier dans : ~/trading-dashboard/backend/scoring_engine.py
"""

import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_composite_scores():
    """
    Score composite pour chaque symbole:
    - COT Institutional Score: 50% weight
    - Economic Score: 25% weight  
    - Retail Sentiment (contrarian): 25% weight
    """
    cot_data = load_json("cot_data.json")
    eco_data = load_json("eco_data.json")
    sentiment_data = load_json("sentiment_data.json")

    if not cot_data:
        print("  [SCORE] Données COT non disponibles")
        return {}

    composite = {}
    cot_symbols = cot_data.get("data", {})
    eco_scores = eco_data.get("currency_scores", {}) if eco_data else {}
    sent_symbols = sentiment_data.get("data", {}) if sentiment_data else {}

    for symbol, cot in cot_symbols.items():
        cot_score = cot.get("sentiment_score", 0)

        # Economic score for the relevant currency
        eco_score = 0
        category = cot.get("category", "")
        if category == "forex":
            # Extract base currency from pair name
            parts = symbol.split("/")
            if len(parts) == 2:
                base_currency = parts[0] if parts[0] != "USD" else parts[1]
                # For USD/XXX pairs, the economic data affects inversely
                if parts[0] == "USD":
                    eco_score = eco_scores.get("USD", {}).get("normalized", 0) - eco_scores.get(base_currency, {}).get("normalized", 0)
                else:
                    eco_score = eco_scores.get(base_currency, {}).get("normalized", 0) - eco_scores.get("USD", {}).get("normalized", 0)
        elif category == "index":
            eco_score = eco_scores.get("USD", {}).get("normalized", 0)
        elif category == "commodity":
            eco_score = -eco_scores.get("USD", {}).get("normalized", 0)  # Commodities inverse to USD

        # Retail sentiment (contrarian)
        sent_score = 0
        if symbol in sent_symbols:
            sent_score = sent_symbols[symbol].get("contrarian_score", 0)

        # Weights
        w_cot = 0.50
        w_eco = 0.25
        w_sent = 0.25

        # If sentiment data is missing, redistribute weight to COT
        if symbol not in sent_symbols:
            w_cot = 0.65
            w_eco = 0.35
            w_sent = 0

        raw = (cot_score * w_cot) + (eco_score * w_eco) + (sent_score * w_sent)
        final_score = max(-100, min(100, raw))

        if final_score > 25:
            bias = "BULLISH"
        elif final_score < -25:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        composite[symbol] = {
            "symbol": symbol,
            "category": category,
            "composite_score": round(final_score, 1),
            "composite_bias": bias,
            "cot_score": round(cot_score, 1),
            "eco_score": round(eco_score, 1),
            "sentiment_score": round(sent_score, 1),
            "weights": {"cot": w_cot, "eco": w_eco, "sentiment": w_sent},
            # Keep original COT data for display
            "smart_money_net": cot.get("smart_money_net", 0),
            "smart_money_change": cot.get("smart_money_change", 0),
            "smart_money_long": cot.get("smart_money_long", 0),
            "smart_money_short": cot.get("smart_money_short", 0),
            "commercial_net": cot.get("commercial_net", 0),
            "open_interest": cot.get("open_interest", 0),
            "latest_date": cot.get("latest_date", ""),
            "cftc_code": cot.get("cftc_code", ""),
            "history": cot.get("history", []),
            # Retail data if available
            "retail_long_pct": sent_symbols.get(symbol, {}).get("retail_long_pct"),
            "retail_short_pct": sent_symbols.get(symbol, {}).get("retail_short_pct"),
            "retail_bias": sent_symbols.get(symbol, {}).get("retail_bias"),
            "crowd_extreme": sent_symbols.get(symbol, {}).get("crowd_extreme", False),
        }

    return composite


def save_composite(composite):
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, "composite_scores.json")

    sorted_data = dict(sorted(composite.items(), key=lambda x: abs(x[1]["composite_score"]), reverse=True))

    output = {
        "last_updated": datetime.now().isoformat(),
        "count": len(sorted_data),
        "data": sorted_data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  [SCORE] Sauvegardé: {filepath}")
    return filepath


def run():
    print("=" * 55)
    print("  COMPOSITE SCORING ENGINE — Trading Dashboard")
    print("=" * 55)

    composite = calculate_composite_scores()

    if not composite:
        print("  [SCORE] Aucune donnée à traiter")
        return {}

    print(f"\n  {'─' * 65}")
    print(f"  {'Symbol':15s} | {'Composite':>9s} | {'COT':>6s} | {'Eco':>6s} | {'Sent':>6s} | Bias")
    print(f"  {'─' * 65}")

    for sym, d in sorted(composite.items(), key=lambda x: x[1]["composite_score"], reverse=True):
        dot = "🟢" if d["composite_bias"] == "BULLISH" else "🔴" if d["composite_bias"] == "BEARISH" else "⚪"
        print(f"  {dot} {sym:13s} | {d['composite_score']:>+8.1f} | {d['cot_score']:>+5.1f} | {d['eco_score']:>+5.1f} | {d['sentiment_score']:>+5.1f} | {d['composite_bias']}")

    save_composite(composite)
    print(f"\n{'=' * 55}")
    return composite


if __name__ == "__main__":
    run()
