import { request } from "./client";
import type {
  BestTimeResponse,
  DomainsResponse,
  SimilarResponse,
  TrendingResponse,
} from "@/types/api";

export function getTrending(params: { hours?: number; top_n?: number } = {}, signal?: AbortSignal) {
  return request<TrendingResponse>("/api/v1/trending", {
    query: { hours: params.hours, top_n: params.top_n },
    signal,
  });
}

export function getTrendingDomains(params: { top_n?: number } = {}, signal?: AbortSignal) {
  return request<DomainsResponse>("/api/v1/trending/domains", {
    query: { top_n: params.top_n },
    signal,
  });
}

export function getBestTime(signal?: AbortSignal) {
  return request<BestTimeResponse>("/api/v1/trending/best_time", { signal });
}

export function getSimilar(params: { topic: string; hours?: number }, signal?: AbortSignal) {
  return request<SimilarResponse>("/api/v1/similar", {
    query: { topic: params.topic, hours: params.hours },
    signal,
  });
}
