// src/contact.js - Feature 4: Feedback & Dispute Contact Form
function validateFeedbackForm(formData) {
  const errors = {};
  if (!formData.email || !formData.email.includes("@")) {
    errors.email = "Valid email is required.";
  }
  if (!formData.subject || formData.subject.trim().length < 3) {
    errors.subject = "Subject must be at least 3 characters.";
  }
  if (!formData.message || formData.message.trim().length < 10) {
    errors.message = "Message must be at least 10 characters.";
  }

  const isValid = Object.keys(errors).length === 0;
  return {
    isValid,
    errors,
    sanitizedPayload: isValid ? {
      email: formData.email.trim(),
      subject: formData.subject.trim(),
      message: formData.message.trim(),
      timestamp: new Date().toISOString()
    } : null
  };
}

module.exports = { validateFeedbackForm };
