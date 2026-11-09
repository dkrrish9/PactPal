// src/calculator.js - Feature 3: Escrow Milestone Calculator
function calculateMilestoneRelease(totalContractAmount, passedFeatureWeights) {
  if (totalContractAmount < 0) {
    throw new Error("Contract amount cannot be negative.");
  }
  const totalWeight = passedFeatureWeights.reduce((sum, w) => sum + w, 0);
  if (totalWeight < 0 || totalWeight > 100) {
    throw new Error("Total passed weight must be between 0 and 100 percent.");
  }

  const releaseAmount = Number(((totalContractAmount * totalWeight) / 100).toFixed(2));
  const refundAmount = Number((totalContractAmount - releaseAmount).toFixed(2));

  return {
    totalAmount: totalContractAmount,
    passedWeightPercent: totalWeight,
    sellerPayout: releaseAmount,
    buyerRefund: refundAmount,
    settledToCent: (releaseAmount + refundAmount === totalContractAmount)
  };
}

module.exports = { calculateMilestoneRelease };
