import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}));
    const role = body?.role || "hirer";

    const clientId = process.env.PAYPAL_CLIENT_ID || "BAAS3nJ2f-EHbCyO2NIU7PWMMVkQopdd4I9CWteq4AqhtW11_K0ktLkPnoK0M_hs-H5iqwSxO-8Ba0oUb0";
    const clientSecret = process.env.PAYPAL_CLIENT_SECRET || "EPOWP2VNpRayjxW7M9raoG_z-zESVvK-bgg8UzhMcorCJi_F8KBTr0IPnYVO6RMpIGJEjw6GGi6fEDVn";
    const baseUrl = (process.env.PAYPAL_API_BASE_URL || "https://api-m.sandbox.paypal.com").replace(/\/$/, "");

    // 1. Get OAuth access token from PayPal Sandbox
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

    // Determine host origin for return URL
    const urlObj = new URL(request.url);
    const origin = `${urlObj.protocol}//${urlObj.host}`;

    // Prevent "merchant trying to pay themselves" conflict:
    // If user is a freelancer, the logging-in PayPal user is the seller persona.
    // Setting payee to buyer allows the seller account to authorize without collision.
    // If user is a hirer, payee is seller, allowing buyer account to authorize without collision.
    const sellerEmail = process.env.PAYPAL_SANDBOX_SELLER_EMAIL || "sb-1pu8h53656646@business.example.com";
    const buyerEmail = process.env.PAYPAL_SANDBOX_BUYER_EMAIL || "sb-zzudl53771742@personal.example.com";
    const payeeEmail = role === "freelancer" ? buyerEmail : sellerEmail;

    // 2. Create PayPal order with AUTHORIZE intent
    const orderPayload = {
      intent: "AUTHORIZE",
      purchase_units: [
        {
          reference_id: `PACTPAL_SIGNUP_${Date.now()}`,
          description: "PactPal Escrow Account Authorization",
          amount: {
            currency_code: "USD",
            value: "1.00",
          },
          payee: {
            email_address: payeeEmail,
          },
        },
      ],
      application_context: {
        brand_name: "PactPal Escrow",
        landing_page: "LOGIN",
        user_action: "CONTINUE",
        return_url: `${origin}/paypal-callback`,
        cancel_url: `${origin}/paypal-callback?cancel=true`,
      },
    };

    const orderRes = await fetch(`${baseUrl}/v2/checkout/orders`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(orderPayload),
    });

    if (!orderRes.ok) {
      const err = await orderRes.text();
      return NextResponse.json(
        { error: "PAYPAL_ORDER_CREATION_FAILED", message: "Failed to initialize PayPal authorization", details: err },
        { status: 502 }
      );
    }

    const orderData = await orderRes.json();
    const approveLink = orderData.links?.find((l: { rel: string; href: string }) => l.rel === "approve" || l.rel === "payer-action");

    if (!approveLink?.href) {
      return NextResponse.json(
        { error: "NO_APPROVE_URL", message: "PayPal did not return an approval URL" },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      order_id: orderData.id,
      approve_url: approveLink.href,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: "INTERNAL_ERROR", message }, { status: 500 });
  }
}
