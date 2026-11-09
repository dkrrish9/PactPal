// src/profile.js - Feature 1: User Profile Header
function getUserProfile(userId) {
  if (!userId) {
    throw new Error("User ID is required.");
  }
  return {
    userId: userId,
    name: "Alex Morgan",
    role: "Senior Fullstack Engineer",
    rating: 4.95,
    completedContracts: 38,
    escrowVerified: true,
    avatarUrl: "https://pactpal.dev/avatars/alex.png"
  };
}

module.exports = { getUserProfile };
