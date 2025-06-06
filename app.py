from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
from io import BytesIO
from PIL import Image
import easyocr
import numpy as np

app = Flask(__name__)
CORS(app)
reader = easyocr.Reader(['en'])


import traceback

@app.route('/ocr', methods=['POST'])
def ocr():
    try:
        data = request.get_json()
        image_data = data.get('imageBase64')

        if not image_data or ',' not in image_data:
            return jsonify({'error': 'Invalid or missing imageBase64'}), 400

        _, encoded = image_data.split(',', 1)
        image_bytes = base64.b64decode(encoded)
        image = Image.open(BytesIO(image_bytes)).convert('RGB')

        # Convert to numpy
        img_np = np.array(image)
        result = reader.readtext(img_np, detail=0)
        return jsonify({'text': "\n".join(result)})
    except Exception as e:
        traceback.print_exc()  # <-- this helps you see the exact issue in the terminal
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000)
