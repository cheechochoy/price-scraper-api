import requests
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='📘 %(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

OCR_SPACE_API_KEY = "K83442308688957"

app = Flask(__name__)
CORS(app)

# In-memory store for submitted data (replace with DB in production)
submitted_data = []

# Dummy test data to ensure something shows up on leaderboard
submitted_data.append({
    "user_id": "test-user",
    "town": "Teluk Air Tawar",
    "region": "Pulau Pinang",
    "country": "MY",
    "timestamp": datetime.now(timezone.utc).timestamp() * 1000,
    "received_at": datetime.now(timezone.utc).isoformat(),
    "code": "1234567890123",
    "name": "Sample Item",
    "data_quality": "High"
})

@app.route('/ocr', methods=['POST'])
def ocr():
    data = request.get_json() or {}
    img_b64 = data.get('imageBase64', '')

    if ',' in img_b64:
        img_b64 = img_b64.split(',', 1)[1]
    if not img_b64:
        return jsonify(error='Missing imageBase64'), 400

    try:
        ocr_response = requests.post(
            'https://api.ocr.space/parse/image',
            data={
                'apikey': OCR_SPACE_API_KEY,
                'base64Image': f'data:image/jpeg;base64,{img_b64}',
                'language': 'eng',
                'isOverlayRequired': False,
                'OCREngine': 2
            },
            timeout=60
        )

        result = ocr_response.json()
        if result.get("IsErroredOnProcessing"):
            return jsonify(error="OCR processing failed", fullOCR=result), 500

        parsed_results = result.get("ParsedResults", [])
        full_text = parsed_results[0]["ParsedText"] if parsed_results else ""

        return jsonify({
            "ParsedText": full_text,
            "IsErroredOnProcessing": False,
            "fullOCR": result
        })

    except requests.exceptions.RequestException as e:
        return jsonify(error="OCR request failed", details=str(e)), 502
    except Exception as e:
        return jsonify(error="Internal server error", details=str(e)), 500

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.get_json() or {}

    items = data.get('items', [])
    user_id = data.get('user_id') or data.get('uuid')
    town = data.get('town')
    region = data.get('region')
    country = data.get('country')
    timestamp = data.get('timestamp')

    if not items or not user_id or not town or not region or not country or not timestamp:
        return jsonify(error='Missing required fields'), 400

    try:
        readable_time = datetime.fromtimestamp(timestamp / 1000)

        points_awarded = 0
        saved_items = []

        for item in items:
            code = item.get('code') or item.get('p_code')
            name = item.get('name') or item.get('p_name')
            quality = item.get('data_quality') or item.get('quality')

            if not code or not name or not quality:
                continue

            submitted_data.append({
                "user_id": user_id,
                "town": town,
                "region": region,
                "country": country,
                "timestamp": timestamp,
                "received_at": readable_time.isoformat(),
                "code": code,
                "name": name,
                "data_quality": quality
            })

            saved_items.append({
                "code": code,
                "name": name
            })

            points_awarded += 1

        logger.info("📥 Submission received: %s", submitted_data[-points_awarded:])

        if points_awarded == 0:
            return jsonify(error='No valid items to submit'), 400

        return jsonify({
            "message": "Submission received. Thank you!",
            "points": points_awarded,
            "items": saved_items
        }), 200

    except Exception as e:
        return jsonify(error='Failed to process submission', details=str(e)), 500

@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    valid_cutoff = datetime.now(timezone.utc) - timedelta(days=21)
    leaderboard_data = defaultdict(int)

    logger.info("🔍 All submitted data: %s", submitted_data)

    for entry in submitted_data:
        timestamp = entry.get("timestamp", 0)
        if datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc) < valid_cutoff:
            continue

        town = entry.get("town", "").strip()
        region = entry.get("region", "").strip()
        country = entry.get("country", "").strip().upper()

        if not (town and region and country):
            continue

        key = (town, region, country)
        leaderboard_data[key] += 1

    sorted_leaderboard = sorted([
        {
            "town": town,
            "region": region,
            "country": country,
            "country_code": country[:2].lower(),
            "count": points
        }
        for (town, region, country), points in leaderboard_data.items()
    ], key=lambda x: x["count"], reverse=True)

    logger.info("✅ Leaderboard API response: %s", sorted_leaderboard)
    return jsonify(sorted_leaderboard)

import random

@app.route('/api/price/<code>', methods=['GET'])
def get_price_data(code):
    if not code:
        return jsonify(error="Missing product code"), 400

    try:
        # Filter matching entries
        matching = [
            entry for entry in submitted_data
            if entry.get("code") == code
        ]

        if not matching:
            return jsonify([])  # Return empty list

        # Sort by timestamp descending (freshest first)
        matching.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

        # Limit to top 10
        top_entries = matching[:10]

        # Jitter coordinates and format response
        response = []
        for entry in top_entries:
            lat = random.uniform(5.2, 6.2)   # West Malaysia range (adjust if needed)
            lon = random.uniform(100.2, 101.7)
            response.append({
                "uuid": entry.get("user_id", "")[:8],
                "price": entry.get("price") or entry.get("p_price") or "N/A",
                "purc_dt": datetime.fromtimestamp(entry["timestamp"] / 1000).strftime("%Y-%m-%d"),
                "lat": lat,
                "lon": lon,
                "fresh": entry == top_entries[0]  # Only the freshest entry is flagged
            })

        return jsonify(response)

    except Exception as e:
        return jsonify(error="Failed to fetch price data", details=str(e)), 500



@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
