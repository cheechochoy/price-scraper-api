import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

OCR_SPACE_API_KEY = "K83442308688957"

app = Flask(__name__)
CORS(app)

@app.route('/ocr', methods=['POST'])
def ocr():
    data = request.get_json() or {}
    img_b64 = data.get('imageBase64', '')

    # Strip metadata if present
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
            timeout=20  # Optional timeout to avoid long waits
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
    
submitted_data = []

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json() or {}

    items = data.get('items', [])
    user_id = data.get('user_id')
    town = data.get('town')
    timestamp = data.get('timestamp')

    if not items or not user_id or not town or not timestamp:
        return jsonify(error='Missing required fields'), 400

    try:
        from datetime import datetime
        readable_time = datetime.fromtimestamp(timestamp / 1000)

        points_awarded = 0
        saved_items = []

        for item in items:
            # Validate each item for required fields: code, name, data_quality
            if not all(k in item for k in ('code', 'name', 'data_quality')):
                continue  # skip invalid items

            submitted_data.append({
                "user_id": user_id,
                "town": town,
                "timestamp": timestamp,
                "received_at": readable_time.isoformat(),
                "code": item['code'],
                "name": item['name'],
                "data_quality": item['data_quality']
            })

            saved_items.append({
                "code": item['code'],
                "name": item['name']
            })

            points_awarded += 1

        if points_awarded == 0:
            return jsonify(error='No valid items to submit'), 400

        return jsonify({
            "message": f"Submission received. Thank you!",
            "points_awarded": points_awarded,
            "items": saved_items
        }), 200

    except Exception as e:
        return jsonify(error='Failed to process submission', details=str(e)), 500


@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
