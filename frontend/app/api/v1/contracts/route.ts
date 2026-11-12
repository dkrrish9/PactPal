import { NextResponse } from "next/server";
import { mockApi } from "@/lib/mockApi";

const BACKEND_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export async function GET() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1500);
    const res = await fetch(`${BACKEND_BASE}/api/v1/contracts`, {
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const liveData = await res.json();
      return NextResponse.json(liveData);
    }
  } catch {
    // Fall back to local mock state if backend is offline
  }

  const contracts = mockApi.getContracts();
  return NextResponse.json({
    data: contracts,
    total: contracts.length,
  });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    if (!body.title || !body.total_amount) {
      return NextResponse.json(
        { error: "VALIDATION_FAILED", message: "Missing required fields" },
        { status: 400 }
      );
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(`${BACKEND_BASE}/api/v1/contracts`, {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "X-Actor-Id": "usr_buyer_01",
        },
        body: JSON.stringify(body),
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const liveCreated = await res.json();
        return NextResponse.json(liveCreated, { status: 201 });
      }
    } catch {
      // Fallback
    }

    const created = mockApi.createContract({
      title: body.title,
      description: body.description || body.title,
      buyer_email: body.buyer_email || "alice@buyer.example.com",
      seller_email: body.seller_email || "bob@seller.example.com",
      total_amount: body.total_amount,
      deadline: body.deadline,
      figma_url: body.figma_url,
      repo_url: body.repo_url,
      features: body.features || [],
    });
    return NextResponse.json(created, { status: 201 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: "INTERNAL_ERROR", message }, { status: 500 });
  }
}
