"use client";

import { useEffect } from "react";

function isExtensionMetaMaskError(payload: unknown): boolean {
  const text = String(payload ?? "");
  return (
    text.toLowerCase().includes("metamask") ||
    text.includes("chrome-extension://")
  );
}

export default function DevExtensionErrorGuard() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "development") {
      return;
    }

    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      const stack =
        reason && typeof reason === "object" && "stack" in reason
          ? (reason as { stack?: string }).stack
          : "";

      if (isExtensionMetaMaskError(reason) || isExtensionMetaMaskError(stack)) {
        event.preventDefault();
        console.warn("Ignored extension error:", reason);
      }
    };

    const onWindowError = (event: ErrorEvent) => {
      const message = event.message;
      const filename = event.filename;
      const stack = event.error?.stack ?? "";

      if (
        isExtensionMetaMaskError(message) ||
        isExtensionMetaMaskError(filename) ||
        isExtensionMetaMaskError(stack)
      ) {
        event.preventDefault();
        console.warn("Ignored extension runtime error:", message);
      }
    };

    window.addEventListener("unhandledrejection", onUnhandledRejection);
    window.addEventListener("error", onWindowError);

    return () => {
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
      window.removeEventListener("error", onWindowError);
    };
  }, []);

  return null;
}
