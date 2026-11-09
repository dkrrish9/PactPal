// test/contact.test.js - Tests for Feature 4 (Contact & Feedback Modal)
const { validateFeedbackForm } = require('../src/contact');

function testContact() {
  const valid = validateFeedbackForm({
    email: "client@example.com",
    subject: "Milestone Approval",
    message: "Work completed according to spec."
  });
  if (!valid.isValid || !valid.sanitizedPayload) {
    throw new Error("Valid form failed validation");
  }

  const invalid = validateFeedbackForm({
    email: "invalid-email",
    subject: "Hi",
    message: "Short"
  });
  if (invalid.isValid) {
    throw new Error("Invalid form incorrectly passed validation");
  }
  return true;
}

module.exports = { testContact };
