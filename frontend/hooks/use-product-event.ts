"use client";

import { useCallback } from "react";

type ProductEventPayload = {
  event_id: string;
  user_id: string;
  role: string;
  screen: string;
  action: string;
  target_type?: string;
  target_id?: string;
  execution_id?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export function useProductEvent() {
  return useCallback(async (payload: ProductEventPayload) => {
    try {
      await fetch(`${API_BASE}/api/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch {
      // Keep UI responsive even when analytics endpoint is unavailable.
    }
  }, []);
}
