import { NextResponse } from "next/server";
import { mockApi } from "@/lib/mockApi";
import { supabase, toUUID } from "@/lib/supabase";

const BACKEND_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const targetUuid = toUUID(id);

  try {
    const { data, error } = await supabase
      .from("contracts")
      .select(`
        id,
        title,
        description,
        status,
        total_amount,
        currency,
        deadline,
        paypal_order_id,
        paypal_auth_id,
        auth_expires_at,
        figma_url,
        repo_url,
        buyer_id,
        seller_id,
        created_at,
        updated_at,
        is_locked,
        buyer_confirmed_at,
        seller_confirmed_at,
        locked_at,
        features (*),
        buyer:users!contracts_buyer_id_fkey (id, name, email, paypal_email),
        seller:users!contracts_seller_id_fkey (id, name, email, paypal_email)
      `)
      .or(`id.eq.${id},id.eq.${targetUuid}`)
      .maybeSingle();

    if (!error && data) {
      return NextResponse.json(data);
    }
  } catch (supaErr) {
    console.warn("Supabase API route single GET error:", supaErr);
  }

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

  const contract = mockApi.getContract(id) || mockApi.getContract(targetUuid);
  if (!contract) {
    return NextResponse.json(
      { error: "NOT_FOUND", message: `Contract with ID '${id}' not found` },
      { status: 404 }
    );
  }

  return NextResponse.json(contract);
}
