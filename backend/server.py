"""
Trading Dashboard — API Server v3 (with Key Levels + Scheduled COT)
"""

from flask import Flask, jsonify
from flask_cors import CORS
import json
import os
import threading
import time
from datetime import datetime

from cot_fetcher import run as fetch_cot
from eco_fetcher import run as fetch_eco
from sentiment_fetcher import run as fetch_sentiment
from scoring_engine import run as compute_scores
from levels_fetcher import run as fetch_levels

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PORT = int(os.environ.get("PORT", 5000))

# Refresh intervals
ECO_SENT_INTERVAL = 300    # 5 min for eco + sentiment
COT_INTERVAL = 86400       # 24h for COT (only changes weekly but we check daily)
LEVELS_INTERVAL = 3600     # 1h for price levels


def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# BACKGROUND THREADS
# ============================================================

def auto_refresh_fast():
    """Eco + sentiment every 5 min."""
    while True:
        time.sleep(ECO_SENT_INTERVAL)
        try:
            fetch_eco()
            fetch_sentiment()
            compute_scores()
        except Exception as e:
            print(f"[AUTO-FAST] {e}")


def auto_refresh_cot():
    """COT data daily (only new data on Fridays)."""
    while True:
        time.sleep(COT_INTERVAL)
        try:
            print(f"[COT-DAILY] Checking for new COT data...")
            fetch_cot()
            compute_scores()
        except Exception as e:
            print(f"[COT-DAILY] {e}")


def auto_refresh_levels():
    """Key levels every hour."""
    while True:
        time.sleep(LEVELS_INTERVAL)
        try:
            fetch_levels()
        except Exception as e:
            print(f"[LEVELS] {e}")


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    return jsonify({"status": "ok", "name": "QuantDash API", "version": "3.0"})

@app.route("/api/cot")
def get_cot():
    data = load_json("cot_data.json")
    return jsonify(data) if data else (jsonify({"error": "unavailable"}), 404)

@app.route("/api/cot/<symbol>")
def get_cot_symbol(symbol):
    data = load_json("cot_data.json")
    if not data: return jsonify({"error": "unavailable"}), 404
    for k, v in data.get("data", {}).items():
        if k.lower() == symbol.lower(): return jsonify(v)
    return jsonify({"error": "not found"}), 404

@app.route("/api/cot/category/<category>")
def get_cot_category(category):
    data = load_json("cot_data.json")
    if not data: return jsonify({"error": "unavailable"}), 404
    f = {k: v for k, v in data.get("data", {}).items() if v.get("category") == category.lower()}
    return jsonify({"category": category, "count": len(f), "data": f})

@app.route("/api/eco")
def get_eco():
    data = load_json("eco_data.json")
    return jsonify(data) if data else (jsonify({"error": "unavailable"}), 404)

@app.route("/api/eco/high-impact")
def get_eco_high():
    data = load_json("eco_data.json")
    return jsonify(data.get("high_impact_events", [])) if data else (jsonify([]), 200)

@app.route("/api/sentiment")
def get_sentiment():
    data = load_json("sentiment_data.json")
    return jsonify(data) if data else (jsonify({"error": "unavailable"}), 404)

@app.route("/api/composite")
def get_composite():
    data = load_json("composite_scores.json")
    return jsonify(data) if data else (jsonify({"error": "unavailable"}), 404)

@app.route("/api/levels")
def get_levels():
    data = load_json("levels_data.json")
    return jsonify(data) if data else (jsonify({"error": "unavailable"}), 404)

@app.route("/api/levels/<symbol>")
def get_levels_symbol(symbol):
    data = load_json("levels_data.json")
    if not data: return jsonify({"error": "unavailable"}), 404
    for k, v in data.get("data", {}).items():
        if k.lower() == symbol.lower(): return jsonify(v)
    return jsonify({"error": "not found"}), 404

@app.route("/api/summary")
def get_summary():
    cot = load_json("cot_data.json")
    comp = load_json("composite_scores.json")
    source = comp or cot
    items = list(source.get("data", {}).values()) if source else []
    sk = "composite_score" if comp else "sentiment_score"
    bk = "composite_bias" if comp else "bias"
    bull = sorted([i for i in items if i.get(bk) == "BULLISH"], key=lambda x: x.get(sk, 0), reverse=True)
    bear = sorted([i for i in items if i.get(bk) == "BEARISH"], key=lambda x: x.get(sk, 0))
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "signals_count": len(items),
        "top_bullish": [{"symbol": i["symbol"], "score": i.get(sk), "category": i["category"]} for i in bull[:5]],
        "top_bearish": [{"symbol": i["symbol"], "score": i.get(sk), "category": i["category"]} for i in bear[:5]],
        "modules": {
            "cot": {"available": cot is not None},
            "economic": {"available": load_json("eco_data.json") is not None},
            "sentiment": {"available": load_json("sentiment_data.json") is not None},
            "composite": {"available": comp is not None},
            "levels": {"available": load_json("levels_data.json") is not None},
        },
    })

@app.route("/api/refresh/all")
def refresh_all():
    try:
        t0 = time.time()
        fetch_cot(); fetch_eco(); fetch_sentiment()
        comp = compute_scores()
        fetch_levels()
        return jsonify({"status": "ok", "symbols": len(comp or {}), "elapsed": round(time.time()-t0, 1)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# STARTUP
# ============================================================

def init_data():
    try:
        if not os.path.exists(os.path.join(DATA_DIR, "cot_data.json")):
            fetch_cot()
        fetch_eco()
        fetch_sentiment()
        compute_scores()
        fetch_levels()
    except Exception as e:
        print(f"[INIT] {e}")

init_data()

# Start background threads
for fn in [auto_refresh_fast, auto_refresh_cot, auto_refresh_levels]:
    threading.Thread(target=fn, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=False, port=PORT)
