import { NextResponse } from "next/server";
import { mockApi } from "@/lib/mockApi";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const holdInfo = mockApi.getHoldInfo(id);

  if (!holdInfo) {
    return NextResponse.json(
      { error: "NO_ACTIVE_HOLD", message: `No active PayPal hold found for contract '${id}'` },
      { status: 404 }
    );
  }

  return NextResponse.json(holdInfo);
}
