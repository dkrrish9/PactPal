"""
PactPal Payments REST API Router & HTTP Dispatcher
Exposes payment rails endpoints matching shared/docs/SHARED_API_CONTRACT.md:
  - GET  /api/v1/contracts/{id}/hold: Exposes authorization expiry countdown data (C14)
  - POST /api/v1/payments/orders/create-hold: Creates PayPal order with AUTHORIZE intent (C10)
  - POST /api/v1/payments/orders/authorize: Executes authorization & marks contract FUNDED (C10)
"""

import re
import json
import urllib.parse
from typing import Dict, Any, Optional, Tuple
from wsgiref.simple_server import make_server

from .service import (
    EscrowPaymentService,
    ContractRepository,
    User,
    UserRole,
    ForbiddenActionError,
    StateValidationError
)

HOLD_ENDPOINT_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/hold/?$")
CREATE_HOLD_REGEX = re.compile(r"^/api/v1/payments/orders/create-hold/?$")
AUTHORIZE_HOLD_REGEX = re.compile(r"^/api/v1/payments/orders/authorize/?$")

class PaymentsAPIHandler:
    """
    HTTP request dispatcher for Payments & Escrow Subsystem.
    Provides standard JSON REST responses for frontend, webhooks, and referee services.
    """

    def __init__(self, service: Optional[EscrowPaymentService] = None):
        self.service = service or EscrowPaymentService()
        self.repository = self.service.repository

    def _extract_actor(self, headers: Dict[str, str]) -> Optional[User]:
        """
        Extracts actor context from X-Actor-Id or Authorization header.
        Supports:
          - X-Actor-Id: <user_id>
          - Authorization: Bearer <user_id_or_token>
        """
        # Normalize header keys to lowercase
        norm_headers = {k.lower(): v for k, v in headers.items()}
        actor_id = norm_headers.get("x-actor-id")

        if not actor_id:
            auth = norm_headers.get("authorization", "")
            if auth.startswith("Bearer "):
                actor_id = auth[7:].strip()

        if not actor_id:
            return None

        # Look up user in repository
        return self.repository.get_user(actor_id)

    def dispatch(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Dispatches request and returns (status_code, response_headers, response_body_bytes).
        """
        headers = headers or {}
        method = method.upper()
        clean_path = path.split("?")[0]

        # 1. GET /api/v1/contracts/{id}/hold
        match_hold = HOLD_ENDPOINT_REGEX.match(clean_path)
        if match_hold:
            if method != "GET":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on hold endpoint."})
            contract_id = match_hold.group(1)
            return self._handle_get_hold(contract_id, headers)

        # 2. POST /api/v1/payments/orders/create-hold
        if CREATE_HOLD_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on create-hold."})
            return self._handle_create_hold(headers, body)

        # 3. POST /api/v1/payments/orders/authorize
        if AUTHORIZE_HOLD_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on authorize."})
            return self._handle_authorize(headers, body)

        return self._json_response(404, {"error": "NOT_FOUND", "message": f"Endpoint '{clean_path}' not found in Payments API."})

    def _handle_get_hold(self, contract_id: str, headers: Dict[str, str]) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for GET /api/v1/contracts/{id}/hold.
        Returns amount, expiry date and time left for the countdown (29-day limit).
        """
        actor = self._extract_actor(headers)
        if actor is None:
            # If actor is not supplied or invalid
            return self._json_response(
                401,
                {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."}
            )

        try:
            hold_data = self.service.get_contract_hold(contract_id=contract_id, actor=actor)
            return self._json_response(200, hold_data)
        except ValueError as e:
            # Contract not found
            return self._json_response(404, {"error": "NOT_FOUND", "message": str(e)})
        except ForbiddenActionError as e:
            # Actor not buyer, seller, or admin
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except StateValidationError as e:
            # Contract is not in funded state
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_create_hold(self, headers: Dict[str, str], body: Optional[bytes]) -> Tuple[int, Dict[str, str], bytes]:
        """Handler for POST /api/v1/payments/orders/create-hold."""
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(401, {"error": "UNAUTHORIZED", "message": "Authentication required."})

        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "Invalid JSON body."})

        contract_id = data.get("contract_id")
        if not contract_id:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "contract_id is required."})

        try:
            res = self.service.initiate_contract_hold(
                contract_id=contract_id,
                actor=actor,
                return_url=data.get("return_url"),
                cancel_url=data.get("cancel_url")
            )
            return self._json_response(200, res)
        except ValueError as e:
            return self._json_response(404, {"error": "NOT_FOUND", "message": str(e)})
        except ForbiddenActionError as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except StateValidationError as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_authorize(self, headers: Dict[str, str], body: Optional[bytes]) -> Tuple[int, Dict[str, str], bytes]:
        """Handler for POST /api/v1/payments/orders/authorize."""
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(401, {"error": "UNAUTHORIZED", "message": "Authentication required."})

        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "Invalid JSON body."})

        contract_id = data.get("contract_id")
        paypal_order_id = data.get("paypal_order_id")

        if not contract_id or not paypal_order_id:
            return self._json_response(
                400,
                {"error": "BAD_REQUEST", "message": "contract_id and paypal_order_id are required."}
            )

        try:
            res = self.service.confirm_and_store_authorization(
                contract_id=contract_id,
                paypal_order_id=paypal_order_id,
                actor=actor
            )
            return self._json_response(200, res)
        except ValueError as e:
            return self._json_response(404, {"error": "NOT_FOUND", "message": str(e)})
        except ForbiddenActionError as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except StateValidationError as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _json_response(self, status_code: int, data: Dict[str, Any]) -> Tuple[int, Dict[str, str], bytes]:
        body_bytes = json.dumps(data, indent=2).encode("utf-8")
        resp_headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body_bytes)),
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Actor-Id",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
        }
        return status_code, resp_headers, body_bytes


def create_payments_app(service: Optional[EscrowPaymentService] = None):
    """
    Creates a standard WSGI application for the Payments API.
    Compatible with gunicorn, uwsgi, or Python wsgiref.
    """
    handler = PaymentsAPIHandler(service=service)

    def application(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")

        # Options preflight
        if method == "OPTIONS":
            status_str = "204 No Content"
            headers = [
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Actor-Id"),
                ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ]
            start_response(status_str, headers)
            return [b""]

        # Parse headers
        headers: Dict[str, str] = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                headers[header_name] = value
            elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                headers[key.replace("_", "-").title()] = value

        # Read body
        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0) or 0)
        except ValueError:
            content_length = 0
        body = environ["wsgi.input"].read(content_length) if content_length > 0 else None

        status_code, resp_headers, resp_bytes = handler.dispatch(
            method=method,
            path=path,
            headers=headers,
            body=body
        )

        status_map = {
            200: "200 OK",
            201: "201 Created",
            204: "204 No Content",
            400: "400 Bad Request",
            401: "401 Unauthorized",
            403: "403 Forbidden",
            404: "404 Not Found",
            405: "405 Method Not Allowed",
            500: "500 Internal Server Error"
        }
        status_line = status_map.get(status_code, f"{status_code} Status")
        start_response(status_line, list(resp_headers.items()))
        return [resp_bytes]

    return application

if __name__ == "__main__":
    app = create_payments_app()
    port = 8000
    print(f"Starting PactPal Payments API on http://localhost:{port} ...")
    with make_server("0.0.0.0", port, app) as httpd:
        httpd.serve_forever()

