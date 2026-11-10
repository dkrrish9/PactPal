import { NextResponse } from "next/server";
import { mockApi } from "@/lib/mockApi";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const contract = mockApi.getContract(id);
  
  if (!contract) {
    return NextResponse.json(
      { error: "NOT_FOUND", message: `Contract with ID '${id}' not found` },
      { status: 404 }
    );
  }

  return NextResponse.json(contract);
}

