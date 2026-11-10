// test/profile.test.js - Tests for Feature 1 (Profile Header)
const { getUserProfile } = require('../src/profile');

function testProfile() {
  const profile = getUserProfile("usr_999");
  if (!profile || profile.name !== "Alex Morgan") {
    throw new Error("Profile name mismatch");
  }
  if (!profile.escrowVerified) {
    throw new Error("Profile escrow verification failed");
  }
  return true;
}

module.exports = { testProfile };

