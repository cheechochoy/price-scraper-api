// index.js (with real OCR)
import express from 'express';
import fetch from 'node-fetch'; // Required for fetching base64 image data
import Tesseract from 'tesseract.js';

const app = express();
app.use(express.json({ limit: '10mb' })); // increase limit for large base64 images

app.post('/ocr', async (req, res) => {
  try {
    const { imageBase64 } = req.body;

    if (!imageBase64) {
      return res.status(400).json({ error: 'Missing imageBase64' });
    }

    // Convert data URL to buffer
    const base64Data = imageBase64.replace(/^data:image\/\w+;base64,/, '');
    const imageBuffer = Buffer.from(base64Data, 'base64');

    // Run Tesseract OCR
    const result = await Tesseract.recognize(imageBuffer, 'eng', {
      logger: m => console.log(m.status, m.progress),
    });

    res.json({
      ParsedResults: [{ ParsedText: result.data.text }],
      IsErroredOnProcessing: false,
    });
  } catch (err) {
    console.error('OCR processing failed:', err);
    res.status(500).json({ error: 'OCR processing failed' });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`✅ OCR server running on port ${PORT}`);
});
