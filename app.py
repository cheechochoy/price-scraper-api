from flask import Flask, request, jsonify
from flask_cors import CORS
import pytesseract
from PIL import Image
import base64
import io

pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

app = Flask(__name__)
CORS(app)  # Allow cross-origin for mobile apps

@app.route('/ocr', methods=['POST'])
def ocr():
    try:
        data = request.get_json()
        image_b64 = data.get('imageBase64')

        if not image_b64:
            return jsonify({'error': 'Missing imageBase64'}), 400

        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]

        image_data = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        text = pytesseract.image_to_string(image)

        return jsonify({'text': text})

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500
    
@app.route('/ocr-dual', methods=['POST'])
def ocr_dual():
    try:
        data = request.get_json()
        image_b64 = data.get('imageBase64')

        if not image_b64:
            return jsonify({'error': 'Missing imageBase64'}), 400

        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]

        image_data = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")

        # Example alternate OCR logic (you can modify this)
        text = pytesseract.image_to_string(image, lang='eng')

        return jsonify({'text': text})

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
