import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime, BigInteger, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests  # Ensure installed
import random

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='📘 %(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Read environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set; falling back to SQLite for local dev")
    # Local dev fallback; in production on Render, DATABASE_URL must be set
    DATABASE_URL = 'sqlite:///./submitted_data.db'

OCR_SPACE_API_KEY = os.environ.get('OCR_SPACE_API_KEY')
if not OCR_SPACE_API_KEY:
    logger.warning("OCR_SPACE_API_KEY not set; OCR endpoint may fail")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# Define Submission model
class Submission(Base):
    __tablename__ = 'submissions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    town = Column(String, nullable=False, index=True)
    region = Column(String, nullable=False)
    country = Column(String, nullable=False)
    timestamp = Column(BigInteger, nullable=False, index=True)  # milliseconds since epoch
    received_at = Column(DateTime, nullable=False)
    code = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    data_quality = Column(String, nullable=False)
    # If you want to store price, add: price = Column(Numeric) or similar

# Create tables
Base.metadata.create_all(bind=engine)

@app.route('/ocr', methods=['POST'])
def ocr():
    data = request.get_json() or {}
    img_b64 = data.get('imageBase64', '')
    if ',' in img_b64:
        img_b64 = img_b64.split(',', 1)[1]
    if not img_b64:
        return jsonify(error='Missing imageBase64'), 400

    if not OCR_SPACE_API_KEY:
        return jsonify(error='OCR_SPACE_API_KEY not configured'), 500

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
            timeout=60
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
        logger.exception("Unexpected OCR error")
        return jsonify(error="Internal server error", details=str(e)), 500

@app.route('/api/submit', methods=['POST'])
def submit():
    data = request.get_json() or {}
    items = data.get('items', [])
    user_id = data.get('user_id') or data.get('uuid')
    town = data.get('town')
    region = data.get('region')
    country = data.get('country')
    timestamp = data.get('timestamp')
    if not items or not user_id or not town or not region or not country or not timestamp:
        return jsonify(error='Missing required fields'), 400

    session = SessionLocal()
    try:
        readable_time = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        points_awarded = 0
        saved_items = []
        for item in items:
            code = item.get('code') or item.get('p_code')
            name = item.get('name') or item.get('p_name')
            quality = item.get('data_quality') or item.get('quality')
            if not code or not name or not quality:
                continue
            sub = Submission(
                user_id=user_id,
                town=town.strip(),
                region=region.strip(),
                country=country.strip().upper(),
                timestamp=timestamp,
                received_at=readable_time,
                code=code.strip(),
                name=name.strip(),
                data_quality=quality.strip()
            )
            session.add(sub)
            saved_items.append({"code": code, "name": name})
            points_awarded += 1
        if points_awarded == 0:
            session.rollback()
            return jsonify(error='No valid items to submit'), 400
        session.commit()
        logger.info("📥 Submission received: user=%s, items=%s", user_id, saved_items)
        return jsonify({
            "message": "Submission received. Thank you!",
            "points": points_awarded,
            "items": saved_items
        }), 200
    except Exception as e:
        session.rollback()
        logger.exception("Failed to process submission")
        return jsonify(error='Failed to process submission', details=str(e)), 500
    finally:
        session.close()

@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    session = SessionLocal()
    try:
        # e.g. last 21 days
        valid_cutoff = datetime.now(timezone.utc) - timedelta(days=21)
        cutoff_ts = int(valid_cutoff.timestamp() * 1000)
        # Aggregate by town, region, country, limit top 50
        results = (
            session.query(
                Submission.town,
                Submission.region,
                Submission.country,
                func.count().label('count')
            )
            .filter(Submission.timestamp >= cutoff_ts)
            .group_by(Submission.town, Submission.region, Submission.country)
            .order_by(func.count().desc())
            .limit(50)
            .all()
        )
        leaderboard_list = []
        for row in results:
            town, region, country, count = row
            leaderboard_list.append({
                "town": town,
                "region": region,
                "country": country,
                "country_code": country[:2].lower(),
                "count": count
            })
        logger.info("✅ Leaderboard API response: %s", leaderboard_list)
        return jsonify(leaderboard_list)
    except Exception as e:
        logger.exception("Failed to aggregate leaderboard")
        return jsonify(error='Failed to aggregate leaderboard', details=str(e)), 500
    finally:
        session.close()

@app.route('/api/price/<code>', methods=['GET'])
def get_price_data(code):
    if not code:
        return jsonify(error="Missing product code"), 400
    session = SessionLocal()
    try:
        # Query recent submissions for this code
        results = (
            session.query(Submission)
            .filter(Submission.code == code)
            .order_by(Submission.timestamp.desc())
            .limit(10)
            .all()
        )
        if not results:
            return jsonify([])
        response = []
        for idx, entry in enumerate(results):
            # Jitter: for prototype, random within a bounding box
            lat = random.uniform(5.2, 6.2)
            lon = random.uniform(100.2, 101.7)
            response.append({
                "uuid": entry.user_id[:8],
                # If you store price: entry.price; else "N/A"
                "price": getattr(entry, 'price', None) or "N/A",
                "purc_dt": entry.received_at.strftime("%Y-%m-%d"),
                "lat": lat,
                "lon": lon,
                "fresh": idx == 0
            })
        return jsonify(response)
    except Exception as e:
        logger.exception("Failed to fetch price data")
        return jsonify(error="Failed to fetch price data", details=str(e)), 500
    finally:
        session.close()

@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    # In Render, use the start command via Gunicorn; this block only for local dev.
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=True)
