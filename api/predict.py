import time
from flask import Flask, jsonify
import requests

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://draw.ar-lottery01.com/",
    "Origin": "https://draw.ar-lottery01.com/",
}

HISTORY_URL = (
    "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
)

DIGIT_MAPPING = {
    0: [5, 2],
    1: [9, 3],
    2: [0, 8],
    3: [1, 7],
    4: [6, 2],
    5: [0, 5],
    6: [4, 8],
    7: [3, 9],
    8: [6, 2],
    9: [1, 7],
}


def get_color(num):
    if num in [0, 5]:
        return "Violet"
    elif num in [1, 3, 7, 9]:
        return "Red"
    elif num in [2, 4, 6, 8]:
        return "Green"
    return "Unknown"


@app.route("/api/predict", methods=["GET"])
@app.route("/predict", methods=["GET"])
def predict():
    ts = int(time.time() * 1000)
    url = f"{HISTORY_URL}?pageNo=1&pageSize=10&_t={ts}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            items = res.json().get("data", {}).get("list", [])
            if not items:
                return jsonify({"error": "No data received"}), 500

            history = []
            for item in items:
                num = int(item.get("number"))
                history.append({
                    "period": str(
                        item.get("issueNumber") or item.get("period")
                    ),
                    "number": num,
                    "outcome": "BIG" if num >= 5 else "SMALL",
                    "color": get_color(num),
                })

            latest = history[0]
            current_period = str(int(latest["period"]) + 1)
            last_num = latest["number"]
            outcomes = [h["outcome"] for h in history]
            colors = [h["color"] for h in history]

            # Big / Small Logic
            if (
                outcomes[0] == "SMALL"
                and outcomes[1] == "SMALL"
                and outcomes[2] == "SMALL"
            ):
                bs_pred = "BIG"
            elif outcomes[0] == outcomes[1]:
                bs_pred = "BIG" if outcomes[0] == "SMALL" else "SMALL"
            else:
                small_count = outcomes[:5].count("SMALL")
                bs_pred = "BIG" if small_count >= 3 else "SMALL"

            # Color Logic
            color_pred = (
                "Violet"
                if "Violet" not in colors[:3]
                else ("Red" if outcomes[0] == "BIG" else "Green")
            )

            # Digits Logic
            digits = DIGIT_MAPPING.get(last_num, [])

            return jsonify({
                "current_period": current_period,
                "big_small": bs_pred,
                "color": color_pred,
                "expected_digits": digits,
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Failed to fetch"}), 500
