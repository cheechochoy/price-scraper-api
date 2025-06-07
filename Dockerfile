# Use an official Python image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y tesseract-ocr libglib2.0-0 libsm6 libxext6 libxrender-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable so Flask runs on 0.0.0.0
ENV FLASK_RUN_HOST=0.0.0.0

# Expose port
EXPOSE 10000

# Run the app
CMD ["python", "app.py"]
