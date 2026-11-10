import { NextResponse } from "next/server";
import { mockApi } from "@/lib/mockApi";

export async function GET() {
  const contracts = mockApi.getContracts();
  return NextResponse.json({
    data: contracts,
    total: contracts.length,
  });
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    if (!body.title || !body.buyer_email || !body.seller_email || !body.total_amount) {
      return NextResponse.json(
        { error: "VALIDATION_FAILED", message: "Missing required fields" },
        { status: 400 }
      );
    }

    const created = mockApi.createContract(body);
    return NextResponse.json(created, { status: 201 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal Server Error";
    return NextResponse.json({ error: "INTERNAL_ERROR", message }, { status: 500 });
  }
}
