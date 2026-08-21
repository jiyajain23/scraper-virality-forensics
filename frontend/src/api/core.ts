import { request } from "./client";
import type { HealthResponse } from "@/types/api";

export function getHealth(signal?: AbortSignal) {
  return request<HealthResponse>("/health", { signal });
}

/** Triggers real backend collection work — never wire this to a page refresh. */
export function triggerCollect() {
  return request<{ status?: string; [key: string]: unknown }>("/api/v1/collect", {
    method: "POST",
  });
}

export function predictStory(storyId: string) {
  return request<Record<string, unknown>>(`/api/v1/predict/${encodeURIComponent(storyId)}`, {
    method: "POST",
  });
}
