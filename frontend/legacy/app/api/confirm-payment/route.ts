import { Polar } from "@polar-sh/sdk";
import { NextRequest, NextResponse } from "next/server";

const polar = new Polar({
  accessToken: process.env.POLAR_ACCESS_TOKEN,
  server: (process.env.POLAR_SERVER as "sandbox" | "production") ?? "sandbox",
});

// Demo buyer ID — replace with real auth user ID once auth is wired in
const DEMO_BUYER_ID = "00000000-0000-0000-0000-000000000001";

export async function GET(req: NextRequest) {
  const checkoutId = req.nextUrl.searchParams.get("checkout_id");
  if (!checkoutId) {
    return NextResponse.json({ error: "Missing checkout_id" }, { status: 400 });
  }

  try {
    // Fetch the checkout from Polar to verify payment status and get metadata
    const checkout = await polar.checkouts.get({ id: checkoutId });

    if (checkout.status !== "confirmed" && checkout.status !== "succeeded") {
      return NextResponse.json(
        { error: `Payment not confirmed. Current status: ${checkout.status}` },
        { status: 402 },
      );
    }

    const meta = (checkout.metadata ?? {}) as Record<string, string>;
    const creditId = meta.credit_id;
    const quantityTco2e = parseFloat(meta.quantity_tco2e ?? "0");
    const totalPrice = parseFloat(meta.total_price_usd ?? "0");
    const creditName = meta.credit_name ?? "Carbon Credit";

    if (!creditId) {
      return NextResponse.json(
        { error: "credit_id missing from checkout metadata" },
        { status: 400 },
      );
    }

    // Server-side route: use BACKEND_URL (no NEXT_PUBLIC needed)
    const apiUrl = process.env.BACKEND_URL ?? "https://terrafoma-api-production-58dc.up.railway.app";

    // Create the transaction record in the TerraFoma backend
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
      // If credit is already sold (idempotency — e.g. page refresh or webhook race),
      // look up the existing transaction for this buyer+credit and return success.
      if (
        txRes.status === 400 &&
        String(err.detail).includes("not available")
      ) {
        const existingRes = await fetch(
          `${apiUrl}/api/transactions/buyer/${DEMO_BUYER_ID}`,
        ).catch(() => null);
        if (existingRes?.ok) {
          const existing: any[] = await existingRes.json().catch(() => []);
          const match = existing.find((t: any) => t.credit_id === creditId);
          if (match) {
            return NextResponse.json({
              transactionId: match.id,
              creditId,
              creditName,
              quantityTco2e,
              totalPrice,
            });
          }
        }
        return NextResponse.json(
          { error: "This credit has already been purchased." },
          { status: 409 },
        );
      }
      return NextResponse.json(
        { error: err.detail ?? "Transaction creation failed" },
        { status: 400 },
      );
    }

    const tx = await txRes.json();

    return NextResponse.json({
      transactionId: tx.id,
      creditId,
      creditName,
      quantityTco2e,
      totalPrice,
    });
  } catch (err: any) {
    console.error("[confirm-payment] Error:", err);
    return NextResponse.json(
      { error: err?.message ?? "Failed to confirm payment" },
      { status: 500 },
    );
  }
}
