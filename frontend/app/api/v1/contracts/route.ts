import { NextResponse } from "next/server";
import { mockApi } from "@/lib/mockApi";
import { supabase, toUUID } from "@/lib/supabase";

const BACKEND_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export async function GET() {
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
      .order("created_at", { ascending: false });

    if (!error && data && data.length > 0) {
      return NextResponse.json({
        data: data,
        total: data.length,
      });
    }
  } catch (supaErr) {
    console.warn("Supabase API route GET error:", supaErr);
  }

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

    const contractId = body.id || (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : toUUID(`pct_${Date.now()}`));
    const buyerUUID = toUUID(body.buyer_id || body.buyer_email || "usr_buyer_01");
    let sellerUUID: string | null = null;
    if (body.seller_id || body.seller_email) {
      sellerUUID = toUUID(body.seller_id || body.seller_email);
    }

    try {
      await supabase.from("contracts").insert({
        id: contractId,
        buyer_id: buyerUUID,
        seller_id: sellerUUID,
        title: body.title,
        description: body.description || body.title,
        status: "DRAFT",
        total_amount: body.total_amount,
        currency: body.currency || "USD",
        deadline: body.deadline || new Date(Date.now() + 14 * 86400000).toISOString(),
        figma_url: body.figma_url || null,
        repo_url: body.repo_url || null,
        is_locked: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });

      if (body.features && body.features.length > 0) {
        const featureRows = body.features.map((f: any, i: number) => ({
          id: toUUID(`${contractId}_feat_${i + 1}`),
          contract_id: contractId,
          title: f.title,
          acceptance_test: f.acceptance_test,
          price_weight: Number(f.price_weight) || 0,
          allocated_amount: Number(f.allocated_amount) || ((body.total_amount * Number(f.price_weight)) / 100),
          status: "PENDING",
          sort_order: i + 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }));
        await supabase.from("features").insert(featureRows);
      }
    } catch (supaErr) {
      console.warn("Supabase API route POST error:", supaErr);
    }

    const created = mockApi.createContract({
      id: contractId,
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
