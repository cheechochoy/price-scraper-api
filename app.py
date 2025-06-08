from flask import Flask, request, jsonify
from flask_cors import CORS
import pytesseract
from PIL import Image
import base64
import io

# Point pytesseract at the system install
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

app = Flask(__name__)
CORS(app)

@app.route('/ocr', methods=['POST'])
def ocr():
    data = request.get_json() or {}
    img_b64 = data.get('imageBase64', '')
    if ',' in img_b64:
        img_b64 = img_b64.split(',', 1)[1]
    if not img_b64:
        return jsonify(error='Missing imageBase64'), 400

    img = Image.open(io.BytesIO(base64.b64decode(img_b64))).convert('RGB')
    text = pytesseract.image_to_string(img)
    return jsonify(text=text)

@app.route('/ocr-dual', methods=['POST'])
def ocr_dual():
    data = request.get_json() or {}
    img_b64 = data.get('imageBase64', '')
    if ',' in img_b64:
        img_b64 = img_b64.split(',', 1)[1]
    if not img_b64:
        return jsonify(error='Missing imageBase64'), 400

    img = Image.open(io.BytesIO(base64.b64decode(img_b64))).convert('RGB')

    # Pass 1: letters only
    cfg_alpha = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    alpha = pytesseract.image_to_string(img, config=cfg_alpha).strip()

    # Pass 2: digits & common symbols
    cfg_num = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789./:%,-'
    numeric = pytesseract.image_to_string(img, config=cfg_num).strip()

    return jsonify(alphabetic=alpha, numeric=numeric)

@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(__import__('os').environ.get('PORT', 10000)))
