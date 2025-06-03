const express = require('express');
const cors = require('cors');
const Tesseract = require('tesseract.js');

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

app.post('/ocr', async (req, res) => {
  const { imageBase64 } = req.body;
  if (!imageBase64) return res.status(400).json({ error: 'Image is required' });

  try {
    console.log('🧠 Running OCR...');
    const result = await Tesseract.recognize(
      Buffer.from(imageBase64, 'base64'),
      'eng',
      { logger: m => console.log(m) }
    );
    res.json({ text: result.data.text });
  } catch (err) {
    console.error('❌ Tesseract error:', err);
    res.status(500).json({ error: 'OCR failed' });
  }
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`🚀 Server is running on port ${PORT}`);
});
