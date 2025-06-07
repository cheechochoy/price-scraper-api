# app.py
from flask import Flask, request, jsonify
import easyocr
import base64
import io
from PIL import Image
import numpy as np

app = Flask(__name__)

# 🔁 Load OCR model once (saves time on repeated scans)
reader = easyocr.Reader(['en'], gpu=False)

@app.route('/ocr', methods=['POST'])
def ocr():
    try:
        data = request.get_json()
        base64_image = data.get('imageBase64')

        if not base64_image:
            return jsonify({'error': 'Missing imageBase64'}), 400

        # Strip data URI prefix if exists
        if ',' in base64_image:
            base64_image = base64_image.split(',')[1]

        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data)).convert('RGB')
        image_np = np.array(image)

        # 🔍 Run OCR
        results = reader.readtext(image_np, detail=0)
        text_output = '\n'.join(results)

        return jsonify({'text': text_output})

    except Exception as e:
        print("OCR Error:", e)
        return jsonify({'error': str(e)}), 500
