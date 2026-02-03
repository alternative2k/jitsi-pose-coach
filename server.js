const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const app = express();

const uploadDir = 'uploads';
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir);
}

const storage = multer.diskStorage({
  destination: uploadDir,
  filename: (req, file, cb) => {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    cb(null, `recording-${timestamp}.webm`);
  }
});

const upload = multer({ 
  storage,
  limits: {
    fileSize: 500 * 1024 * 1024
  }
});

app.use(express.static('public'));

app.post('/upload', upload.single('video'), (req, res) => {
  res.json({ success: true, path: req.file.path, filename: req.file.filename });
});

app.listen(3000, () => console.log('Server running on http://localhost:3000'));