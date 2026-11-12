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
    const res = await fetch(`${BACKEND_BASE}/api/v1/contracts/${id}`, {
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const contract = await res.json();
      return NextResponse.json(contract);
    }
  } catch {
    // Fall back to local mock state
  }

  const contract = mockApi.getContract(id);
  if (!contract) {
    return NextResponse.json(
      { error: "NOT_FOUND", message: `Contract with ID '${id}' not found` },
      { status: 404 }
    );
  }

  return NextResponse.json(contract);
}
