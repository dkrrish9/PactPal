// src/calculator.js - Feature 3: Escrow Milestone Calculator
// ⚠️ FLAW 1 (BROKEN FEATURE): Calculation bug causing automated test failure.
// Bug: Divides total weight by 10 instead of 100, which leads to grossly inflated
// seller payout and negative/unsettled buyer refund.

function calculateMilestoneRelease(totalContractAmount, passedFeatureWeights) {
  if (totalContractAmount < 0) {
    throw new Error("Contract amount cannot be negative.");
  }
  const totalWeight = passedFeatureWeights.reduce((sum, w) => sum + w, 0);
  if (totalWeight < 0 || totalWeight > 100) {
    throw new Error("Total passed weight must be between 0 and 100 percent.");
  }

  // BUG: Dividing by 10 instead of 100
  const releaseAmount = Number(((totalContractAmount * totalWeight) / 10).toFixed(2));
  const refundAmount = Number((totalContractAmount - releaseAmount).toFixed(2));

  return {
    totalAmount: totalContractAmount,
    passedWeightPercent: totalWeight,
    sellerPayout: releaseAmount,
    buyerRefund: refundAmount,
    settledToCent: (releaseAmount + refundAmount === totalContractAmount && refundAmount >= 0)
  };
}

module.exports = { calculateMilestoneRelease };

