import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}));
    const contractId = body?.contract_id;
    const orderId = body?.order_id;

    if (!contractId || !orderId) {
      return NextResponse.json(
        { error: "MISSING_FIELDS", message: "contract_id and order_id are required." },
        { status: 400 }
      );
    }

    const clientId = process.env.PAYPAL_CLIENT_ID || "BAAS3nJ2f-EHbCyO2NIU7PWMMVkQopdd4I9CWteq4AqhtW11_K0ktLkPnoK0M_hs-H5iqwSxO-8Ba0oUb0";
    const clientSecret = process.env.PAYPAL_CLIENT_SECRET || "EPOWP2VNpRayjxW7M9raoG_z-zESVvK-bgg8UzhMcorCJi_F8KBTr0IPnYVO6RMpIGJEjw6GGi6fEDVn";
    const baseUrl = (process.env.PAYPAL_API_BASE_URL || "https://api-m.sandbox.paypal.com").replace(/\/$/, "");

    // 1. Get OAuth access token
    const basicAuth = Buffer.from(`${clientId}:${clientSecret}`).toString("base64");
    const tokenRes = await fetch(`${baseUrl}/v1/oauth2/token`, {
      method: "POST",
      headers: {
        Authorization: `Basic ${basicAuth}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: "grant_type=client_credentials",
    });

    if (!tokenRes.ok) {
      const err = await tokenRes.text();
      return NextResponse.json(
        { error: "PAYPAL_AUTH_FAILED", message: "Failed to authenticate with PayPal", details: err },
        { status: 502 }
      );
    }

    const { access_token } = await tokenRes.json();

    // 2. Execute authorization on PayPal Rails
    const authRes = await fetch(`${baseUrl}/v2/checkout/orders/${orderId}/authorize`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });

    if (!authRes.ok) {
      const err = await authRes.text();
      return NextResponse.json(
        { error: "AUTHORIZATION_EXECUTION_FAILED", message: "PayPal failed to execute authorization hold", details: err },
        { status: 502 }
      );
    }

    const authData = await authRes.json();
    const purchaseUnits = authData.purchase_units || [];
    const authorizations = purchaseUnits[0]?.payments?.authorizations || [];
    const primaryAuth = authorizations[0] || {};
    const authId = primaryAuth.id || `AUTH_${Date.now()}`;
    const authStatus = primaryAuth.status || "CREATED";
    const expirationTime = primaryAuth.expiration_time || new Date(Date.now() + 29 * 86400000).toISOString();
    const heldAmount = primaryAuth.amount?.value;
    const currency = primaryAuth.amount?.currency_code || "USD";

    // 3. Forward to Python backend if reachable to sync state machine
    try {
      const backendUrl = (process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
      await fetch(`${backendUrl}/api/v1/contracts/${contractId}/fund`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Actor-Id": "usr_buyer_01" },
        body: JSON.stringify({
          paypal_order_id: orderId,
          paypal_auth_id: authId,
        }),
      }).catch(() => null);
    } catch {
      // ignore
    }

    return NextResponse.json({
      success: true,
      contract_id: contractId,
      paypal_order_id: orderId,
      paypal_auth_id: authId,
      status: "FUNDED",
      auth_status: authStatus,
      auth_expires_at: expirationTime,
      held_amount: heldAmount,
      currency,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: "INTERNAL_ERROR", message }, { status: 500 });
  }
}
