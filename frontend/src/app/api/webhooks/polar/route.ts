import { NextRequest, NextResponse } from "next/server";
import {
  validateEvent,
  WebhookVerificationError,
} from "@polar-sh/sdk/webhooks";

const DEMO_BUYER_ID = "00000000-0000-0000-0000-000000000001";

export async function POST(req: NextRequest) {
  const secret = process.env.POLAR_WEBHOOK_SECRET;
  if (!secret) {
    console.warn(
      "[webhook/polar] POLAR_WEBHOOK_SECRET not set — skipping verification",
    );
  }

  const rawBody = await req.text();

  // Verify the webhook signature when a secret is configured
  if (secret) {
    try {
      validateEvent(rawBody, Object.fromEntries(req.headers.entries()), secret);
    } catch (err) {
      if (err instanceof WebhookVerificationError) {
        console.error(
          "[webhook/polar] Signature verification failed:",
          err.message,
        );
        return NextResponse.json(
          { error: "Invalid signature" },
          { status: 403 },
        );
      }
      throw err;
    }
  }

  let event: { type: string; data: any };
  try {
    event = JSON.parse(rawBody);
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  // Only handle order.created — this fires when a checkout payment succeeds
  if (event.type !== "order.created") {
    return NextResponse.json({ received: true, skipped: event.type });
  }

  const meta = (event.data?.checkout?.metadata ?? {}) as Record<string, string>;
  const creditId = meta.credit_id;
  const quantityTco2e = parseFloat(meta.quantity_tco2e ?? "0");
  const totalPrice = parseFloat(meta.total_price_usd ?? "0");

  if (!creditId) {
    console.warn("[webhook/polar] order.created missing credit_id in metadata");
    return NextResponse.json({
      received: true,
      warning: "No credit_id in metadata",
    });
  }

  // Server-side route: use BACKEND_URL (no NEXT_PUBLIC needed)
  const apiUrl = process.env.BACKEND_URL ?? "https://terrafoma-api-production-58dc.up.railway.app";

  try {
    const txRes = await fetch(`${apiUrl}/api/transactions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        credit_id: creditId,
        buyer_id: DEMO_BUYER_ID,
        quantity_tco2e: quantityTco2e,
        total_price: totalPrice,
        currency: "USD",
      }),
    });

    if (!txRes.ok) {
      const err = await txRes.json().catch(() => ({}));
      // 400 with "not available" means the success page already created the transaction
      if (
        txRes.status === 400 &&
        String(err.detail).includes("not available")
      ) {
        console.log(
          "[webhook/polar] Transaction already created by success page. Skipping.",
        );
        return NextResponse.json({ received: true, note: "already processed" });
      }
      console.error("[webhook/polar] Transaction creation failed:", err);
      return NextResponse.json({ error: err.detail }, { status: 500 });
    }

    const tx = await txRes.json();
    console.log(
      `[webhook/polar] Transaction created: ${tx.id} for credit ${creditId}`,
    );
    return NextResponse.json({ received: true, transactionId: tx.id });
  } catch (err: any) {
    console.error("[webhook/polar] Unexpected error:", err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
