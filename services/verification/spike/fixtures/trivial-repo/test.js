// test.js - Verifies build artifacts
const fs = require('fs');
const path = require('path');

console.log('[TEST] Executing test suite...');
const distHtml = path.join(__dirname, 'dist', 'index.html');
const distJs = path.join(__dirname, 'dist', 'bundle.js');

if (!fs.existsSync(distHtml)) {
  console.error('[TEST ERROR] Missing dist/index.html');
  process.exit(1);
}

if (!fs.existsSync(distJs)) {
  console.error('[TEST ERROR] Missing dist/bundle.js');
  process.exit(1);
}

const htmlContent = fs.readFileSync(distHtml, 'utf8');
if (!htmlContent.includes('Trivial Freelance Deliverable')) {
  console.error('[TEST ERROR] index.html missing required title content');
  process.exit(1);
}

console.log('[TEST] All 3 assertions passed. Test suite green.');
process.exit(0);
