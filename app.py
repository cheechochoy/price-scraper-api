import express from 'express';
import Tesseract from 'tesseract.js';

// Dummy comment to trigger redeploy

const app = express();
app.use(express.json({ limit: '10mb' }));

/**
 * Helper function to decode base64 image to a Buffer.
 */
function decodeBase64Image(imageBase64) {
  if (!imageBase64) throw new Error('Missing imageBase64');
  const base64Data = imageBase64.replace(/^data:image\/\w+;base64,/, '');
  return Buffer.from(base64Data, 'base64');
}

/**
 * Helper for dual-pass OCR using a whitelist.
 */
async function runTesseract(buffer, whitelist) {
  const { createWorker } = Tesseract;
  const worker = await createWorker('eng');

  await worker.setParameters({
    tessedit_char_whitelist: whitelist,
  });

  const {
    data: { text },
  } = await worker.recognize(buffer);

  await worker.terminate();
  return text;
}

// 🔵 Single-pass OCR
app.post('/ocr', async (req, res) => {
  try {
    const { imageBase64 } = req.body;
    const imageBuffer = decodeBase64Image(imageBase64);

    const result = await Tesseract.recognize(imageBuffer, 'eng', {
      logger: m => console.log(m.status, m.progress),
    });

    res.json({
      ParsedResults: [{ ParsedText: result.data.text }],
      IsErroredOnProcessing: false,
    });
  } catch (err) {
    console.error('❌ OCR failed:', err.message);
    res.status(500).json({ error: 'OCR processing failed' });
  }
});

// 🟢 Dual-pass OCR: Alphabetic and Numeric results
app.post('/ocr-dual', async (req, res) => {
  try {
    const { imageBase64 } = req.body;
    const imageBuffer = decodeBase64Image(imageBase64);

    console.log('🟢 Running dual-pass OCR...');

    const alphabetic = await runTesseract(imageBuffer, 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz');
    const numeric = await runTesseract(imageBuffer, '0123456789./:%,-');

    res.json({
      alphabetic: alphabetic.trim(),
      numeric: numeric.trim(),
      IsErroredOnProcessing: false,
    });
  } catch (err) {
    console.error('❌ Dual OCR failed:', err.message);
    res.status(500).json({ error: 'OCR dual-pass failed' });
  }
});

// ✅ Server start
const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`✅ OCR server running on port ${PORT}`);
});
