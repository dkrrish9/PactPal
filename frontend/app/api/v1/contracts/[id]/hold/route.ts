import { NextResponse } from "next/server";
import { mockApi } from "@/lib/mockApi";

const BACKEND_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1500);
    const res = await fetch(`${BACKEND_BASE}/api/v1/contracts/${id}/hold`, {
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Actor-Id": "usr_buyer_01",
      },
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const holdInfo = await res.json();
      return NextResponse.json(holdInfo);
    }
  } catch {
    // Fall back to local mock state
  }

  const holdInfo = mockApi.getHoldInfo(id);
  if (!holdInfo) {
    return NextResponse.json(
      { error: "NO_ACTIVE_HOLD", message: `No active PayPal hold found for contract '${id}'` },
      { status: 404 }
    );
  }

  return NextResponse.json(holdInfo);
}
