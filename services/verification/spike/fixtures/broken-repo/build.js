// build.js - Simulates a broken freelancer deliverable with a compiler syntax error
console.log('[BUILD] Starting build pipeline for broken repository...');
console.error('[BUILD ERROR] SyntaxError: Unexpected token "<<<" in src/app.js at line 14: Failed to bundle deliverable.');
process.exit(1);
