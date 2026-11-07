#!/usr/bin/env python3
"""
PactPal PayPal Sandbox Escrow Spike Runner
Tests the core PayPal rails required for PactPal:
  1. OAuth2 Token Generation
  2. Order Creation with AUTHORIZE intent (Milestone funding)
  3. Payouts API execution (Milestone release)
  4. Payout status polling and confirmation
"""

import os
import sys
import json
import time
import base64
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

def load_env():
    """Load key-value pairs from .env in project root if available."""
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

load_env()

CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID")
CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET")
BASE_URL = os.environ.get("PAYPAL_API_BASE_URL", "https://api-m.sandbox.paypal.com")
RECEIVER_EMAIL = os.environ.get("PAYPAL_SANDBOX_BUYER_EMAIL", "sb-zzudl53771742@personal.example.com")

if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be set in .env")
    sys.exit(1)

def get_access_token():
    print("\n--- 1. Generating OAuth2 Access Token ---")
    url = f"{BASE_URL}/v1/oauth2/token"
    auth_b64 = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"Token acquired. Expires in: {data.get('expires_in')}s")
        return data["access_token"]

def create_authorize_order(token, amount="100.00", currency="USD"):
    print(f"\n--- 2. Creating Order with AUTHORIZE intent (${amount} {currency}) ---")
    url = f"{BASE_URL}/v2/checkout/orders"
    payload = {
        "intent": "AUTHORIZE",
        "purchase_units": [{
            "reference_id": f"pactpal_spike_{int(time.time())}",
            "description": "Milestone Escrow Hold (PactPal)",
            "amount": {
                "currency_code": currency,
                "value": amount
            }
        }],
        "application_context": {
            "return_url": "http://localhost:3000/contracts/spike/success",
            "cancel_url": "http://localhost:3000/contracts/spike/cancel",
            "user_action": "CONTINUE"
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        order_id = data["id"]
        approve_url = next(link["href"] for link in data["links"] if link["rel"] == "approve")
        print(f"Order created successfully: {order_id}")
        print(f"Approval Link (for Buyer redirect): {approve_url}")
        return order_id, approve_url

def execute_test_payout(token, receiver_email, amount="10.00", currency="USD"):
    print(f"\n--- 3. Executing Test Payout to Seller (${amount} {currency}) ---")
    url = f"{BASE_URL}/v1/payments/payouts"
    batch_id = f"spike_batch_{int(time.time())}"
    payload = {
        "sender_batch_header": {
            "sender_batch_id": batch_id,
            "email_subject": "PactPal Milestone Payout Released",
            "email_message": "Feature tests passed. Milestone funds released by PactPal AI Referee."
        },
        "items": [{
            "recipient_type": "EMAIL",
            "amount": {
                "value": amount,
                "currency": currency
            },
            "receiver": receiver_email,
            "note": "Payment for verified checklist items",
            "sender_item_id": f"pactpal_item_{int(time.time())}"
        }]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        payout_batch_id = data["batch_header"]["payout_batch_id"]
        print(f"Payout Batch Submitted: {payout_batch_id} (Status: {data['batch_header']['batch_status']})")
        return payout_batch_id

def verify_payout_status(token, payout_batch_id):
    print(f"\n--- 4. Polling Payout Status for Batch: {payout_batch_id} ---")
    url = f"{BASE_URL}/v1/payments/payouts/{payout_batch_id}"
    for attempt in range(6):
        time.sleep(2)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                batch_status = data["batch_header"]["batch_status"]
                items = data.get("items", [])
                item_status = items[0].get("transaction_status") if items else "UNKNOWN"
                print(f"  Check {attempt + 1}: Batch={batch_status}, Item={item_status}")
                if item_status == "SUCCESS":
                    item_id = items[0].get("payout_item_id")
                    print(f"\nSUCCESS! Payout completed successfully. Item ID: {item_id}")
                    return True
        except Exception as e:
            print(f"  Polling error: {e}")
    return False

def main():
    print("=" * 60)
    print("PactPal PayPal Sandbox Escrow Spike Runner")
    print(f"Target Sandbox Endpoint: {BASE_URL}")
    print(f"Testing Recipient: {RECEIVER_EMAIL}")
    print("=" * 60)

    token = get_access_token()
    order_id, approve_url = create_authorize_order(token, amount="100.00")
    batch_id = execute_test_payout(token, RECEIVER_EMAIL, amount="10.00")
    success = verify_payout_status(token, batch_id)

    if success:
        print("\nAll PayPal sandbox spike checks PASSED!")
        print("Ready for Gate 0 sync.")
    else:
        print("\nSpike execution completed (check batch status in sandbox dashboard).")

if __name__ == "__main__":
    main()

