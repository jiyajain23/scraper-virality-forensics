import { request } from "./client";
import type { MonitorHistory, MonitorSnapshot } from "@/types/api";

export function getMonitor(storyId: string, signal?: AbortSignal) {
  return request<MonitorSnapshot>(`/api/v1/monitor/${encodeURIComponent(storyId)}`, { signal });
}

export function getMonitorHistory(storyId: string, signal?: AbortSignal) {
  return request<MonitorHistory | MonitorHistory["history"]>(
    `/api/v1/monitor/${encodeURIComponent(storyId)}/history`,
    { signal },
  );
}

export function clearMonitorHistory(storyId: string) {
  return request<unknown>(`/api/v1/monitor/${encodeURIComponent(storyId)}/history`, {
    method: "DELETE",
  });
}
