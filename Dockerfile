# Use slim Python and install Tesseract
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y tesseract-ocr libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PORT=10000
EXPOSE 10000

CMD ["python", "app.py"]
