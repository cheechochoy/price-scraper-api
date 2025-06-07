from flask import Flask, request, jsonify
import pytesseract
from PIL import Image
import base64
import io

app = Flask(__name__)

@app.route('/ocr', methods=['POST'])
def ocr():
    try:
        data = request.get_json()
        image_b64 = data.get('imageBase64')

        if not image_b64:
            return jsonify({'error': 'Missing imageBase64'}), 400

        # Strip prefix if present
        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]

        image_data = base64.b64decode(image_b64)
        image = Image.open(io.BytesIO(image_data))

        text = pytesseract.image_to_string(image)

        return jsonify({'text': text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
