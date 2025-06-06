import base64
import requests
from PIL import Image
from io import BytesIO

# Load image and convert to base64
def image_to_base64(path):
    with Image.open(path).convert("RGB") as img:
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{encoded}"

# Use a sample image file in the same folder
image_base64 = image_to_base64("test_receipt.jpg")

# Send POST request to Flask OCR endpoint
url = "http://127.0.0.1:5000/ocr"
payload = {
    "imageBase64": image_base64
}

try:
    response = requests.post(url, json=payload)
    response.raise_for_status()
    print("✅ OCR response:")
    print(response.json())
except Exception as e:
    print("❌ Error:")
    print(e)
    if response is not None:
        print("Server said:", response.text)
