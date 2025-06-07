const express = require('express');
const router = express.Router();
const Tesseract = require('tesseract.js');
const { createWorker } = Tesseract;
const axios = require('axios');

const processOCR = async (imageBuffer, charWhitelist) => {
  const worker = await createWorker('eng');
  await worker.setParameters({
    tessedit_char_whitelist: charWhitelist,
  });

  const { data: { text } } = await worker.recognize(imageBuffer);
  await worker.terminate();
  return text;
};

router.post('/', async (req, res) => {
  try {
    const imageUrl = req.body.imageUrl;
    if (!imageUrl) {
      return res.status(400).json({ error: 'Missing imageUrl in request body' });
    }

    // Download image
    const response = await axios.get(imageUrl, { responseType: 'arraybuffer' });
    const imageBuffer = Buffer.from(response.data);

    // First pass: Alphabetic only
    const alphabeticText = await processOCR(imageBuffer, 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz');

    // Second pass: Numeric + common symbols
    const numericText = await processOCR(imageBuffer, '0123456789./:%,-');

    // Combine or return separately
    res.json({
      alphabetic: alphabeticText,
      numeric: numericText,
    });
  } catch (err) {
    console.error('OCR Dual-Pass Error:', err.message);
    res.status(500).json({ error: 'OCR processing failed' });
  }
});

module.exports = router;
