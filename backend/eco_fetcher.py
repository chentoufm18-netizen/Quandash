"""
Economic Calendar Fetcher v2
Source primaire : FF JSON feed (nfs.faireconomy.media) — fiable, pas de 403
Fallback : Forex Factory scraping
Nouveau : impact_explanation — explication textuelle de chaque news publiée
"""

import requests
import json
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

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
    "Accept": "application/json, text/html,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

# ============================================================
# KNOWLEDGE BASE — explications des indicateurs
# ============================================================

EVENT_KNOWLEDGE = {
    "non-farm payrolls": {"negative": False,
        "above": "More jobs than expected → strong economy → USD bullish. Fed may delay rate cuts.",
        "below": "Fewer jobs than expected → slowdown risk → USD bearish. Fed more likely to cut rates."},
    "nfp": {"negative": False,
        "above": "More jobs than expected → strong economy → USD bullish. Fed may delay rate cuts.",
        "below": "Fewer jobs than expected → slowdown risk → USD bearish. Fed more likely to cut rates."},
    "unemployment rate": {"negative": True,
        "above": "Higher unemployment than expected → labor market weakening → USD bearish.",
        "below": "Lower unemployment than expected → tight labor market → USD bullish."},
    "jobless claims": {"negative": True,
        "above": "More claims than expected → labor market softening → USD bearish.",
        "below": "Fewer claims than expected → tight labor market → USD bullish."},
    "initial jobless": {"negative": True,
        "above": "More initial claims → job market weakening → USD bearish.",
        "below": "Fewer initial claims → solid job market → USD bullish."},
    "cpi": {"negative": False,
        "above": "Inflation above forecast → hawkish Fed pressure → USD bullish near-term.",
        "below": "Inflation below forecast → disinflation → USD bearish, rate cuts more likely."},
    "core cpi": {"negative": False,
        "above": "Core inflation hot → Fed stays restrictive → USD bullish.",
        "below": "Core inflation cooling → Fed can ease → USD bearish."},
    "ppi": {"negative": False,
        "above": "Producer prices rising → upstream inflation → USD bullish.",
        "below": "Producer prices falling → disinflation pipeline → USD bearish."},
    "pce": {"negative": False,
        "above": "PCE above target → Fed hawkish → USD bullish.",
        "below": "PCE softening → Fed dovish → USD bearish."},
    "gdp": {"negative": False,
        "above": "GDP above forecast → strong growth → currency bullish.",
        "below": "GDP below forecast → economic slowdown → currency bearish."},
    "retail sales": {"negative": False,
        "above": "Consumer spending strong → economy solid → USD bullish.",
        "below": "Consumer spending weak → demand slowing → USD bearish."},
    "ism manufacturing": {"negative": False,
        "above": "Manufacturing expanding faster than expected → USD bullish.",
        "below": "Manufacturing contracting more than expected → USD bearish."},
    "ism services": {"negative": False,
        "above": "Services sector beats → broad economy strong → USD bullish.",
        "below": "Services sector misses → slowdown risk → USD bearish."},
    "pmi": {"negative": False,
        "above": "PMI beat → business activity expanding → currency bullish.",
        "below": "PMI miss → activity contracting → currency bearish."},
    "interest rate": {"negative": False,
        "above": "Rate higher than expected → hawkish surprise → currency strongly bullish.",
        "below": "Rate lower than expected → dovish surprise → currency strongly bearish."},
    "rate decision": {"negative": False,
        "above": "More hawkish than expected → currency bullish.",
        "below": "More dovish than expected → currency bearish."},
    "fomc": {"negative": False,
        "above": "Fed more hawkish than expected → USD bullish.",
        "below": "Fed more dovish than expected → USD bearish."},
    "ecb": {"negative": False,
        "above": "ECB more hawkish than expected → EUR bullish.",
        "below": "ECB more dovish than expected → EUR bearish."},
    "boe": {"negative": False,
        "above": "BoE more hawkish than expected → GBP bullish.",
        "below": "BoE more dovish than expected → GBP bearish."},
    "trade balance": {"negative": False,
        "above": "Trade surplus better than expected → currency bullish.",
        "below": "Trade deficit wider than expected → currency bearish."},
    "housing starts": {"negative": False,
        "above": "More construction than expected → healthy economy → USD bullish.",
        "below": "Less construction → slowdown signal → USD bearish."},
    "building permits": {"negative": False,
        "above": "More permits → forward construction strong → USD bullish.",
        "below": "Fewer permits → slowdown ahead → USD bearish."},
    "durable goods": {"negative": False,
        "above": "Orders beat → business investment strong → USD bullish.",
        "below": "Orders missed → capex slowing → USD bearish."},
    "consumer confidence": {"negative": False,
        "above": "Confidence above forecast → spending expected to rise → USD bullish.",
        "below": "Confidence below forecast → spending risk → USD bearish."},
    "michigan": {"negative": False,
        "above": "Sentiment beat → consumer optimism → USD bullish.",
        "below": "Sentiment missed → consumer pessimism → USD bearish."},
    "crude oil": {"negative": True,
        "above": "More supply than expected → oil bearish pressure.",
        "below": "Less supply than expected → oil bullish pressure."},
    "inflation": {"negative": False,
        "above": "Inflation above target → central bank hawkish pressure → currency bullish near-term.",
        "below": "Inflation below target → easing likely → currency bearish."},
    "employment change": {"negative": False,
        "above": "More jobs than expected → labor market tight → currency bullish.",
        "below": "Fewer jobs than expected → labor market loosening → currency bearish."},
    "average hourly earnings": {"negative": False,
        "above": "Wages rising faster → wage inflation → USD bullish (Fed hawkish).",
        "below": "Wages rising slower → less inflation pressure → USD bearish."},
}


def get_event_knowledge(title):
    title_lower = title.lower()
    for key, data in EVENT_KNOWLEDGE.items():
        if key in title_lower:
            return data
    return None


# ============================================================
# SOURCE 1 — FF JSON FEED (fiable, pas de 403)
# ============================================================

def fetch_ff_json():
    urls = [
        "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
        "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
    ]
    all_events = []

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"  [ECO] JSON feed HTTP {resp.status_code}: {url}")
                continue

            data = resp.json()
            print(f"  [ECO] JSON feed OK: {len(data)} events from {url.split('/')[-1]}")

            for item in data:
                impact_raw = item.get("impact", "").lower()
                if impact_raw == "high":
                    impact = "High"
                elif impact_raw == "medium":
                    impact = "Medium"
                else:
                    impact = "Low"

                date_str = item.get("date", "")
                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    date_fmt = dt.strftime("%a %b %d")
                    time_fmt = dt.strftime("%H:%M")
                except Exception:
                    date_fmt = date_str[:10]
                    time_fmt = ""

                title = item.get("title", "")
                currency = item.get("country", "").upper()
                actual = item.get("actual", "") or ""
                forecast = item.get("forecast", "") or ""
                previous = item.get("previous", "") or ""

                sentiment = analyze_sentiment(title, actual, forecast, previous)
                explanation = generate_explanation(title, actual, forecast, previous, currency)

                all_events.append({
                    "date": date_fmt,
                    "time": time_fmt,
                    "currency": currency,
                    "impact": impact,
                    "title": title,
                    "actual": actual,
                    "forecast": forecast,
                    "previous": previous,
                    "sentiment": sentiment,
                    "impact_explanation": explanation,
                    "affected_symbols": CURRENCY_IMPACT.get(currency, []),
                })

        except Exception as e:
            print(f"  [ECO] JSON feed error: {e}")
            continue

    return all_events


# ============================================================
# SOURCE 2 — FOREX FACTORY SCRAPING (fallback)
# ============================================================

def fetch_forex_factory_scrape():
    url = "https://www.forexfactory.com/calendar"
    print("  [ECO] Fallback: scraping Forex Factory...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ECO] Scraping failed: {e}")
        return []

    soup = BeautifulSoup(response.text, "lxml")
    events = []
    rows = soup.select("tr.calendar__row")
    current_date = ""

    for row in rows:
        try:
            date_cell = row.select_one(".calendar__date")
            if date_cell and date_cell.text.strip():
                current_date = date_cell.text.strip()

            time_cell = row.select_one(".calendar__time")
            time_str = time_cell.text.strip() if time_cell else ""
            currency_cell = row.select_one(".calendar__currency")
            currency = currency_cell.text.strip() if currency_cell else ""
            impact_cell = row.select_one(".calendar__impact")
            impact = "Low"
            if impact_cell:
                spans = impact_cell.select("span")
                if len([s for s in spans if "high" in s.get("class", [])]) > 0:
                    impact = "High"
                elif len([s for s in spans if "medium" in s.get("class", [])]) > 0:
                    impact = "Medium"

            title_cell = row.select_one(".calendar__event-title")
            title = title_cell.text.strip() if title_cell else ""
            actual = (row.select_one(".calendar__actual") or type('', (), {'text': ''})()).text.strip()
            forecast = (row.select_one(".calendar__forecast") or type('', (), {'text': ''})()).text.strip()
            previous = (row.select_one(".calendar__previous") or type('', (), {'text': ''})()).text.strip()

            if not title or not currency:
                continue

            sentiment = analyze_sentiment(title, actual, forecast, previous)
            explanation = generate_explanation(title, actual, forecast, previous, currency)

            events.append({
                "date": current_date, "time": time_str, "currency": currency,
                "impact": impact, "title": title, "actual": actual,
                "forecast": forecast, "previous": previous,
                "sentiment": sentiment, "impact_explanation": explanation,
                "affected_symbols": CURRENCY_IMPACT.get(currency, []),
            })
        except Exception:
            continue

    print(f"  [ECO] Scraping: {len(events)} events")
    return events


# ============================================================
# ANALYSE SENTIMENT
# ============================================================

def analyze_sentiment(title, actual, forecast, previous):
    if not actual:
        return "PENDING"

    def clean_val(v):
        if not v:
            return None
        v = str(v).replace("%", "").replace("K", "000").replace("M", "000000").replace("B", "000000000")
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

    knowledge = get_event_knowledge(title)
    is_negative = knowledge["negative"] if knowledge else False

    if fct is not None and fct != 0:
        diff_pct = ((act - fct) / abs(fct)) * 100
        if diff_pct > 2:
            return "BEARISH" if is_negative else "BULLISH"
        elif diff_pct < -2:
            return "BULLISH" if is_negative else "BEARISH"

    if prv is not None:
        if act > prv:
            return "BEARISH" if is_negative else "BULLISH"
        elif act < prv:
            return "BULLISH" if is_negative else "BEARISH"

    return "NEUTRAL"


# ============================================================
# GÉNÉRATION D'EXPLICATION
# ============================================================

def generate_explanation(title, actual, forecast, previous, currency):
    if not actual:
        return None

    def clean_val(v):
        if not v:
            return None
        v = str(v).replace("%", "").replace("K", "000").replace("M", "000000").replace("B", "000000000")
        v = v.replace(",", "").strip()
        try:
            return float(v)
        except ValueError:
            return None

    act = clean_val(actual)
    fct = clean_val(forecast)
    prv = clean_val(previous)
    knowledge = get_event_knowledge(title)
    is_negative = knowledge["negative"] if knowledge else False

    if act is not None and fct is not None and fct != 0:
        diff = act - fct
        diff_pct = (diff / abs(fct)) * 100
        sign = "+" if diff > 0 else ""

        if abs(diff_pct) <= 2:
            return f"In line with forecast ({actual} vs {forecast}). No significant surprise — limited market impact expected."

        beat = diff > 0
        if is_negative:
            beat = not beat

        direction = "beat" if beat else "missed"
        surprise = f"Actual {actual} vs forecast {forecast} ({sign}{diff_pct:.1f}%)"

        if knowledge:
            base = knowledge["above"] if direction == "beat" else knowledge["below"]
            return f"{surprise} — {base}"
        else:
            bias = "bullish" if beat else "bearish"
            return f"{surprise} — {'Better' if beat else 'Worse'} than expected → {currency} {bias} pressure."

    elif act is not None and prv is not None:
        diff = act - prv
        sign = "+" if diff > 0 else ""
        improving = diff > 0
        if is_negative:
            improving = not improving

        base_text = ""
        if knowledge:
            base_text = " — " + (knowledge["above"] if improving else knowledge["below"])

        return f"Actual {actual} vs previous {previous} ({sign}{diff:.3g}){base_text}"

    return f"Published: {actual}. Awaiting comparison data."


# ============================================================
# SCORING
# ============================================================

def calculate_eco_scores(events):
    currency_scores = {}
    for event in events:
        currency = event.get("currency", "")
        if not currency:
            continue
        impact = event.get("impact", "Low")
        sentiment = event.get("sentiment", "NEUTRAL")
        weight = {"High": 3, "Medium": 1.5, "Low": 0.5}.get(impact, 0.5)
        score_delta = {"BULLISH": weight, "BEARISH": -weight, "NEUTRAL": 0, "PENDING": 0}.get(sentiment, 0)
        if currency not in currency_scores:
            currency_scores[currency] = {"score": 0, "events": 0, "high_impact": 0}
        currency_scores[currency]["score"] += score_delta
        currency_scores[currency]["events"] += 1
        if impact == "High":
            currency_scores[currency]["high_impact"] += 1
    for currency in currency_scores:
        n = currency_scores[currency]["events"]
        raw = currency_scores[currency]["score"]
        currency_scores[currency]["normalized"] = max(-100, min(100, raw * 10)) if n > 0 else 0
    return currency_scores


# ============================================================
# SAUVEGARDE
# ============================================================

def save_results(events, eco_scores):
    os.makedirs(DATA_DIR, exist_ok=True)
    high_impact = [e for e in events if e["impact"] == "High"]
    pending = [e for e in events if e["sentiment"] == "PENDING"]
    released = [e for e in events if e.get("impact_explanation")]

    output = {
        "last_updated": datetime.now().isoformat(),
        "total_events": len(events),
        "high_impact_count": len(high_impact),
        "currency_scores": eco_scores,
        "events": events,
        "high_impact_events": high_impact,
        "upcoming_events": pending[:10],
        "released_events": released[:20],
    }

    filepath = os.path.join(DATA_DIR, "eco_data.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"  [ECO] Saved: {filepath}")
    return filepath


# ============================================================
# MAIN
# ============================================================

def run():
    print("=" * 55)
    print("  ECO CALENDAR FETCHER v2")
    print("=" * 55)

    events = fetch_ff_json()

    if not events:
        print("  [ECO] JSON feed empty, trying FF scrape...")
        events = fetch_forex_factory_scrape()

    if not events:
        print("  [ECO] All sources failed, using static fallback...")
        today = datetime.now().strftime("%a %b %d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%a %b %d")
        events = [
            {"date": today, "time": "14:30", "currency": "USD", "impact": "High",
             "title": "Non-Farm Payrolls", "actual": "", "forecast": "185K", "previous": "175K",
             "sentiment": "PENDING", "impact_explanation": None, "affected_symbols": CURRENCY_IMPACT["USD"]},
            {"date": tomorrow, "time": "12:45", "currency": "EUR", "impact": "High",
             "title": "ECB Interest Rate Decision", "actual": "", "forecast": "2.65%", "previous": "2.65%",
             "sentiment": "PENDING", "impact_explanation": None, "affected_symbols": CURRENCY_IMPACT["EUR"]},
        ]

    eco_scores = calculate_eco_scores(events)

    released = [e for e in events if e.get("impact_explanation")]
    print(f"  {len(events)} events | {len([e for e in events if e['impact']=='High'])} High | {len(released)} published with explanation")

    save_results(events, eco_scores)
    print(f"\n{'=' * 55}")
    return events, eco_scores


if __name__ == "__main__":
    run()
