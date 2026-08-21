import { request } from "./client";
import type { TitleAnalysis } from "@/types/api";

export function scoreTitle(title: string, signal?: AbortSignal) {
  return request<TitleAnalysis>("/api/v1/score_title", {
    method: "POST",
    body: { title },
    signal,
  });
}

export function refreshCorpus() {
  return request<{ status?: string; [key: string]: unknown }>("/api/v1/refresh_corpus", {
    method: "POST",
  });
}
