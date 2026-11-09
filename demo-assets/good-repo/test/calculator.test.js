// test/calculator.test.js - Tests for Feature 3 (Escrow Calculator)
const { calculateMilestoneRelease } = require('../src/calculator');

function testCalculator() {
  const result = calculateMilestoneRelease(1000.00, [25.0, 30.0, 25.0]);
  if (result.sellerPayout !== 800.00) {
    throw new Error(`Expected sellerPayout 800.00, got ${result.sellerPayout}`);
  }
  if (result.buyerRefund !== 200.00) {
    throw new Error(`Expected buyerRefund 200.00, got ${result.buyerRefund}`);
  }
  if (!result.settledToCent) {
    throw new Error("Payout did not settle to exact cent");
  }
  return true;
}

module.exports = { testCalculator };
