from flask import Flask, request, jsonify
from flask_cors import CORS
import pytesseract
from PIL import Image
import base64
import io
import cv2
import numpy as np
from difflib import get_close_matches

# Point pytesseract at the system install
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

app = Flask(__name__)
CORS(app)

# List of known store names
known_stores = [
    "LOTUS", "TESCO", "GIANT", "AEON", "MYDIN", "FRESH", "ECONSAVE", "99 SPEEDMART",
    "THE STORE", "NSK", "HERO", "TF VALUE-MART", "COLD STORAGE", "JAYA GROCER"
]

def preprocess_image(pil_image):
    """Convert to grayscale, blur, and threshold using OpenCV."""
    img = np.array(pil_image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)

def crop_top(img, percentage=0.35):
    """Crop the top X% of the image (for likely store/town name)."""
    width, height = img.size
    return img.crop((0, 0, width, int(height * percentage)))

def fuzzy_match_store(text):
    """Fuzzy match a line to a known store name."""
    lines = text.upper().splitlines()
    for line in lines:
        matches = get_close_matches(line.strip(), known_stores, n=1, cutoff=0.6)
        if matches:
            return matches[0]
    return None

@app.route('/ocr-dual', methods=['POST'])
def ocr_dual():
    data = request.get_json() or {}
    img_b64 = data.get('imageBase64', '')
    if ',' in img_b64:
        img_b64 = img_b64.split(',', 1)[1]
    if not img_b64:
        return jsonify(error='Missing imageBase64'), 400

    img = Image.open(io.BytesIO(base64.b64decode(img_b64))).convert('RGB')
    preprocessed_img = preprocess_image(img)

    # Crop top section for likely store name
    header_img = crop_top(preprocessed_img)

    # OCR 1: Alphabetic restricted (header only)
    cfg_alpha = r'--oem 3 --psm 4 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    alpha_text = pytesseract.image_to_string(header_img, config=cfg_alpha).strip()

    # OCR fallback: general OCR (header only)
    fallback_text = pytesseract.image_to_string(header_img).strip()

    # OCR 2: Numeric (full image)
    cfg_num = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789./:%,-'
    numeric_text = pytesseract.image_to_string(preprocessed_img, config=cfg_num).strip()

    # Match store using both OCR outputs
    matched_store = fuzzy_match_store(alpha_text) or fuzzy_match_store(fallback_text)

    return jsonify({
        "alphabetic": alpha_text,
        "fallbackText": fallback_text,
        "numeric": numeric_text,
        "matchedStore": matched_store or "Unknown",
        "text": f"{alpha_text}\n{numeric_text}",
        "IsErroredOnProcessing": False
    })

@app.route('/ocr', methods=['POST'])
def ocr():
    data = request.get_json() or {}
    img_b64 = data.get('imageBase64', '')
    if ',' in img_b64:
        img_b64 = img_b64.split(',', 1)[1]
    if not img_b64:
        return jsonify(error='Missing imageBase64'), 400

    img = Image.open(io.BytesIO(base64.b64decode(img_b64))).convert('RGB')
    img = preprocess_image(img)

    text = pytesseract.image_to_string(img)
    return jsonify(text=text)

@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(__import__('os').environ.get('PORT', 10000)))
