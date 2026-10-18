import type { Order, OrderStatus, PaymentAttempt, PaymentStatus } from "@/lib/types";

type Tone = "green" | "amber" | "red" | "neutral";

export type OrderPaymentPresentation = {
  title: string;
  message: string;
  tone: Tone;
};

export type OrderPaymentState = {
  status: OrderStatus;
  payment_status: PaymentStatus;
  latest_payment_attempt: PaymentAttempt | null;
};

export function latestPaymentAttempt(order: Order): PaymentAttempt | null {
  return order.payment_attempts.at(-1) ?? null;
}

export function getOrderPaymentPresentation(order: Order): OrderPaymentPresentation {
  return getPaymentPresentation({
    status: order.status,
    payment_status: order.payment_status,
    latest_payment_attempt: latestPaymentAttempt(order)
  });
}

export function getPaymentPresentation(state: OrderPaymentState): OrderPaymentPresentation {
  const attempt = state.latest_payment_attempt;
  if (state.payment_status === "refunded") {
    return { title: "Refunded", message: "Payment for this order was refunded.", tone: "neutral" };
  }
  if (state.payment_status === "paid" || attempt?.status === "paid") {
    return { title: "Paid", message: "Payment is verified and this order is confirmed.", tone: "green" };
  }
  if (attempt?.status === "processing") {
    return { title: "Processing", message: "Stripe is still confirming this payment. Inventory remains reserved.", tone: "amber" };
  }
  if (attempt?.status === "initializing" || attempt?.status === "open") {
    return { title: "Payment pending", message: "Payment has not been verified yet. You can resume or cancel this reservation.", tone: "amber" };
  }
  if (attempt?.status === "expired") {
    return { title: "Payment expired", message: "The payment window expired and reserved inventory was released.", tone: "red" };
  }
  if (attempt?.status === "cancelled") {
    return { title: "Payment cancelled", message: "This pending payment was cancelled and reserved inventory was released.", tone: "red" };
  }
  if (attempt?.status === "failed" || state.payment_status === "failed") {
    return { title: "Payment failed", message: "Payment was not completed and reserved inventory was released.", tone: "red" };
  }
  if (state.status === "confirmed" && state.payment_status === "unpaid") {
    return { title: "Manual order · Unpaid", message: "This development order was confirmed without collecting payment.", tone: "neutral" };
  }
  return { title: "Payment status unavailable", message: "Refresh this order for the latest payment state.", tone: "neutral" };
}

const TONE_CLASSES: Record<Tone, string> = {
  green: "border-market-green/30 bg-market-mint text-ink-900",
  amber: "border-amber-300 bg-amber-50 text-amber-900",
  red: "border-market-red/30 bg-red-50 text-market-red",
  neutral: "border-ink-200 bg-ink-50 text-ink-700"
};

export function OrderPaymentStatus({ order, compact = false }: { order: Order; compact?: boolean }) {
  const presentation = getOrderPaymentPresentation(order);
  return <PaymentStatusPresentation presentation={presentation} compact={compact} />;
}

export function PaymentStatusPresentation({
  presentation,
  compact = false
}: {
  presentation: OrderPaymentPresentation;
  compact?: boolean;
}) {
  if (compact) {
    return <p className={`inline-flex border px-2 py-1 text-xs font-bold uppercase ${TONE_CLASSES[presentation.tone]}`}>{presentation.title}</p>;
  }
  return (
    <div className={`border px-4 py-3 ${TONE_CLASSES[presentation.tone]}`}>
      <p className="font-black">{presentation.title}</p>
      <p className="mt-1 text-sm font-medium">{presentation.message}</p>
    </div>
  );
}
