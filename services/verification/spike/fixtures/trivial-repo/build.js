// build.js - Builds the trivial deliverable into dist/
const fs = require('fs');
const path = require('path');

console.log('[BUILD] Starting build pipeline...');
const distDir = path.join(__dirname, 'dist');
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

// Copy HTML
const htmlSrc = path.join(__dirname, 'src', 'index.html');
const htmlDest = path.join(distDir, 'index.html');
fs.copyFileSync(htmlSrc, htmlDest);
console.log('[BUILD] Copied src/index.html -> dist/index.html');

// Bundle JS
const jsSrc = path.join(__dirname, 'src', 'app.js');
const jsDest = path.join(distDir, 'bundle.js');
fs.copyFileSync(jsSrc, jsDest);
console.log('[BUILD] Bundled src/app.js -> dist/bundle.js');

console.log('[BUILD] Build completed successfully with 0 errors.');
process.exit(0);
