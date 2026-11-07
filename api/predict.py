import time
import traceback
from flask import Flask, jsonify
import requests

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
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
    try:
        ts = int(time.time() * 1000)
        url = f"{HISTORY_URL}?pageNo=1&pageSize=10&_t={ts}"

        # 8 second timeout to avoid function freeze
        res = requests.get(url, headers=HEADERS, timeout=8)

        if res.status_code != 200:
            return (
                jsonify({
                    "error": f"Upstream API returned status {res.status_code}",
                    "details": res.text[:200],
                }),
                200,
            )

        data = res.json()
        items = data.get("data", {}).get("list", [])
        if not items:
            return (
                jsonify({
                    "error": "Empty list from API",
                    "raw_response": str(data)[:200],
                }),
                200,
            )

        history = []
        for item in items:
            num = int(item.get("number", 0))
            history.append({
                "period": str(item.get("issueNumber") or item.get("period")),
                "number": num,
                "outcome": "BIG" if num >= 5 else "SMALL",
                "color": get_color(num),
            })

        latest = history[0]
        current_period = str(int(latest["period"]) + 1)
        last_num = latest["number"]
        outcomes = [h["outcome"] for h in history]
        colors = [h["color"] for h in history]

        # Big / Small Calculation[span_0](start_span)[span_0](end_span)
        if (
            len(outcomes) >= 3
            and outcomes[0] == "SMALL"
            and outcomes[1] == "SMALL"
            and outcomes[2] == "SMALL"
        ):
            bs_pred = "BIG"  #[span_1](start_span)[span_1](end_span)
        elif len(outcomes) >= 2 and outcomes[0] == outcomes[1]:
            bs_pred = (
                "BIG" if outcomes[0] == "SMALL" else "SMALL"
            )  #[span_2](start_span)[span_2](end_span)
        else:
            recent_5 = outcomes[:5]
            small_count = recent_5.count("SMALL")
            bs_pred = "BIG" if small_count >= 3 else "SMALL"  #[span_3](start_span)[span_3](end_span)

        # Color Calculation[span_4](start_span)[span_4](end_span)
        if "Violet" not in colors[:3]:
            color_pred = "Violet"  #[span_5](start_span)[span_5](end_span)
        else:
            color_pred = "Red" if outcomes[0] == "BIG" else "Green"

        # Digit Mapping[span_6](start_span)[span_6](end_span)
        digits = DIGIT_MAPPING.get(last_num, [0, 5])

        return jsonify({
            "current_period": current_period,
            "big_small": bs_pred,
            "color": color_pred,
            "expected_digits": digits,
        })

    except Exception as e:
        # 500 crash hone ke bajaye exact error return karega
        return (
            jsonify({
                "error": "Server Exception",
                "message": str(e),
                "trace": traceback.format_exc()[:300],
            }),
            200,
        )
