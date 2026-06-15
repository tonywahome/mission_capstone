import { Polar } from "@polar-sh/sdk";
import { NextRequest, NextResponse } from "next/server";

const polar = new Polar({
  accessToken: process.env.POLAR_ACCESS_TOKEN,
  server: (process.env.POLAR_SERVER as "sandbox" | "production") ?? "sandbox",
});

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { creditId, creditName, quantity, totalPrice } = body;

    // Convert the actual credit price to cents for Polar.
    // The Polar product must be set to "Custom amount" pricing in the dashboard —
    // otherwise Polar ignores this value and uses the product's fixed price.
    const amountInCents = Math.round(Number(totalPrice) * 100);

    const checkout = await polar.checkouts.create({
      products: [
        process.env.POLAR_PRODUCT_ID ?? "620b261a-f47b-4926-87bb-22664d688410",
      ],
      amount: amountInCents,
      successUrl: process.env.POLAR_SUCCESS_URL,
      metadata: {
        credit_id: creditId,
        credit_name: creditName ?? "",
        quantity_tco2e: String(quantity ?? ""),
        total_price_usd: String(totalPrice ?? ""),
      },
    });

    return NextResponse.json({ url: checkout.url });
  } catch (err: any) {
    console.error("Polar checkout error:", err);
    return NextResponse.json(
      { error: err?.message ?? "Failed to create checkout" },
      { status: 500 },
    );
  }
}
