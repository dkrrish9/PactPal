import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const { token } = await request.json();
    if (!token) {
      return NextResponse.json(
        { error: "MISSING_TOKEN", message: "PayPal order token is required" },
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

    // 2. Fetch the real PayPal order details
    const orderRes = await fetch(`${baseUrl}/v2/checkout/orders/${token}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${access_token}`,
        "Content-Type": "application/json",
      },
    });

    if (!orderRes.ok) {
      const err = await orderRes.text();
      return NextResponse.json(
        { error: "ORDER_LOOKUP_FAILED", message: "Failed to look up PayPal order", details: err },
        { status: 502 }
      );
    }

    const orderData = await orderRes.json();
    const payer = orderData.payer || {};
    const payerName = payer.name
      ? `${payer.name.given_name || ""} ${payer.name.surname || ""}`.trim()
      : null;

    if (orderData.status !== "APPROVED" && !payer.email_address) {
      return NextResponse.json({
        success: false,
        status: orderData.status,
        message: "Authorization was not completed on PayPal. Make sure to click Continue/Agree on PayPal.",
      });
    }

    return NextResponse.json({
      success: true,
      order_id: orderData.id,
      status: orderData.status,
      email: payer.email_address || null,
      payer_id: payer.payer_id || null,
      name: payerName,
      raw_payer: payer,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: "INTERNAL_ERROR", message }, { status: 500 });
  }
}
