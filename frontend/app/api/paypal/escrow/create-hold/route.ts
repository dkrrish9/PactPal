import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}));
    const contractId = body?.contract_id;
    const rawAmount = body?.amount ?? 1500;
    const amountVal = (typeof rawAmount === "number" ? rawAmount : parseFloat(rawAmount) || 1500).toFixed(2);
    const currency = body?.currency || "USD";
    const title = body?.title || "Digital Milestone Agreement";

    if (!contractId) {
      return NextResponse.json(
        { error: "MISSING_CONTRACT_ID", message: "contract_id is required." },
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

    // 2. Resolve origin for redirect URLs
    const clientOrigin = typeof body?.origin === "string" ? body.origin.trim() : "";
    const headerOrigin = request.headers.get("origin")?.trim();
    const forwardedHost = request.headers.get("x-forwarded-host")?.trim();
    const forwardedProto = request.headers.get("x-forwarded-proto")?.trim() || "https";
    const referer = request.headers.get("referer")?.trim();
    const envUrl = (process.env.NEXT_PUBLIC_APP_URL || process.env.APP_URL || process.env.RENDER_EXTERNAL_URL)?.trim();

    let origin = "";
    if (clientOrigin && (clientOrigin.startsWith("http://") || clientOrigin.startsWith("https://"))) {
      origin = clientOrigin.replace(/\/$/, "");
    } else if (headerOrigin && (headerOrigin.startsWith("http://") || headerOrigin.startsWith("https://"))) {
      origin = headerOrigin.replace(/\/$/, "");
    } else if (forwardedHost) {
      origin = `${forwardedProto}://${forwardedHost}`.replace(/\/$/, "");
    } else if (referer) {
      try {
        origin = new URL(referer).origin.replace(/\/$/, "");
      } catch {
        // ignore
      }
    } else if (envUrl && (envUrl.startsWith("http://") || envUrl.startsWith("https://"))) {
      origin = envUrl.replace(/\/$/, "");
    }

    if (!origin) {
      try {
        const urlObj = new URL(request.url);
        origin = `${urlObj.protocol}//${urlObj.host}`.replace(/\/$/, "");
      } catch {
        origin = "http://localhost:3000";
      }
    }

    // Safeguard: Port 10000 is Render's internal container port and cannot be reached from outside.
    // If origin contains :10000 or points to localhost when running in production/Render, resolve to live domain.
    if (origin.includes(":10000") || (origin.includes("localhost") && (process.env.RENDER || process.env.NODE_ENV === "production"))) {
      if (process.env.RENDER_EXTERNAL_URL) {
        origin = process.env.RENDER_EXTERNAL_URL.replace(/\/$/, "");
      } else if (forwardedHost && !forwardedHost.includes(":10000") && !forwardedHost.includes("localhost")) {
        origin = `${forwardedProto}://${forwardedHost}`.replace(/\/$/, "");
      } else {
        origin = "https://pactpal-frontend-c0mh.onrender.com";
      }
    }

    const returnUrl = `${origin}/contracts/${contractId}/fund?paypal_action=approved`;
    const cancelUrl = `${origin}/contracts/${contractId}/fund?paypal_action=cancelled`;

    // 3. Create PayPal order with AUTHORIZE intent
    // Payee is set to merchant business account so buyer account can authorize without collision
    const sellerEmail = process.env.PAYPAL_SANDBOX_SELLER_EMAIL || "sb-1pu8h53656646@business.example.com";

    const orderPayload = {
      intent: "AUTHORIZE",
      purchase_units: [
        {
          reference_id: String(contractId),
          description: `PactPal Escrow: ${title.slice(0, 80)}`,
          amount: {
            currency_code: currency,
            value: amountVal,
          },
          payee: {
            email_address: sellerEmail,
          },
        },
      ],
      application_context: {
        brand_name: "PactPal Escrow",
        landing_page: "LOGIN",
        user_action: "CONTINUE",
        return_url: returnUrl,
        cancel_url: cancelUrl,
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
        { error: "PAYPAL_ORDER_CREATION_FAILED", message: "Failed to initialize PayPal escrow hold", details: err },
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
      contract_id: contractId,
      order_id: orderData.id,
      approve_url: approveLink.href,
      intent: "AUTHORIZE",
      amount: parseFloat(amountVal),
      currency,
      status: orderData.status,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: "INTERNAL_ERROR", message }, { status: 500 });
  }
}
