"""
Trading Dashboard — API Server (Local + Render)
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

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
REFRESH_INTERVAL = 300
PORT = int(os.environ.get("PORT", 5000))


def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def auto_refresh():
    while True:
        time.sleep(REFRESH_INTERVAL)
        try:
            print(f"[AUTO] Refresh {datetime.now().strftime('%H:%M:%S')}...")
            fetch_eco()
            fetch_sentiment()
            compute_scores()
        except Exception as e:
            print(f"[AUTO] Error: {e}")


@app.route("/")
def index():
    return jsonify({"status": "ok", "name": "QuantDash API", "version": "2.0"})

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
        },
    })

@app.route("/api/refresh/all")
def refresh_all():
    try:
        t0 = time.time()
        fetch_cot(); fetch_eco(); fetch_sentiment()
        comp = compute_scores()
        return jsonify({"status": "ok", "symbols": len(comp or {}), "elapsed": round(time.time()-t0, 1)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def init_data():
    try:
        if not os.path.exists(os.path.join(DATA_DIR, "cot_data.json")):
            fetch_cot()
        fetch_eco(); fetch_sentiment(); compute_scores()
    except Exception as e:
        print(f"[INIT] {e}")

init_data()
threading.Thread(target=auto_refresh, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=False, port=PORT)
