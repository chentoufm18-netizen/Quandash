"""
Economic Calendar Fetcher
Récupère le calendrier économique depuis Forex Factory
Place ce fichier dans : ~/trading-dashboard/backend/eco_fetcher.py
"""

import requests
import json
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Mapping devise → symboles COT affectés
CURRENCY_IMPACT = {
    "USD": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "USD/CAD", "AUD/USD", "NZD/USD", "S&P 500", "Nasdaq 100", "Dow Jones", "Gold", "Crude Oil WTI"],
    "EUR": ["EUR/USD"],
    "GBP": ["GBP/USD"],
    "JPY": ["USD/JPY"],
    "CHF": ["USD/CHF"],
    "CAD": ["USD/CAD"],
    "AUD": ["AUD/USD"],
    "NZD": ["NZD/USD"],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.forexfactory.com/",
}


# ============================================================
# FOREX FACTORY SCRAPER
# ============================================================

def fetch_forex_factory():
    """Scrape le calendrier économique de Forex Factory."""
    url = "https://www.forexfactory.com/calendar"
    print("  [ECO] Scraping Forex Factory...")

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ECO] Erreur Forex Factory: {e}")
        return []

    soup = BeautifulSoup(response.text, "lxml")
    events = []

    # Parser les lignes du calendrier
    rows = soup.select("tr.calendar__row")
    current_date = ""

    for row in rows:
        try:
            # Date (parfois dans une ligne séparée)
            date_cell = row.select_one(".calendar__date")
            if date_cell and date_cell.text.strip():
                current_date = date_cell.text.strip()

            # Heure
            time_cell = row.select_one(".calendar__time")
            time_str = time_cell.text.strip() if time_cell else ""

            # Devise
            currency_cell = row.select_one(".calendar__currency")
            currency = currency_cell.text.strip() if currency_cell else ""

            # Impact (nombre de bulles rouges)
            impact_cell = row.select_one(".calendar__impact")
            impact = "Low"
            if impact_cell:
                spans = impact_cell.select("span")
                high_count = len([s for s in spans if "high" in s.get("class", [])])
                med_count = len([s for s in spans if "medium" in s.get("class", [])])
                if high_count > 0:
                    impact = "High"
                elif med_count > 0:
                    impact = "Medium"

            # Titre de l'événement
            title_cell = row.select_one(".calendar__event-title")
            title = title_cell.text.strip() if title_cell else ""

            # Valeurs (actuel, prévision, précédent)
            actual_cell = row.select_one(".calendar__actual")
            forecast_cell = row.select_one(".calendar__forecast")
            previous_cell = row.select_one(".calendar__previous")

            actual = actual_cell.text.strip() if actual_cell else ""
            forecast = forecast_cell.text.strip() if forecast_cell else ""
            previous = previous_cell.text.strip() if previous_cell else ""

            if not title or not currency:
                continue

            # Déterminer le sentiment (actual vs forecast)
            sentiment = analyze_sentiment(title, actual, forecast, previous)

            events.append({
                "date": current_date,
                "time": time_str,
                "currency": currency,
                "impact": impact,
                "title": title,
                "actual": actual,
                "forecast": forecast,
                "previous": previous,
                "sentiment": sentiment,
                "affected_symbols": CURRENCY_IMPACT.get(currency, []),
            })

        except Exception as e:
            continue

    print(f"  [ECO] {len(events)} événements trouvés")
    return events


def analyze_sentiment(title, actual, forecast, previous):
    """
    Analyse le sentiment d'un événement économique.
    Retourne: 'BULLISH', 'BEARISH', 'NEUTRAL', ou 'PENDING'
    """
    if not actual:
        return "PENDING"

    # Nettoyer les valeurs
    def clean_val(v):
        if not v:
            return None
        v = v.replace("%", "").replace("K", "000").replace("M", "000000").replace("B", "000000000")
        v = v.replace(",", "").strip()
        try:
            return float(v)
        except ValueError:
            return None

    act = clean_val(actual)
    fct = clean_val(forecast)
    prv = clean_val(previous)

    if act is None:
        return "NEUTRAL"

    # Mots-clés négatifs dans le titre (pour inverser la logique)
    negative_keywords = ["unemployment", "jobless", "claims", "deficit", "debt", "inflation cpi", "ppi"]
    is_negative_indicator = any(kw in title.lower() for kw in negative_keywords)

    # Comparer actual vs forecast
    if fct is not None:
        diff_pct = ((act - fct) / abs(fct)) * 100 if fct != 0 else 0
        if diff_pct > 2:
            return "BEARISH" if is_negative_indicator else "BULLISH"
        elif diff_pct < -2:
            return "BULLISH" if is_negative_indicator else "BEARISH"

    # Comparer actual vs previous si pas de forecast
    if prv is not None:
        if act > prv:
            return "BEARISH" if is_negative_indicator else "BULLISH"
        elif act < prv:
            return "BULLISH" if is_negative_indicator else "BEARISH"

    return "NEUTRAL"


# ============================================================
# FALLBACK : DONNÉES STATIQUES SI SCRAPING ÉCHOUE
# ============================================================

def get_fallback_events():
    """Retourne des événements types si le scraping échoue."""
    today = datetime.now().strftime("%a %b %d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%a %b %d")

    return [
        {"date": today, "time": "08:30", "currency": "USD", "impact": "High",
         "title": "Non-Farm Payrolls", "actual": "", "forecast": "185K", "previous": "175K",
         "sentiment": "PENDING", "affected_symbols": CURRENCY_IMPACT["USD"]},
        {"date": today, "time": "08:30", "currency": "USD", "impact": "High",
         "title": "Unemployment Rate", "actual": "", "forecast": "3.9%", "previous": "3.9%",
         "sentiment": "PENDING", "affected_symbols": CURRENCY_IMPACT["USD"]},
        {"date": today, "time": "10:00", "currency": "USD", "impact": "Medium",
         "title": "ISM Manufacturing PMI", "actual": "", "forecast": "48.5", "previous": "47.8",
         "sentiment": "PENDING", "affected_symbols": CURRENCY_IMPACT["USD"]},
        {"date": tomorrow, "time": "03:00", "currency": "EUR", "impact": "High",
         "title": "ECB Interest Rate Decision", "actual": "", "forecast": "3.65%", "previous": "3.65%",
         "sentiment": "PENDING", "affected_symbols": CURRENCY_IMPACT["EUR"]},
        {"date": tomorrow, "time": "09:30", "currency": "GBP", "impact": "High",
         "title": "UK CPI y/y", "actual": "", "forecast": "2.8%", "previous": "2.6%",
         "sentiment": "PENDING", "affected_symbols": CURRENCY_IMPACT["GBP"]},
    ]


# ============================================================
# SCORING ÉCONOMIQUE PAR DEVISE
# ============================================================

def calculate_eco_scores(events):
    """
    Calcule un score économique par devise basé sur
    les événements récents et à venir à fort impact.
    """
    currency_scores = {}

    for event in events:
        currency = event.get("currency", "")
        if not currency:
            continue

        impact = event.get("impact", "Low")
        sentiment = event.get("sentiment", "NEUTRAL")

        # Poids selon l'impact
        weight = {"High": 3, "Medium": 1.5, "Low": 0.5}.get(impact, 0.5)

        # Score selon le sentiment
        score_delta = {"BULLISH": weight, "BEARISH": -weight, "NEUTRAL": 0, "PENDING": 0}.get(sentiment, 0)

        if currency not in currency_scores:
            currency_scores[currency] = {"score": 0, "events": 0, "high_impact": 0}

        currency_scores[currency]["score"] += score_delta
        currency_scores[currency]["events"] += 1
        if impact == "High":
            currency_scores[currency]["high_impact"] += 1

    # Normaliser les scores
    for currency in currency_scores:
        n = currency_scores[currency]["events"]
        if n > 0:
            raw = currency_scores[currency]["score"]
            currency_scores[currency]["normalized"] = max(-100, min(100, raw * 10))
        else:
            currency_scores[currency]["normalized"] = 0

    return currency_scores


# ============================================================
# SAUVEGARDE
# ============================================================

def save_results(events, eco_scores):
    """Sauvegarder les données économiques."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Séparer les événements par impact
    high_impact = [e for e in events if e["impact"] == "High"]
    pending = [e for e in events if e["sentiment"] == "PENDING"]
    released = [e for e in events if e["sentiment"] not in ["PENDING", "NEUTRAL"] and e["actual"]]

    output = {
        "last_updated": datetime.now().isoformat(),
        "total_events": len(events),
        "high_impact_count": len(high_impact),
        "currency_scores": eco_scores,
        "events": events,
        "high_impact_events": high_impact,
        "upcoming_events": pending[:10],
        "released_events": released[:10],
    }

    filepath = os.path.join(DATA_DIR, "eco_data.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  [ECO] Sauvegardé: {filepath}")
    return filepath


# ============================================================
# MAIN
# ============================================================

def run():
    print("=" * 55)
    print("  ECO CALENDAR FETCHER — Trading Dashboard")
    print("=" * 55)

    # Tenter le scraping
    events = fetch_forex_factory()

    # Fallback si rien trouvé
    if not events:
        print("  [ECO] Scraping vide, utilisation des données de référence...")
        events = get_fallback_events()

    # Calculer les scores économiques
    eco_scores = calculate_eco_scores(events)

    # Afficher résumé
    print(f"\n  {'─' * 50}")
    print(f"  {len(events)} événements | {len([e for e in events if e['impact'] == 'High'])} High Impact")
    print(f"  {'─' * 50}")

    print("\n  SCORES ÉCONOMIQUES PAR DEVISE:")
    for currency, data in sorted(eco_scores.items(), key=lambda x: x[1]["normalized"], reverse=True):
        score = data["normalized"]
        bar = "🟢" if score > 0 else "🔴" if score < 0 else "⚪"
        print(f"  {bar} {currency:4s} | Score: {score:>6.1f} | Events: {data['events']} | High: {data['high_impact']}")

    print("\n  ÉVÉNEMENTS HIGH IMPACT:")
    for e in events:
        if e["impact"] == "High":
            status = e["sentiment"] if e["actual"] else "⏳ PENDING"
            print(f"  [{e['currency']:3s}] {e['title'][:35]:35s} | {status}")

    save_results(events, eco_scores)
    print(f"\n{'=' * 55}")
    return events, eco_scores


if __name__ == "__main__":
    run()
