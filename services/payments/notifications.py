"""
PactPal Automated Email Notification Service & State Change Dispatcher
Linked Commit: C51 (Milestone 3: Money & Extras)
Done When:
  'Signed, funded, submitted, verifying, decision, payout complete all send'

Architecture:
1. Pluggable Transport Providers:
   - BaseEmailProvider: Abstract email provider contract
   - InMemoryEmailProvider: Default zero-network in-memory provider for isolated test runs
   - SMTPEmailProvider: Production SMTP delivery over TLS with auth
   - SendGridEmailProvider: SendGrid v3 Web API delivery
   - get_email_provider: Factory resolving provider from config / env

2. Role-Tailored Contextual Email Templates:
   - Evaluates each of the 6 mandatory state milestones:
     1. SIGNED: Notifies buyer & seller that agreement is formalized and ready for funding.
     2. FUNDED: Notifies seller that funds are secured in escrow, and notifies buyer with hold confirmation & 29-day countdown.
     3. SUBMITTED: Notifies buyer that deliverable code is ready for automated referee inspection (and seller that submission was recorded).
     4. VERIFYING: Notifies both parties that test execution, cheat scan, and visual diff analysis are underway.
     5. DECISION: Notifies both parties with the verdict overview and next steps.
     6. SETTLED / PAYOUT COMPLETE: Notifies seller of disbursed earnings with payout batch reference, and notifies buyer of release/refund amounts with cryptographic receipt hash link.
   - Separate, personalized copy for BUYER vs SELLER perspectives.
   - Dynamic interpolation: participant names, contract title, monetary amounts, currency, deadlines, auth IDs, commit SHAs, receipt hashes, and timestamps.
   - High-fidelity dual rendering (Plain Text + Responsive HTML).

3. Immutable Audit Logging:
   - Records every dispatched email in relational 'messages' table with event="EMAIL_NOTIFICATION_SENT".
   - Persists recipient email, role, state transition, subject, delivery status, provider, and timestamp.

4. Integration Points:
   - ContractRepository.transition_contract() automated hook
   - EscrowPaymentService funding and settlement hooks
   - DeadlineWatcherService autonomous sweep notifications
   - REST API routes (POST /api/v1/payments/notifications/dispatch & GET /api/v1/contracts/{id}/notifications)
"""

import os
import re
import abc
import json
import uuid
import smtplib
import importlib
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

# Dynamic imports to handle hyphenated directory name 'core-api'
_roles_mod = importlib.import_module("services.core-api.auth.roles")
User = _roles_mod.User
UserRole = _roles_mod.UserRole
ForbiddenActionError = _roles_mod.ForbiddenActionError
UnauthorizedRoleError = getattr(_roles_mod, "UnauthorizedRoleError", ForbiddenActionError)
assert_can_view_notifications = getattr(_roles_mod, "assert_can_view_notifications", None)
assert_can_dispatch_notification = getattr(_roles_mod, "assert_can_dispatch_notification", None)


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

@dataclass
class NotificationRecipient:
    """Represents an email recipient with participant role context."""
    email: str
    name: str
    role: str  # "BUYER" | "SELLER" | "ADMIN"
    user_id: Optional[str] = None
    paypal_email: Optional[str] = None


@dataclass
class NotificationMessage:
    """Represents a rendered notification email payload."""
    contract_id: str
    state_transition: str
    recipient: NotificationRecipient
    subject: str
    body_text: str
    body_html: Optional[str] = None
    delivery_status: str = "PENDING"
    message_id: Optional[str] = None
    provider: str = "in_memory"
    sent_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# -----------------------------------------------------------------------------
# Transport Providers (Pluggable Architecture)
# -----------------------------------------------------------------------------

class BaseEmailProvider(abc.ABC):
    """Abstract interface for email delivery providers."""
    name: str = "base"

    @abc.abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sends an email and returns dispatch outcome dictionary:
        {
            "status": "SENT" | "FAILED",
            "message_id": str,
            "to_email": str,
            "subject": str,
            "provider": str,
            "sent_at": str
        }
        """
        pass


class InMemoryEmailProvider(BaseEmailProvider):
    """
    Default in-memory email provider for testing and offline environments.
    Captures sent emails without making external network calls.
    """
    name: str = "in_memory"

    def __init__(self):
        self.sent_emails: List[Dict[str, Any]] = []

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        message_id = f"mem_{uuid.uuid4().hex[:12]}"
        sent_at = datetime.now(timezone.utc).isoformat()
        record = {
            "message_id": message_id,
            "to_email": to_email,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "metadata": metadata or {},
            "status": "SENT",
            "provider": self.name,
            "sent_at": sent_at
        }
        self.sent_emails.append(record)
        return record

    def get_sent_emails(
        self,
        to_email: Optional[str] = None,
        contract_id: Optional[str] = None,
        state: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = list(self.sent_emails)
        if to_email:
            results = [e for e in results if e.get("to_email") == to_email]
        if contract_id:
            results = [e for e in results if e.get("metadata", {}).get("contract_id") == contract_id]
        if state:
            results = [e for e in results if e.get("metadata", {}).get("state_transition") == state]
        return results

    def clear(self) -> None:
        self.sent_emails.clear()


class SMTPEmailProvider(BaseEmailProvider):
    """SMTP email transport provider with STARTTLS support."""
    name: str = "smtp"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
        from_email: Optional[str] = None
    ):
        self.host = host or os.environ.get("SMTP_HOST", "localhost")
        self.port = int(port or os.environ.get("SMTP_PORT", 587))
        self.user = user or os.environ.get("SMTP_USER", "")
        self.password = password or os.environ.get("SMTP_PASSWORD", "")
        self.use_tls = use_tls if use_tls is not None else (os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes"))
        self.from_email = from_email or os.environ.get("SMTP_FROM_EMAIL", "no-reply@pactpal.com")

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        message_id = f"smtp_{uuid.uuid4().hex[:12]}"
        sent_at = datetime.now(timezone.utc).isoformat()

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.sendmail(self.from_email, [to_email], msg.as_string())
            status = "SENT"
        except Exception as e:
            raise RuntimeError(f"SMTP email dispatch to {to_email} failed: {str(e)}") from e

        return {
            "message_id": message_id,
            "to_email": to_email,
            "subject": subject,
            "status": status,
            "provider": self.name,
            "sent_at": sent_at,
            "metadata": metadata or {}
        }


class SendGridEmailProvider(BaseEmailProvider):
    """SendGrid v3 REST API email transport provider."""
    name: str = "sendgrid"

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None
    ):
        self.api_key = api_key or os.environ.get("SENDGRID_API_KEY", "")
        self.from_email = from_email or os.environ.get("SENDGRID_FROM_EMAIL", "no-reply@pactpal.com")

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("SendGrid API key is not configured (SENDGRID_API_KEY).")

        payload: Dict[str, Any] = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": self.from_email},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body_text}]
        }
        if body_html:
            payload["content"].append({"type": "text/html", "value": body_html})

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=data_bytes,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        message_id = f"sg_{uuid.uuid4().hex[:12]}"
        sent_at = datetime.now(timezone.utc).isoformat()

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status not in (200, 202):
                    raise RuntimeError(f"SendGrid API responded with HTTP status {resp.status}")
            status = "SENT"
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else str(e)
            raise RuntimeError(f"SendGrid API HTTP error {e.code}: {err_body}") from e
        except Exception as e:
            raise RuntimeError(f"SendGrid email dispatch to {to_email} failed: {str(e)}") from e

        return {
            "message_id": message_id,
            "to_email": to_email,
            "subject": subject,
            "status": status,
            "provider": self.name,
            "sent_at": sent_at,
            "metadata": metadata or {}
        }


def get_email_provider(
    provider_type: Optional[str] = None,
    **kwargs
) -> BaseEmailProvider:
    """Factory creating an email provider instance based on type or environment."""
    p_type = (provider_type or os.environ.get("EMAIL_PROVIDER", "memory")).lower().strip()
    if p_type in ("memory", "in_memory", "mock", "test"):
        return InMemoryEmailProvider()
    elif p_type == "smtp":
        return SMTPEmailProvider(**kwargs)
    elif p_type == "sendgrid":
        return SendGridEmailProvider(**kwargs)
    return InMemoryEmailProvider()


# -----------------------------------------------------------------------------
# Contextual Email Templating Engine
# -----------------------------------------------------------------------------

class EmailTemplateEngine:
    """
    Renders role-tailored subjects and bodies for the 6 critical contract milestones:
    SIGNED, FUNDED, SUBMITTED, VERIFYING, DECISION, SETTLED (PAYOUT COMPLETE).
    """

    @staticmethod
    def _wrap_html(
        title: str,
        headline: str,
        recipient_name: str,
        greeting_text: str,
        key_value_pairs: List[Tuple[str, str]],
        callout_text: str,
        action_note: Optional[str] = None,
        badge_text: str = "PactPal Escrow",
        badge_color: str = "#2563EB"
    ) -> str:
        """Helper generating professional responsive HTML markup with brand styling."""
        rows = "".join([
            f"""<tr>
                <td style="padding: 8px 12px; font-weight: 600; color: #4B5563; border-bottom: 1px solid #E5E7EB; width: 35%;">{k}</td>
                <td style="padding: 8px 12px; color: #111827; border-bottom: 1px solid #E5E7EB;">{v}</td>
            </tr>"""
            for k, v in key_value_pairs
        ])

        action_html = ""
        if action_note:
            action_html = f"""
            <div style="margin-top: 20px; padding: 14px 18px; background-color: #F3F4F6; border-left: 4px solid {badge_color}; border-radius: 4px; font-size: 14px; color: #1F2937;">
                <strong>Next Step:</strong> {action_note}
            </div>
            """

        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F9FAFB; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #111827; line-height: 1.5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #F9FAFB; padding: 32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width: 600px; background-color: #FFFFFF; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06); border: 1px solid #E5E7EB;">
          <!-- Brand Header -->
          <tr>
            <td style="background-color: #0F172A; padding: 24px 32px; text-align: left;">
              <span style="font-size: 22px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.5px;">PactPal</span>
              <span style="font-size: 12px; font-weight: 500; color: #94A3B8; margin-left: 8px;">Zero-Trust AI Escrow</span>
            </td>
          </tr>
          <!-- Main Content -->
          <tr>
            <td style="padding: 32px;">
              <div style="display: inline-block; padding: 4px 10px; border-radius: 12px; background-color: {badge_color}15; color: {badge_color}; font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 12px;">
                {badge_text}
              </div>
              <h1 style="margin: 0 0 16px 0; font-size: 22px; font-weight: 700; color: #111827;">{headline}</h1>
              <p style="margin: 0 0 16px 0; font-size: 15px; color: #374151;">Hello <strong>{recipient_name}</strong>,</p>
              <p style="margin: 0 0 24px 0; font-size: 15px; color: #374151;">{greeting_text}</p>
              <!-- Details Table -->
              <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; background-color: #F9FAFB; border-radius: 6px; overflow: hidden; margin-bottom: 20px; font-size: 14px;">
                {rows}
              </table>
              <p style="margin: 0 0 8px 0; font-size: 14px; color: #4B5563;">{callout_text}</p>
              {action_html}
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background-color: #F9FAFB; padding: 20px 32px; text-align: center; border-top: 1px solid #E5E7EB; font-size: 12px; color: #6B7280;">
              <p style="margin: 0 0 4px 0;">PactPal Zero-Trust Multimodal Escrow Platform</p>
              <p style="margin: 0;">Automated referee notifications &bull; Cryptographically fingerprinted ledger</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    @classmethod
    def render(
        cls,
        state: str,
        role: str,
        contract: Dict[str, Any],
        buyer: NotificationRecipient,
        seller: NotificationRecipient,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, str]:
        """
        Renders role-tailored (subject, body_text, body_html) for a given state transition.
        """
        metadata = metadata or {}
        role = role.upper().strip()
        state = state.upper().strip()

        # Dynamic contract parameters (strictly dynamic, zero hardcoding)
        contract_id = str(contract.get("id", ""))
        title = str(contract.get("title", "Untitled Contract"))
        total_amount = float(contract.get("total_amount", 0.0))
        currency = str(contract.get("currency", "USD"))
        deadline = str(contract.get("deadline", "N/A"))
        paypal_auth_id = str(metadata.get("paypal_auth_id") or contract.get("paypal_auth_id") or "AUTH_PENDING")
        auth_expires_at = str(metadata.get("auth_expires_at") or contract.get("auth_expires_at") or "29 days from authorization")

        # ---------------------------------------------------------------------
        # 1. SIGNED
        # ---------------------------------------------------------------------
        if state == "SIGNED":
            if role == "BUYER":
                subject = f"[PactPal] Contract Signed: {title} - Action Required: Escrow Funding"
                body_text = (
                    f"Hello {buyer.name},\n\n"
                    f"Your agreement '{title}' (Contract ID: {contract_id}) has been formally signed by both you and freelancer {seller.name}.\n\n"
                    f"Agreement Details:\n"
                    f"- Contract Value: {total_amount:,.2f} {currency}\n"
                    f"- Freelancer: {seller.name} ({seller.email})\n"
                    f"- Delivery Deadline: {deadline}\n\n"
                    f"Next Step:\n"
                    f"Please fund the escrow authorization hold to activate the contract. Freelancer {seller.name} will be cleared to commence development as soon as funds are secured on PayPal escrow rails.\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"Agreement Signed: {title}",
                    headline=f"Agreement Signed: {title}",
                    recipient_name=buyer.name,
                    greeting_text=f"Your contract with freelancer <strong>{seller.name}</strong> has been signed by both parties and is ready for funding.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Contract ID", contract_id),
                        ("Total Value", f"{total_amount:,.2f} {currency}"),
                        ("Freelancer", f"{seller.name} ({seller.email})"),
                        ("Deadline", deadline)
                    ],
                    callout_text="Funds are held securely under PayPal authorization rails until deliverables are verified.",
                    action_note="Please fund the escrow authorization hold to officially start the delivery clock.",
                    badge_text="Action Required: Fund Escrow",
                    badge_color="#2563EB"
                )
            else:  # SELLER
                subject = f"[PactPal] Contract Signed: {title} - Awaiting Buyer Escrow Funding"
                body_text = (
                    f"Hello {seller.name},\n\n"
                    f"Your agreement '{title}' (Contract ID: {contract_id}) has been formally signed by both you and client {buyer.name}.\n\n"
                    f"Agreement Details:\n"
                    f"- Contract Value: {total_amount:,.2f} {currency}\n"
                    f"- Client: {buyer.name} ({buyer.email})\n"
                    f"- Delivery Deadline: {deadline}\n\n"
                    f"Status:\n"
                    f"Client {buyer.name} has been prompted to fund the escrow authorization hold. Please wait for the escrow confirmation before commencing development.\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"Agreement Signed: {title}",
                    headline=f"Agreement Signed: {title}",
                    recipient_name=seller.name,
                    greeting_text=f"Your agreement with client <strong>{buyer.name}</strong> has been signed by both parties.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Contract ID", contract_id),
                        ("Agreed Price", f"{total_amount:,.2f} {currency}"),
                        ("Client", f"{buyer.name} ({buyer.email})"),
                        ("Deadline", deadline)
                    ],
                    callout_text="Client has been prompted to fund the escrow hold. You will receive an immediate notification as soon as funds are secured.",
                    action_note="Please wait for escrow funding confirmation before beginning development work.",
                    badge_text="Awaiting Funding",
                    badge_color="#4F46E5"
                )
            return subject, body_text, body_html

        # ---------------------------------------------------------------------
        # 2. FUNDED
        # ---------------------------------------------------------------------
        elif state == "FUNDED":
            if role == "BUYER":
                subject = f"[PactPal] Escrow Funded: {title} ({total_amount:,.2f} {currency} on Hold)"
                body_text = (
                    f"Hello {buyer.name},\n\n"
                    f"The escrow authorization hold for '{title}' (Contract ID: {contract_id}) has been successfully created and verified on PayPal rails.\n\n"
                    f"Escrow Hold Details:\n"
                    f"- Hold Amount: {total_amount:,.2f} {currency}\n"
                    f"- PayPal Authorization ID: {paypal_auth_id}\n"
                    f"- Hold Expiration (29-day limit): {auth_expires_at}\n"
                    f"- Delivery Deadline: {deadline}\n\n"
                    f"Status:\n"
                    f"Your funds are securely locked in escrow. Freelancer {seller.name} has been notified that funding is confirmed and work may begin immediately.\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"Escrow Funded: {title}",
                    headline=f"Escrow Funded: {title}",
                    recipient_name=buyer.name,
                    greeting_text=f"Your escrow hold of <strong>{total_amount:,.2f} {currency}</strong> has been successfully authorized and locked on PayPal rails.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Contract ID", contract_id),
                        ("Secured Hold", f"{total_amount:,.2f} {currency}"),
                        ("PayPal Auth ID", paypal_auth_id),
                        ("Hold Expiry", auth_expires_at),
                        ("Delivery Deadline", deadline)
                    ],
                    callout_text="Your money is protected by PactPal's 29-day authorization hold and will only disburse when deliverables pass verification.",
                    action_note=f"Freelancer {seller.name} has been given the green light to begin development.",
                    badge_text="Escrow Active",
                    badge_color="#059669"
                )
            else:  # SELLER
                subject = f"[PactPal] Escrow Secured: Work Begins on {title} ({total_amount:,.2f} {currency})"
                body_text = (
                    f"Hello {seller.name},\n\n"
                    f"Great news! Client {buyer.name} has successfully funded the escrow authorization hold for '{title}' (Contract ID: {contract_id}).\n\n"
                    f"Escrow Details:\n"
                    f"- Secured Hold Amount: {total_amount:,.2f} {currency}\n"
                    f"- PayPal Authorization ID: {paypal_auth_id}\n"
                    f"- Delivery Deadline: {deadline}\n\n"
                    f"Status:\n"
                    f"Funds are safely held under PactPal Zero-Trust Multimodal Escrow. You may now commence development with guaranteed payment upon passing verified acceptance criteria.\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"Escrow Secured: {title}",
                    headline=f"Funds Secured: You May Begin Work",
                    recipient_name=seller.name,
                    greeting_text=f"Client <strong>{buyer.name}</strong> has deposited <strong>{total_amount:,.2f} {currency}</strong> into PactPal escrow hold.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Contract ID", contract_id),
                        ("Escrow Balance", f"{total_amount:,.2f} {currency}"),
                        ("PayPal Auth ID", paypal_auth_id),
                        ("Client", f"{buyer.name} ({buyer.email})"),
                        ("Delivery Deadline", deadline)
                    ],
                    callout_text="Your payment is guaranteed upon submitting deliverables that satisfy the locked feature checklist acceptance tests.",
                    action_note="You may now commence development with complete confidence.",
                    badge_text="Funds Secured",
                    badge_color="#059669"
                )
            return subject, body_text, body_html

        # ---------------------------------------------------------------------
        # 3. SUBMITTED
        # ---------------------------------------------------------------------
        elif state == "SUBMITTED":
            repo_url = metadata.get("repo_url") or contract.get("repo_url") or "Repository attached"
            commit_sha = metadata.get("commit_sha") or "HEAD"
            sub_num = metadata.get("submission_number", 1)
            submitted_at = metadata.get("submitted_at") or datetime.now(timezone.utc).isoformat()

            if role == "BUYER":
                subject = f"[PactPal] Deliverable Submitted: {title} - Verification Queued"
                body_text = (
                    f"Hello {buyer.name},\n\n"
                    f"Freelancer {seller.name} has submitted the deliverable for contract '{title}' (Contract ID: {contract_id}).\n\n"
                    f"Submission Details:\n"
                    f"- Submission Number: #{sub_num}\n"
                    f"- Repository URL: {repo_url}\n"
                    f"- Commit SHA: {commit_sha}\n"
                    f"- Submitted At: {submitted_at}\n\n"
                    f"Next Step:\n"
                    f"The autonomous multi-modal AI Referee pipeline has been queued to inspect test results, verify checklist features, and run cheat detection.\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"Deliverable Submitted: {title}",
                    headline=f"Deliverable Submitted: {title}",
                    recipient_name=buyer.name,
                    greeting_text=f"Freelancer <strong>{seller.name}</strong> has submitted code deliverables for verification.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Submission #", f"#{sub_num}"),
                        ("Repository URL", repo_url),
                        ("Commit SHA", commit_sha[:12] if len(commit_sha) > 12 else commit_sha),
                        ("Submitted At", submitted_at)
                    ],
                    callout_text="The automated referee pipeline is preparing to execute containerized sandbox tests, AST loophole scans, and visual diff analysis.",
                    action_note="You do not need to take any action; verification results will be posted automatically.",
                    badge_text="Deliverable Submitted",
                    badge_color="#0284C7"
                )
            else:  # SELLER
                subject = f"[PactPal] Submission Confirmed: {title} (Submission #{sub_num})"
                body_text = (
                    f"Hello {seller.name},\n\n"
                    f"Your deliverable submission for contract '{title}' (Contract ID: {contract_id}) has been received successfully.\n\n"
                    f"Submission Details:\n"
                    f"- Submission Number: #{sub_num}\n"
                    f"- Repository URL: {repo_url}\n"
                    f"- Commit SHA: {commit_sha}\n"
                    f"- Submitted At: {submitted_at}\n\n"
                    f"Status:\n"
                    f"Your code is queued for automated referee verification across sandbox test suites, AST loophole checks, and visual diff analysis.\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"Submission Received: {title}",
                    headline=f"Submission Received: #{sub_num}",
                    recipient_name=seller.name,
                    greeting_text="Your deliverable has been safely logged in the PactPal repository.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Submission #", f"#{sub_num}"),
                        ("Repository URL", repo_url),
                        ("Commit SHA", commit_sha[:12] if len(commit_sha) > 12 else commit_sha),
                        ("Submitted At", submitted_at)
                    ],
                    callout_text="Your code is queued for multi-stage automated test evaluation and referee inspection.",
                    action_note="You will be notified as soon as verification completes.",
                    badge_text="Submission Queued",
                    badge_color="#0284C7"
                )
            return subject, body_text, body_html

        # ---------------------------------------------------------------------
        # 4. VERIFYING
        # ---------------------------------------------------------------------
        elif state == "VERIFYING":
            if role == "BUYER":
                subject = f"[PactPal] Multi-Modal Verification In Progress: {title}"
                body_text = (
                    f"Hello {buyer.name},\n\n"
                    f"The multi-modal verification pipeline is actively evaluating the submitted deliverable for contract '{title}' (Contract ID: {contract_id}).\n\n"
                    f"Active Verification Stages:\n"
                    f"1. Stage A: Repository intake & dependency validation\n"
                    f"2. Stage B: Isolated container build execution & automated test runner\n"
                    f"3. Stage C: Static AST cheat scan & loophole detection\n"
                    f"4. Stage D: Multi-viewport visual diff and layout screenshot comparison\n\n"
                    f"Status:\n"
                    f"Autonomous verification is in progress. You will receive an immediate update once the AI Referee issues the final verdict.\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"Verification In Progress: {title}",
                    headline="Multi-Modal Verification In Progress",
                    recipient_name=buyer.name,
                    greeting_text=f"The AI Referee is actively inspecting the deliverable for <strong>{title}</strong>.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Contract ID", contract_id),
                        ("Pipeline Stages", "Stage A (Intake) &bull; Stage B (Build & Tests) &bull; Stage C (Cheat Scan) &bull; Stage D (Visual Diff)"),
                        ("Environment", "Isolated Ephemeral Docker Worker"),
                        ("Status", "RUNNING")
                    ],
                    callout_text="Tests and cheat detection scans are executing in isolated sandboxes to guarantee zero-trust compliance.",
                    action_note="Verification report and referee verdict will be generated shortly.",
                    badge_text="Active Verification",
                    badge_color="#7C3AED"
                )
            else:  # SELLER
                subject = f"[PactPal] Deliverable Under Active Verification: {title}"
                body_text = (
                    f"Hello {seller.name},\n\n"
                    f"Your submitted deliverable for contract '{title}' (Contract ID: {contract_id}) is currently undergoing multi-modal verification.\n\n"
                    f"Active Verification Stages:\n"
                    f"1. Stage A: Repository intake & dependency validation\n"
                    f"2. Stage B: Container build & automated acceptance tests\n"
                    f"3. Stage C: Static AST cheat scan & loophole detection\n"
                    f"4. Stage D: Visual diff analysis against UI specifications\n\n"
                    f"Status:\n"
                    f"Tests are executing in isolated sandboxes. You will be notified with the final verdict and feature scoring.\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"Verification Running: {title}",
                    headline="Verification Underway",
                    recipient_name=seller.name,
                    greeting_text="Your submitted code is undergoing automated sandbox testing and quality checks.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Contract ID", contract_id),
                        ("Verification Suite", "Acceptance Tests &bull; AST Code Scan &bull; UI Visual Diff"),
                        ("Status", "RUNNING")
                    ],
                    callout_text="Our multi-modal referee is verifying your checklist features against acceptance criteria.",
                    action_note="You will receive the verdict and score breakdown once tests complete.",
                    badge_text="Testing in Progress",
                    badge_color="#7C3AED"
                )
            return subject, body_text, body_html

        # ---------------------------------------------------------------------
        # 5. DECISION
        # ---------------------------------------------------------------------
        elif state == "DECISION":
            decision = str(metadata.get("decision") or metadata.get("verdict") or "VERIFIED").upper()
            score = str(metadata.get("score") or metadata.get("overall_score") or "100%")
            build_status = "PASSED" if metadata.get("build_succeeded", True) else "FAILED"
            features_passed = metadata.get("features_passed", len(contract.get("features", [])))
            features_total = metadata.get("features_total", max(len(contract.get("features", [])), 1))
            passed_amount = float(metadata.get("passed_amount", total_amount))
            refund_amount = float(metadata.get("refund_amount", 0.0))
            summary = metadata.get("summary") or metadata.get("findings") or "All verified acceptance tests satisfied requirements."
            seller_paypal_email = seller.paypal_email or seller.email

            if role == "BUYER":
                subject = f"[PactPal] AI Referee Verdict: {title} - {decision}"
                body_text = (
                    f"Hello {buyer.name},\n\n"
                    f"The AI Referee has concluded verification for contract '{title}' (Contract ID: {contract_id}) and rendered a decision.\n\n"
                    f"Referee Verdict:\n"
                    f"- Overall Verdict: {decision}\n"
                    f"- Verification Score: {score}\n"
                    f"- Build Status: {build_status}\n"
                    f"- Verified Features: {features_passed}/{features_total} passed\n\n"
                    f"Financial Allocation Preview:\n"
                    f"- Release to Seller: {passed_amount:,.2f} {currency}\n"
                    f"- Refund to You: {refund_amount:,.2f} {currency}\n\n"
                    f"Referee Findings:\n"
                    f"{summary}\n\n"
                    f"Next Step:\n"
                    f"Escrow settlement and disbursement will proceed in accordance with this verified verdict.\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"AI Referee Verdict: {title}",
                    headline=f"Referee Verdict: {decision}",
                    recipient_name=buyer.name,
                    greeting_text=f"The AI Referee has issued an automated verdict for contract <strong>{title}</strong>.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Verdict", decision),
                        ("Verification Score", str(score)),
                        ("Features Passed", f"{features_passed} of {features_total}"),
                        ("Release to Seller", f"{passed_amount:,.2f} {currency}"),
                        ("Refund to You", f"{refund_amount:,.2f} {currency}")
                    ],
                    callout_text=f"Referee Findings: {summary}",
                    action_note="Escrow settlement will execute capture and refund based on this verdict.",
                    badge_text=f"Verdict: {decision}",
                    badge_color="#059669" if decision in ("PASSED", "VERIFIED") else "#D97706"
                )
            else:  # SELLER
                subject = f"[PactPal] AI Referee Verdict: {title} - {decision}"
                body_text = (
                    f"Hello {seller.name},\n\n"
                    f"The AI Referee has concluded verification for contract '{title}' (Contract ID: {contract_id}) and rendered a decision.\n\n"
                    f"Referee Verdict:\n"
                    f"- Overall Verdict: {decision}\n"
                    f"- Verification Score: {score}\n"
                    f"- Build Status: {build_status}\n"
                    f"- Verified Features: {features_passed}/{features_total} passed\n\n"
                    f"Financial Allocation Preview:\n"
                    f"- Disbursed Earnings: {passed_amount:,.2f} {currency}\n"
                    f"- Deductions / Refund to Buyer: {refund_amount:,.2f} {currency}\n\n"
                    f"Referee Findings:\n"
                    f"{summary}\n\n"
                    f"Next Step:\n"
                    f"Payout will be disbursed to your PayPal account ({seller_paypal_email}).\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"AI Referee Verdict: {title}",
                    headline=f"Referee Verdict: {decision}",
                    recipient_name=seller.name,
                    greeting_text=f"The AI Referee has evaluated your deliverable for <strong>{title}</strong>.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Verdict", decision),
                        ("Verification Score", str(score)),
                        ("Features Passed", f"{features_passed} of {features_total}"),
                        ("Disbursed Earnings", f"{passed_amount:,.2f} {currency}"),
                        ("Deductions / Refund", f"{refund_amount:,.2f} {currency}")
                    ],
                    callout_text=f"Referee Findings: {summary}",
                    action_note=f"Payment will disburse to your registered PayPal account ({seller_paypal_email}).",
                    badge_text=f"Verdict: {decision}",
                    badge_color="#059669" if decision in ("PASSED", "VERIFIED") else "#D97706"
                )
            return subject, body_text, body_html

        # ---------------------------------------------------------------------
        # 6. SETTLED / PAYOUT COMPLETE
        # ---------------------------------------------------------------------
        elif state in ("SETTLED", "PAYOUT_COMPLETE", "PAYOUT COMPLETE"):
            passed_amount = float(metadata.get("passed_amount", total_amount))
            refund_amount = float(metadata.get("refund_amount", 0.0))
            payout_batch_ref = str(metadata.get("payout_batch_reference") or metadata.get("payout_batch_id") or "BATCH_COMPLETED")
            receipt_hash = str(metadata.get("receipt_hash") or "SHA256_VERIFIED_FINGERPRINT")
            seller_paypal_email = seller.paypal_email or seller.email

            # Compute human-readable settlement rationale
            if "why" in metadata:
                why_explanation = str(metadata["why"])
            elif passed_amount > 0 and refund_amount == 0:
                why_explanation = f"All checklist acceptance tests verified successfully. 100% full payout of {passed_amount:,.2f} {currency} disbursed to seller."
            elif passed_amount == 0 and refund_amount > 0:
                why_explanation = f"No checklist features met acceptance criteria or project was abandoned. 100% full refund of {refund_amount:,.2f} {currency} returned to buyer."
            else:
                why_explanation = (
                    f"Proportional partial split verified: {passed_amount:,.2f} {currency} released for passed features, "
                    f"and {refund_amount:,.2f} {currency} returned to buyer for failed/unverified features."
                )

            if role == "BUYER":
                subject = f"[PactPal] Escrow Settlement Completed: {title}"
                body_text = (
                    f"Hello {buyer.name},\n\n"
                    f"Escrow settlement for contract '{title}' (Contract ID: {contract_id}) has been successfully completed.\n\n"
                    f"Financial Settlement Summary:\n"
                    f"- Amount Released to Seller ({seller.name}): {passed_amount:,.2f} {currency}\n"
                    f"- Amount Refunded to You: {refund_amount:,.2f} {currency}\n"
                    f"- Total Contract Value: {total_amount:,.2f} {currency}\n\n"
                    f"Settlement Rationale:\n"
                    f"{why_explanation}\n\n"
                    f"Cryptographic Proof-of-Work Receipt:\n"
                    f"- Receipt Hash (SHA-256): {receipt_hash}\n"
                    f"- Verification Link: /api/v1/contracts/{contract_id}/receipt\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"Settlement Completed: {title}",
                    headline=f"Escrow Settlement Completed: {title}",
                    recipient_name=buyer.name,
                    greeting_text="Escrow capture and refunds have been finalized on PayPal rails.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Contract ID", contract_id),
                        ("Released to Seller", f"{passed_amount:,.2f} {currency}"),
                        ("Refunded to You", f"{refund_amount:,.2f} {currency}"),
                        ("Total Contract Value", f"{total_amount:,.2f} {currency}"),
                        ("Proof-of-Work Hash", f"<code>{receipt_hash[:16]}...</code>")
                    ],
                    callout_text=f"Settlement Details: {why_explanation}",
                    action_note=f"You can view and cryptographically verify the immutable receipt at /api/v1/contracts/{contract_id}/receipt.",
                    badge_text="Settlement Finalized",
                    badge_color="#059669"
                )
            else:  # SELLER
                subject = f"[PactPal] Payout Disbursed: {passed_amount:,.2f} {currency} for {title}"
                body_text = (
                    f"Hello {seller.name},\n\n"
                    f"Your payout for contract '{title}' (Contract ID: {contract_id}) has been disbursed to your PayPal account.\n\n"
                    f"Disbursement Details:\n"
                    f"- Amount Disbursed to You: {passed_amount:,.2f} {currency}\n"
                    f"- PayPal Payout Batch ID: {payout_batch_ref}\n"
                    f"- Refund to Buyer: {refund_amount:,.2f} {currency}\n"
                    f"- Total Contract Value: {total_amount:,.2f} {currency}\n\n"
                    f"Settlement Rationale:\n"
                    f"{why_explanation}\n\n"
                    f"Cryptographic Proof-of-Work Receipt:\n"
                    f"- Receipt Hash (SHA-256): {receipt_hash}\n\n"
                    f"PactPal Zero-Trust Multimodal Escrow"
                )
                body_html = cls._wrap_html(
                    title=f"Payout Disbursed: {title}",
                    headline=f"Payout Disbursed: {passed_amount:,.2f} {currency}",
                    recipient_name=seller.name,
                    greeting_text=f"Your earnings for <strong>{title}</strong> have been disbursed via PayPal Payouts.",
                    key_value_pairs=[
                        ("Contract Title", title),
                        ("Disbursed Earnings", f"{passed_amount:,.2f} {currency}"),
                        ("PayPal Batch ID", payout_batch_ref),
                        ("Refund to Buyer", f"{refund_amount:,.2f} {currency}"),
                        ("Destination Account", seller_paypal_email),
                        ("Proof-of-Work Hash", f"<code>{receipt_hash[:16]}...</code>")
                    ],
                    callout_text=f"Settlement Details: {why_explanation}",
                    action_note="Funds are transferred directly to your PayPal account balance.",
                    badge_text="Payout Disbursed",
                    badge_color="#059669"
                )
            return subject, body_text, body_html

        # Fallback generic state template
        subject = f"[PactPal] Contract Update: {title} ({state})"
        body_text = (
            f"Hello {role.title()},\n\n"
            f"Contract '{title}' (ID: {contract_id}) has transitioned to {state}.\n\n"
            f"PactPal Zero-Trust Multimodal Escrow"
        )
        body_html = cls._wrap_html(
            title=f"Contract Update: {title}",
            headline=f"Contract Status: {state}",
            recipient_name=role.title(),
            greeting_text=f"Contract {title} has progressed to state <strong>{state}</strong>.",
            key_value_pairs=[("Contract", title), ("State", state)],
            callout_text="PactPal autonomous tracking active."
        )
        return subject, body_text, body_html


# -----------------------------------------------------------------------------
# Automated Notification Service
# -----------------------------------------------------------------------------

class EmailNotificationService:
    """
    Central Email Notification Orchestrator.
    Dispatches tailored notifications for each of the 6 core contract milestones.
    """

    SUPPORTED_MILESTONES = {
        "SIGNED",
        "FUNDED",
        "SUBMITTED",
        "VERIFYING",
        "DECISION",
        "SETTLED"
    }

    STATE_ALIASES = {
        "PAYOUT_COMPLETE": "SETTLED",
        "PAYOUT COMPLETE": "SETTLED",
        "PAYOUT": "SETTLED",
        "COMPLETE": "SETTLED",
    }

    def __init__(
        self,
        repository: Optional[Any] = None,
        provider: Optional[BaseEmailProvider] = None,
        auto_wire: bool = True
    ):
        self.repository = repository
        self.provider = provider or get_email_provider()
        self._recent_dispatches: Dict[str, float] = {}

        if auto_wire and self.repository and hasattr(self.repository, "set_notification_service"):
            self.repository.set_notification_service(self)

    def normalize_state(self, raw_state: str) -> Optional[str]:
        """Maps incoming state strings to canonical milestone states."""
        clean = str(raw_state).upper().strip()
        canonical = self.STATE_ALIASES.get(clean, clean)
        return canonical if canonical in self.SUPPORTED_MILESTONES else None

    def resolve_recipients(
        self,
        contract: Dict[str, Any]
    ) -> Tuple[NotificationRecipient, NotificationRecipient]:
        """
        Dynamically extracts Buyer and Seller recipients from contract and database records.
        """
        buyer_id = contract.get("buyer_id")
        seller_id = contract.get("seller_id")

        buyer_user = None
        seller_user = None

        if self.repository and hasattr(self.repository, "get_user"):
            if buyer_id:
                buyer_user = self.repository.get_user(buyer_id)
            if seller_id:
                seller_user = self.repository.get_user(seller_id)

        # Buyer resolution
        if buyer_user:
            buyer = NotificationRecipient(
                email=buyer_user.email,
                name=buyer_user.name,
                role="BUYER",
                user_id=buyer_user.id,
                paypal_email=buyer_user.paypal_email
            )
        else:
            buyer = NotificationRecipient(
                email=contract.get("buyer_email") or f"buyer_{str(buyer_id)[:8]}@example.com",
                name=contract.get("buyer_name") or f"Buyer ({str(buyer_id)[:8]})",
                role="BUYER",
                user_id=buyer_id
            )

        # Seller resolution
        if seller_user:
            seller = NotificationRecipient(
                email=seller_user.email,
                name=seller_user.name,
                role="SELLER",
                user_id=seller_user.id,
                paypal_email=seller_user.paypal_email
            )
        else:
            seller = NotificationRecipient(
                email=contract.get("seller_email") or contract.get("seller_paypal_email") or f"seller_{str(seller_id)[:8]}@example.com",
                name=contract.get("seller_name") or f"Freelancer ({str(seller_id)[:8]})",
                role="SELLER",
                user_id=seller_id,
                paypal_email=contract.get("seller_paypal_email")
            )

        return buyer, seller

    def _enrich_metadata_from_db(
        self,
        contract_id: str,
        state: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Pulls missing context dynamically from submissions, verification reports, receipts, or payments."""
        enriched = dict(metadata)
        if not self.repository:
            return enriched

        # If SUBMITTED or VERIFYING: pull deliverable submission details
        if state in ("SUBMITTED", "VERIFYING"):
            if hasattr(self.repository, "get_latest_submission"):
                sub = self.repository.get_latest_submission(contract_id)
                if sub:
                    enriched.setdefault("repo_url", sub.get("repo_url"))
                    enriched.setdefault("commit_sha", sub.get("commit_sha"))
                    enriched.setdefault("submission_number", sub.get("submission_number", 1))
                    enriched.setdefault("submitted_at", sub.get("submitted_at"))

        # If DECISION: pull verification report
        if state == "DECISION":
            if hasattr(self.repository, "get_latest_verification_report"):
                rep = self.repository.get_latest_verification_report(contract_id)
                if rep:
                    enriched.setdefault("score", f"{rep.get('overall_score', 100):.1f}%")
                    enriched.setdefault("build_succeeded", rep.get("build_succeeded", True))
                    per_feat = rep.get("per_feature_results", {})
                    if isinstance(per_feat, dict):
                        passed_cnt = sum(1 for f in per_feat.values() if isinstance(f, dict) and f.get("status") == "PASSED")
                        enriched.setdefault("features_passed", passed_cnt)
                        enriched.setdefault("features_total", len(per_feat))

        # If SETTLED: pull receipt and payments
        if state == "SETTLED":
            if hasattr(self.repository, "get_receipt"):
                rec = self.repository.get_receipt(contract_id)
                if rec:
                    enriched.setdefault("receipt_hash", rec.get("receipt_hash"))
            if hasattr(self.repository, "get_payments"):
                payments = self.repository.get_payments(contract_id)
                payout = next((p for p in payments if p.get("payment_type") == "PAYOUT"), None)
                if payout:
                    enriched.setdefault("payout_batch_reference", payout.get("paypal_reference_id"))
                    enriched.setdefault("passed_amount", payout.get("amount"))

        return enriched

    def notify_state_change(
        self,
        contract_id: str,
        new_state: str,
        metadata: Optional[Dict[str, Any]] = None,
        actor: Optional[Any] = None,
        force: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Dispatches tailored email notifications to both Buyer and Seller for a state milestone.
        Returns list of dispatch result dicts.
        """
        canonical_state = self.normalize_state(new_state)
        if not canonical_state:
            return []

        # De-duplication check: prevent multiple sends within a 2-second burst unless force=True
        dedup_key = f"{contract_id}:{canonical_state}"
        now_ts = datetime.now(timezone.utc).timestamp()
        if not force:
            last_ts = self._recent_dispatches.get(dedup_key)
            if last_ts and (now_ts - last_ts < 2.0):
                return []
        self._recent_dispatches[dedup_key] = now_ts

        # Retrieve contract
        contract = None
        if self.repository and hasattr(self.repository, "get_contract"):
            contract = self.repository.get_contract(contract_id)
        if not contract:
            contract = {
                "id": contract_id,
                "title": f"Contract {contract_id[:8]}",
                "total_amount": 0.0,
                "currency": "USD",
                "deadline": "N/A"
            }

        # Resolve participants
        buyer, seller = self.resolve_recipients(contract)

        # Enrich metadata
        meta = self._enrich_metadata_from_db(contract_id, canonical_state, metadata or {})

        dispatched_records: List[Dict[str, Any]] = []

        # Send to both Buyer and Seller
        for recipient in (buyer, seller):
            subject, body_text, body_html = EmailTemplateEngine.render(
                state=canonical_state,
                role=recipient.role,
                contract=contract,
                buyer=buyer,
                seller=seller,
                metadata=meta
            )

            send_meta = {
                "contract_id": contract_id,
                "role": recipient.role,
                "state_transition": canonical_state,
                "actor_id": getattr(actor, "id", None) if actor else None
            }

            try:
                result = self.provider.send_email(
                    to_email=recipient.email,
                    subject=subject,
                    body_text=body_text,
                    body_html=body_html,
                    metadata=send_meta
                )
                delivery_status = result.get("status", "SENT")
                message_id = result.get("message_id", f"msg_{uuid.uuid4().hex[:12]}")
            except Exception as e:
                delivery_status = "FAILED"
                message_id = f"err_{uuid.uuid4().hex[:12]}"

            # Immutable audit logging in messages table
            if self.repository and hasattr(self.repository, "record_message"):
                try:
                    self.repository.record_message(
                        contract_id=contract_id,
                        content=f"Email notification sent to {recipient.role} ({recipient.email}): {subject}",
                        sender_type="AI_REFEREE",
                        sender_id=None,
                        metadata={
                            "event": "EMAIL_NOTIFICATION_SENT",
                            "recipient_email": recipient.email,
                            "recipient_name": recipient.name,
                            "role": recipient.role,
                            "state_transition": canonical_state,
                            "subject": subject,
                            "delivery_status": delivery_status,
                            "message_id": message_id,
                            "provider": getattr(self.provider, "name", "unknown"),
                            "sent_at": datetime.now(timezone.utc).isoformat(),
                            "contract_id": contract_id
                        }
                    )
                except Exception:
                    pass

            dispatched_records.append({
                "recipient": recipient.email,
                "recipient_name": recipient.name,
                "role": recipient.role,
                "subject": subject,
                "message_id": message_id,
                "delivery_status": delivery_status,
                "state_transition": canonical_state,
                "sent_at": datetime.now(timezone.utc).isoformat()
            })

        return dispatched_records

    # --- Convenience Trigger Methods ---
    def notify_signed(self, contract_id: str, metadata: Optional[Dict[str, Any]] = None, actor: Optional[Any] = None) -> List[Dict[str, Any]]:
        return self.notify_state_change(contract_id, "SIGNED", metadata, actor, force=True)

    def notify_funded(self, contract_id: str, metadata: Optional[Dict[str, Any]] = None, actor: Optional[Any] = None) -> List[Dict[str, Any]]:
        return self.notify_state_change(contract_id, "FUNDED", metadata, actor, force=True)

    def notify_submitted(self, contract_id: str, metadata: Optional[Dict[str, Any]] = None, actor: Optional[Any] = None) -> List[Dict[str, Any]]:
        return self.notify_state_change(contract_id, "SUBMITTED", metadata, actor, force=True)

    def notify_verifying(self, contract_id: str, metadata: Optional[Dict[str, Any]] = None, actor: Optional[Any] = None) -> List[Dict[str, Any]]:
        return self.notify_state_change(contract_id, "VERIFYING", metadata, actor, force=True)

    def notify_decision(self, contract_id: str, metadata: Optional[Dict[str, Any]] = None, actor: Optional[Any] = None) -> List[Dict[str, Any]]:
        return self.notify_state_change(contract_id, "DECISION", metadata, actor, force=True)

    def notify_payout_complete(self, contract_id: str, metadata: Optional[Dict[str, Any]] = None, actor: Optional[Any] = None) -> List[Dict[str, Any]]:
        return self.notify_state_change(contract_id, "SETTLED", metadata, actor, force=True)

    def notify_settled(self, contract_id: str, metadata: Optional[Dict[str, Any]] = None, actor: Optional[Any] = None) -> List[Dict[str, Any]]:
        return self.notify_state_change(contract_id, "SETTLED", metadata, actor, force=True)

    # --- Inspection & Audit Retrieval ---
    def get_contract_notifications(
        self,
        contract_id: str,
        actor: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves sent notification records for a contract from messages table with RBAC checks."""
        if not self.repository:
            return []

        contract = self.repository.get_contract(contract_id) if hasattr(self.repository, "get_contract") else None
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        if actor and assert_can_view_notifications:
            assert_can_view_notifications(actor, contract)

        if hasattr(self.repository, "get_contract_notifications"):
            return self.repository.get_contract_notifications(contract_id)

        # Fallback query
        if hasattr(self.repository, "get_messages"):
            messages = self.repository.get_messages(contract_id)
            res = []
            for m in messages:
                meta = m.get("metadata")
                if isinstance(meta, dict) and meta.get("event") == "EMAIL_NOTIFICATION_SENT":
                    res.append({
                        "id": m.get("id"),
                        "contract_id": contract_id,
                        "recipient_email": meta.get("recipient_email"),
                        "recipient_name": meta.get("recipient_name"),
                        "role": meta.get("role"),
                        "state_transition": meta.get("state_transition"),
                        "subject": meta.get("subject"),
                        "delivery_status": meta.get("delivery_status"),
                        "message_id": meta.get("message_id"),
                        "provider": meta.get("provider"),
                        "sent_at": meta.get("sent_at") or m.get("sent_at")
                    })
            return res
        return []

