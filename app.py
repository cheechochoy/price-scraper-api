import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta, timezone

valid_cutoff = datetime.now(timezone.utc) - timedelta(days=21)


OCR_SPACE_API_KEY = "K83442308688957"

app = Flask(__name__)
CORS(app)

# In-memory store for submitted data (replace with DB in production)
submitted_data = []

@app.route('/ocr', methods=['POST'])
def ocr():
    data = request.get_json() or {}
    img_b64 = data.get('imageBase64', '')

    # Strip metadata if present (e.g. data:image/jpeg;base64,)
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
            timeout=60  # You may increase to 60 if needed
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

        if points_awarded == 0:
            return jsonify(error='No valid items to submit'), 400

        return jsonify({
            "message": "Submission received. Thank you!",
            "points": points_awarded,
            "items": saved_items
        }), 200

    except Exception as e:
        return jsonify(error='Failed to process submission', details=str(e)), 500


from collections import defaultdict

@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    valid_cutoff = datetime.utcnow() - timedelta(days=21)
    leaderboard_data = defaultdict(int)

    for entry in submitted_data:
        timestamp = entry.get("timestamp", 0)
        if datetime.fromtimestamp(timestamp / 1000) < valid_cutoff:
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
            "country_code": country[:2].lower(),  # better if you have a real mapping
            "count": points
        }
        for (town, region, country), points in leaderboard_data.items()
    ], key=lambda x: x["count"], reverse=True)

    print("✅ Leaderboard API response:", sorted_leaderboard)


    return jsonify(sorted_leaderboard)





@app.route('/health')
def health():
    return 'OK'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
