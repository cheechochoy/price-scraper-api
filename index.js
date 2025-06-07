// index.js (OCR server with /ocr and /ocr-dual)
import express from 'express';
import fetch from 'node-fetch';
import Tesseract from 'tesseract.js';

const app = express();
app.use(express.json({ limit: '10mb' }));

// Helper for dual-pass OCR
async function runTesseract(buffer, whitelist) {
  const { createWorker } = Tesseract;
  const worker = await createWorker('eng');
  await worker.setParameters({ tessedit_char_whitelist: whitelist });

  const { data: { text } } = await worker.recognize(buffer);
  await worker.terminate();
  return text;
}

// 🔵 Original OCR endpoint
app.post('/ocr', async (req, res) => {
  try {
    const { imageBase64 } = req.body;
    if (!imageBase64) return res.status(400).json({ error: 'Missing imageBase64' });

    const base64Data = imageBase64.replace(/^data:image\/\w+;base64,/, '');
    const imageBuffer = Buffer.from(base64Data, 'base64');

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

// 🟢 Dual-pass OCR endpoint
app.post('/ocr-dual', async (req, res) => {
  try {
    const { imageBase64 } = req.body;

    if (!imageBase64) {
      return res.status(400).json({ error: 'Missing imageBase64' });
    }

    const base64Data = imageBase64.replace(/^data:image\/\w+;base64,/, '');
    const imageBuffer = Buffer.from(base64Data, 'base64');

    // Run OCR with Tesseract for dual layout detection (same as /ocr for now)
    const result = await Tesseract.recognize(imageBuffer, 'eng', {
      logger: m => console.log(`[Dual] ${m.status} ${m.progress}`),
    });

    res.json({
      ParsedResults: [{ ParsedText: result.data.text }],
      IsErroredOnProcessing: false,
    });
  } catch (err) {
    console.error('OCR-DUAL processing failed:', err);
    res.status(500).json({ error: 'OCR-DUAL processing failed' });
  }
});


const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`✅ OCR server running on port ${PORT}`);
});
