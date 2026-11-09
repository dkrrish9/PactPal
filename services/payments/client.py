"""
PactPal PayPal REST API Client
Handles OAuth2 token caching, Orders creation with AUTHORIZE intent,
and Authorization capture execution against PayPal Sandbox/Live endpoints.
Linked Tasks: C10, C14, C24
"""

import os
import time
import json
import base64
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

def load_env_defaults():
    """Fallback loader for local .env if not already loaded into os.environ."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

load_env_defaults()

class PayPalAPIError(Exception):
    """Raised when PayPal returns an error response or network failure."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}

class PayPalClient:
    """
    Production-ready PayPal REST API v2 client.
    Supports client credential caching, order creation with AUTHORIZE intent,
    and authorization capture execution.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.client_id = client_id or os.environ.get("PAYPAL_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("PAYPAL_CLIENT_SECRET")
        self.base_url = (base_url or os.environ.get("PAYPAL_API_BASE_URL", "https://api-m.sandbox.paypal.com")).rstrip("/")

        # OAuth2 token caching
        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Retrieves a valid OAuth2 Bearer token from PayPal.
        Caches token in-memory and auto-refreshes 60s before expiration.
        """
        now = time.time()
        if not force_refresh and self._cached_token and now < (self._token_expires_at - 60):
            return self._cached_token

        if not self.client_id or not self.client_secret:
            raise PayPalAPIError("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be set.")

        url = f"{self.base_url}/v1/oauth2/token"
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

        req = urllib.request.Request(
            url,
            data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                self._cached_token = data["access_token"]
                expires_in = int(data.get("expires_in", 32400))
                self._token_expires_at = now + expires_in
                return self._cached_token
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()
            raise PayPalAPIError(f"OAuth2 failed ({e.code}): {err_body}", status_code=e.code)
        except Exception as e:
            raise PayPalAPIError(f"Failed to connect to PayPal OAuth: {str(e)}")

    def _send_authorized_request(
        self,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
        method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes an authenticated HTTP request against PayPal REST API.
        Includes automatic 1-time token refresh on HTTP 401 Unauthorized.
        """
        token = self.get_access_token()
        req_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Token may have expired upstream; force refresh and retry once
                fresh_token = self.get_access_token(force_refresh=True)
                req_headers["Authorization"] = f"Bearer {fresh_token}"
                retry_req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
                try:
                    with urllib.request.urlopen(retry_req, timeout=15) as resp:
                        return json.loads(resp.read().decode())
                except urllib.error.HTTPError as retry_e:
                    err_body = retry_e.read().decode()
                    raise PayPalAPIError(f"Request failed after token refresh ({retry_e.code}): {err_body}", status_code=retry_e.code)
            err_body = e.read().decode()
            raise PayPalAPIError(f"PayPal API error ({e.code}): {err_body}", status_code=e.code)
        except Exception as e:
            raise PayPalAPIError(f"Failed to communicate with PayPal API: {str(e)}")

    def create_authorize_order(
        self,
        reference_id: str,
        amount: float,
        currency: str = "USD",
        description: str = "PactPal Milestone Escrow Hold",
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a PayPal Order with intent 'AUTHORIZE' (funds reserved, not captured).
        Returns order ID and the buyer approval redirect URL.
        """
        frontend_base = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
        resolved_return = return_url or f"{frontend_base}/contracts/funded"
        resolved_cancel = cancel_url or f"{frontend_base}/contracts/cancel"

        url = f"{self.base_url}/v2/checkout/orders"

        payload = {
            "intent": "AUTHORIZE",
            "purchase_units": [{
                "reference_id": str(reference_id),
                "description": description,
                "amount": {
                    "currency_code": currency,
                    "value": f"{amount:.2f}"
                }
            }],
            "application_context": {
                "return_url": resolved_return,
                "cancel_url": resolved_cancel,
                "user_action": "CONTINUE",
                "brand_name": "PactPal Escrow"
            }
        }

        data = self._send_authorized_request(url, data=json.dumps(payload).encode(), method="POST")
        order_id = data["id"]
        approve_url = next(
            (link["href"] for link in data.get("links", []) if link.get("rel") == "approve"),
            None
        )
        return {
            "order_id": order_id,
            "approve_url": approve_url,
            "status": data.get("status"),
            "intent": "AUTHORIZE",
            "raw_response": data
        }

    def execute_authorization(self, order_id: str) -> Dict[str, Any]:
        """
        Executes authorization against an approved PayPal order.
        Extracts and returns the live authorization_id and holding status.
        """
        url = f"{self.base_url}/v2/checkout/orders/{order_id}/authorize"
        data = self._send_authorized_request(url, data=json.dumps({}).encode(), method="POST")

        # Extract authorization reference from purchase_units
        purchase_units = data.get("purchase_units", [])
        if not purchase_units:
            raise PayPalAPIError("Malformed PayPal response: missing purchase_units", details=data)

        payments = purchase_units[0].get("payments", {})
        authorizations = payments.get("authorizations", [])
        if not authorizations:
            raise PayPalAPIError("No authorization generated for order", details=data)

        primary_auth = authorizations[0]
        auth_id = primary_auth["id"]
        auth_status = primary_auth.get("status")
        expiration_time = primary_auth.get("expiration_time")

        return {
            "order_id": order_id,
            "authorization_id": auth_id,
            "status": auth_status,
            "expiration_time": expiration_time,
            "amount": primary_auth.get("amount", {}).get("value"),
            "currency": primary_auth.get("amount", {}).get("currency_code"),
            "raw_response": data
        }

    def get_authorization(self, authorization_id: str) -> Dict[str, Any]:
        """
        Fetches live authorization details from PayPal REST API v2.
        Endpoint: GET /v2/payments/authorizations/{authorization_id}
        """
        url = f"{self.base_url}/v2/payments/authorizations/{authorization_id}"
        data = self._send_authorized_request(url, method="GET")

        return {
            "authorization_id": data.get("id"),
            "status": data.get("status"),
            "expiration_time": data.get("expiration_time"),
            "amount": data.get("amount", {}).get("value"),
            "currency": data.get("amount", {}).get("currency_code"),
            "raw_response": data
        }


