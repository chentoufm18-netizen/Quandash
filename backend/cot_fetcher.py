"""
COT Data Fetcher v2 — Récupère les données COT (CFTC)
Fetches BOTH disaggregated (commodities) AND financial futures (forex/indices/crypto)
Place ce fichier dans : ~/trading-dashboard/backend/cot_fetcher.py
"""

import requests
import zipfile
import io
import csv
import json
import os
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

# Rapport DISAGGREGATED (commodités physiques)
DISAGG_SYMBOLS = {
    "088691": {"name": "Gold", "category": "commodity"},
    "084691": {"name": "Silver", "category": "commodity"},
    "067651": {"name": "Crude Oil WTI", "category": "commodity"},
    "023651": {"name": "Natural Gas", "category": "commodity"},
    "001602": {"name": "Wheat", "category": "commodity"},
    "002602": {"name": "Corn", "category": "commodity"},
    "005602": {"name": "Soybeans", "category": "commodity"},
    "073732": {"name": "Copper", "category": "commodity"},
}

# Rapport TRADERS IN FINANCIAL FUTURES (forex, indices, crypto)
TFF_SYMBOLS = {
    "099741": {"name": "EUR/USD", "category": "forex"},
    "096742": {"name": "GBP/USD", "category": "forex"},
    "097741": {"name": "USD/JPY", "category": "forex"},
    "098662": {"name": "USD/CHF", "category": "forex"},
    "090741": {"name": "USD/CAD", "category": "forex"},
    "232741": {"name": "AUD/USD", "category": "forex"},
    "112741": {"name": "NZD/USD", "category": "forex"},
    "13874P": {"name": "S&P 500", "category": "index"},
    "209742": {"name": "Nasdaq 100", "category": "index"},
    "124603": {"name": "Dow Jones", "category": "index"},
    "133741": {"name": "Bitcoin", "category": "crypto"},
    "146021": {"name": "Ethereum", "category": "crypto"},
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# ============================================================
# FETCHER
# ============================================================

def fetch_report(report_type, year=None):
    if year is None:
        year = datetime.now().year

    urls = {
        "disagg": f"https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip",
        "tff": f"https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip",
    }

    url = urls[report_type]
    print(f"  [{report_type.upper()}] Téléchargement depuis {url}...")

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  [{report_type.upper()}] Erreur: {e}")
        if year == datetime.now().year:
            print(f"  [{report_type.upper()}] Tentative {year - 1}...")
            return fetch_report(report_type, year - 1)
        return None

    z = zipfile.ZipFile(io.BytesIO(response.content))
    csv_filename = z.namelist()[0]
    print(f"  [{report_type.upper()}] Fichier: {csv_filename}")

    with z.open(csv_filename) as f:
        text = io.TextIOWrapper(f, encoding="utf-8")
        reader = csv.DictReader(text)
        rows = list(reader)

    print(f"  [{report_type.upper()}] {len(rows)} lignes chargées")
    return rows


def find_column(row, candidates):
    for c in candidates:
        if c in row:
            return c
    return None


def safe_int(value):
    try:
        return int(str(value).strip().replace(",", ""))
    except (ValueError, TypeError):
        return 0


# ============================================================
# PARSER DISAGGREGATED (Commodités)
# ============================================================

def parse_disagg(rows):
    results = {}
    if not rows:
        return results

    sample = rows[0]

    col_code = find_column(sample, ["CFTC_Contract_Market_Code", "CFTC Contract Market Code"])
    col_date = find_column(sample, ["Report_Leg_as_of_Date_", "As_of_Date_In_Form_YYMMDD", "As of Date in Form YYYY-MM-DD"])
    col_mm_long = find_column(sample, ["M_Money_Positions_Long_All", "M_Money_Positions_Long_ALL", "Money Manager Longs"])
    col_mm_short = find_column(sample, ["M_Money_Positions_Short_All", "M_Money_Positions_Short_ALL", "Money Manager Shorts"])
    col_oi = find_column(sample, ["Open_Interest_All", "Open_Interest_ALL", "Open Interest (All)"])
    col_swap_long = find_column(sample, ["Swap_Positions_Long_All", "Swap__Positions_Long_All", "Swap_Positions_Long_ALL"])
    col_swap_short = find_column(sample, ["Swap_Positions_Short_All", "Swap__Positions_Short_All", "Swap_Positions_Short_ALL"])
    col_prod_long = find_column(sample, ["Prod_Merc_Positions_Long_All", "Prod_Merc_Positions_Long_ALL"])
    col_prod_short = find_column(sample, ["Prod_Merc_Positions_Short_All", "Prod_Merc_Positions_Short_ALL"])

    if not col_code or not col_mm_long:
        print("  [DISAGG] Colonnes introuvables. Disponibles:")
        print(f"  {[k for k in sample.keys() if 'Money' in k or 'money' in k or 'Prod' in k]}")
        return results

    print(f"  [DISAGG] Smart money col: {col_mm_long} / {col_mm_short}")

    for code, info in DISAGG_SYMBOLS.items():
        symbol_rows = [r for r in rows if r.get(col_code, "").strip() == code]
        if not symbol_rows:
            continue

        symbol_rows.sort(key=lambda r: r.get(col_date, ""), reverse=True)

        history = []
        for row in symbol_rows[:12]:
            mm_long = safe_int(row.get(col_mm_long, 0))
            mm_short = safe_int(row.get(col_mm_short, 0))
            sw_long = safe_int(row.get(col_swap_long, 0)) if col_swap_long else 0
            sw_short = safe_int(row.get(col_swap_short, 0)) if col_swap_short else 0
            pr_long = safe_int(row.get(col_prod_long, 0)) if col_prod_long else 0
            pr_short = safe_int(row.get(col_prod_short, 0)) if col_prod_short else 0
            oi = safe_int(row.get(col_oi, 0))

            history.append({
                "date": row.get(col_date, "").strip(),
                "smart_money": {"long": mm_long, "short": mm_short, "net": mm_long - mm_short},
                "swap_dealers": {"long": sw_long, "short": sw_short, "net": sw_long - sw_short},
                "commercials": {"long": pr_long, "short": pr_short, "net": pr_long - pr_short},
                "open_interest": oi,
            })

        if history:
            results[info["name"]] = build_result(info, code, history)

    return results


# ============================================================
# PARSER TFF (Financial Futures)
# ============================================================

def parse_tff(rows):
    results = {}
    if not rows:
        return results

    sample = rows[0]

    col_code = find_column(sample, ["CFTC_Contract_Market_Code", "CFTC Contract Market Code"])
    col_date = find_column(sample, ["Report_Leg_as_of_Date_", "As_of_Date_In_Form_YYMMDD", "As of Date in Form YYYY-MM-DD"])
    col_am_long = find_column(sample, ["Asset_Mgr_Positions_Long_All", "Asset_Mgr_Positions_Long_ALL"])
    col_am_short = find_column(sample, ["Asset_Mgr_Positions_Short_All", "Asset_Mgr_Positions_Short_ALL"])
    col_lev_long = find_column(sample, ["Lev_Money_Positions_Long_All", "Lev_Money_Positions_Long_ALL"])
    col_lev_short = find_column(sample, ["Lev_Money_Positions_Short_All", "Lev_Money_Positions_Short_ALL"])
    col_deal_long = find_column(sample, ["Dealer_Positions_Long_All", "Dealer_Positions_Long_ALL"])
    col_deal_short = find_column(sample, ["Dealer_Positions_Short_All", "Dealer_Positions_Short_ALL"])
    col_oi = find_column(sample, ["Open_Interest_All", "Open_Interest_ALL", "Open Interest (All)"])

    if not col_code or not col_am_long:
        print("  [TFF] Colonnes introuvables. Disponibles:")
        print(f"  {[k for k in sample.keys() if 'Asset' in k or 'Lev' in k or 'Deal' in k]}")
        return results

    print(f"  [TFF] Asset Mgr: {col_am_long} / {col_am_short}")
    print(f"  [TFF] Lev Funds: {col_lev_long} / {col_lev_short}")

    for code, info in TFF_SYMBOLS.items():
        symbol_rows = [r for r in rows if r.get(col_code, "").strip() == code]
        if not symbol_rows:
            continue

        symbol_rows.sort(key=lambda r: r.get(col_date, ""), reverse=True)

        history = []
        for row in symbol_rows[:12]:
            am_long = safe_int(row.get(col_am_long, 0))
            am_short = safe_int(row.get(col_am_short, 0))
            lev_long = safe_int(row.get(col_lev_long, 0))
            lev_short = safe_int(row.get(col_lev_short, 0))
            dl_long = safe_int(row.get(col_deal_long, 0))
            dl_short = safe_int(row.get(col_deal_short, 0))
            oi = safe_int(row.get(col_oi, 0))

            history.append({
                "date": row.get(col_date, "").strip(),
                "smart_money": {"long": am_long, "short": am_short, "net": am_long - am_short},
                "leveraged_funds": {"long": lev_long, "short": lev_short, "net": lev_long - lev_short},
                "commercials": {"long": dl_long, "short": dl_short, "net": dl_long - dl_short},
                "open_interest": oi,
            })

        if history:
            results[info["name"]] = build_result(info, code, history)

    return results


# ============================================================
# SCORING
# ============================================================

def build_result(info, code, history):
    latest = history[0]
    previous = history[1] if len(history) > 1 else latest

    sm_net = latest["smart_money"]["net"]
    sm_change = sm_net - previous["smart_money"]["net"]
    score = calculate_sentiment_score(history)

    if score > 25:
        bias = "BULLISH"
    elif score < -25:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    return {
        "symbol": info["name"],
        "category": info["category"],
        "cftc_code": code,
        "latest_date": latest["date"],
        "bias": bias,
        "sentiment_score": round(score, 1),
        "smart_money_net": sm_net,
        "smart_money_change": sm_change,
        "smart_money_long": latest["smart_money"]["long"],
        "smart_money_short": latest["smart_money"]["short"],
        "commercial_net": latest["commercials"]["net"],
        "open_interest": latest["open_interest"],
        "history": history[:8],
    }


def calculate_sentiment_score(history):
    if not history:
        return 0

    latest = history[0]
    sm_net = latest["smart_money"]["net"]
    oi = latest["open_interest"]

    # 1. Position nette relative (40%)
    relative = (sm_net / oi * 100) if oi > 0 else 0

    # 2. Tendance 4 semaines (35%)
    trend = 0
    if len(history) >= 4:
        nets = [h["smart_money"]["net"] for h in history[:4]]
        raw_trend = nets[0] - nets[-1]
        avg_oi = sum(h["open_interest"] for h in history[:4]) / 4
        if avg_oi > 0:
            trend = (raw_trend / avg_oi) * 100

    # 3. Accélération (25%)
    accel = 0
    if len(history) >= 3:
        ch1 = history[0]["smart_money"]["net"] - history[1]["smart_money"]["net"]
        ch2 = history[1]["smart_money"]["net"] - history[2]["smart_money"]["net"]
        avg_oi = (history[0]["open_interest"] + history[1]["open_interest"]) / 2
        if avg_oi > 0:
            accel = ((ch1 - ch2) / avg_oi) * 100

    raw_score = (relative * 0.40) + (trend * 0.35) + (accel * 0.25)
    return max(-100, min(100, raw_score * 4))


# ============================================================
# SAUVEGARDE
# ============================================================

def save_results(results, filename="cot_data.json"):
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)

    sorted_data = dict(sorted(results.items(), key=lambda x: abs(x[1]["sentiment_score"]), reverse=True))

    output = {
        "last_updated": datetime.now().isoformat(),
        "symbols_count": len(sorted_data),
        "data": sorted_data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[COT] Sauvegardé: {filepath}")
    return filepath


# ============================================================
# MAIN
# ============================================================

def run():
    print("=" * 55)
    print("  COT DATA FETCHER v2 — Trading Dashboard")
    print("=" * 55)

    all_results = {}

    print("\n[1/2] Rapport DISAGGREGATED (commodités)...")
    disagg_rows = fetch_report("disagg")
    if disagg_rows:
        results = parse_disagg(disagg_rows)
        all_results.update(results)
        print(f"  → {len(results)} commodités trouvées")

    print("\n[2/2] Rapport TFF (forex, indices, crypto)...")
    tff_rows = fetch_report("tff")
    if tff_rows:
        results = parse_tff(tff_rows)
        all_results.update(results)
        print(f"  → {len(results)} instruments financiers trouvés")

    print(f"\n{'=' * 55}")
    print(f"  RÉSULTATS — {len(all_results)} symboles")
    print(f"{'=' * 55}")

    for cat in ["forex", "index", "crypto", "commodity"]:
        items = {k: v for k, v in all_results.items() if v["category"] == cat}
        if not items:
            continue
        print(f"\n  {cat.upper()}")
        print(f"  {'─' * 50}")
        for sym, d in sorted(items.items(), key=lambda x: x[1]["sentiment_score"], reverse=True):
            dot = "🟢" if d["bias"] == "BULLISH" else "🔴" if d["bias"] == "BEARISH" else "⚪"
            print(f"  {dot} {sym:15s} | Score: {d['sentiment_score']:>6.1f} | {d['bias']:8s} | SM Net: {d['smart_money_net']:>10,}")

    save_results(all_results)
    print(f"{'=' * 55}")
    return all_results


if __name__ == "__main__":
    run()
