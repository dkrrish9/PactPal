// build.js - Builds bad-repo into dist/
const fs = require('fs');
const path = require('path');

console.log('[BUILD] Packaging bad-repo deliverable...');
const distDir = path.join(__dirname, 'dist');
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

fs.copyFileSync(path.join(__dirname, 'src', 'index.html'), path.join(distDir, 'index.html'));
console.log('[BUILD] Copied mismatched src/index.html -> dist/index.html');
console.log('[BUILD] Build complete with exit code 0.');
process.exit(0);
