// build.js - Builds bad-repo into dist/
const fs = require('fs');
const path = require('path');

console.log('[BUILD] Packaging bad-repo deliverable...');
const distDir = path.join(__dirname, 'dist');
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

// Copy HTML
fs.copyFileSync(path.join(__dirname, 'src', 'index.html'), path.join(distDir, 'index.html'));
console.log('[BUILD] Copied mismatched src/index.html -> dist/index.html');

// Create bundled JS
const modules = ['profile.js', 'catalog.js', 'calculator.js', 'contact.js'];
let bundle = '/* PactPal Bad-Repo Bundle (Flawed Deliverable) */\n';
for (const mod of modules) {
  const content = fs.readFileSync(path.join(__dirname, 'src', mod), 'utf8');
  bundle += `\n// --- ${mod} ---\n` + content;
}
fs.writeFileSync(path.join(distDir, 'bundle.js'), bundle, 'utf8');
console.log('[BUILD] Created dist/bundle.js with all 4 deliverable modules.');

console.log('[BUILD] Compilation finished cleanly with exit code 0.');
process.exit(0);
