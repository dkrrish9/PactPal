// test/runner.js - Master Test Runner for Bad Repo
const { testProfile } = require('./profile.test');
const { testCatalog } = require('./catalog.test');
const { testCalculator } = require('./calculator.test');
const { testContact } = require('./contact.test');

const suites = [
  { name: 'Feature 1: User Profile Header', fn: testProfile, feature_id: 'feat_profile' },
  { name: 'Feature 2: Product Catalog & Filter', fn: testCatalog, feature_id: 'feat_catalog' },
  { name: 'Feature 3: Escrow Milestone Calculator', fn: testCalculator, feature_id: 'feat_calculator' },
  { name: 'Feature 4: Dispute & Feedback Form', fn: testContact, feature_id: 'feat_contact' }
];

console.log('[TEST RUNNER] Executing bad-repo test suites...');
let passed = 0;
let failed = 0;
const results = [];

const startTime = Date.now();

for (const suite of suites) {
  try {
    suite.fn();
    console.log(`  ✓ PASS: ${suite.name}`);
    passed++;
    results.push({ name: suite.name, feature_id: suite.feature_id, status: 'PASSED' });
  } catch (err) {
    console.error(`  ✗ FAIL: ${suite.name} - ${err.message}`);
    failed++;
    results.push({ name: suite.name, feature_id: suite.feature_id, status: 'FAILED', error: err.message });
  }
}

const duration = Date.now() - startTime;
console.log(`\n[TEST SUMMARY] Total: ${suites.length} | Passed: ${passed} | Failed: ${failed} | Duration: ${duration}ms`);

if (failed > 0) {
  console.log('[TEST FAILURE] One or more test suites failed as expected in flawed deliverable.');
  process.exit(1);
} else {
  console.log('[TEST SUCCESS] All test suites passed.');
  process.exit(0);
}

