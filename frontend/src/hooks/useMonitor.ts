import { useQuery } from "@tanstack/react-query";
import { getMonitor, getMonitorHistory } from "@/api/monitor";
import type { MonitorHistory, MonitorHistoryPoint, MonitorSnapshot } from "@/types/api";

export const MONITOR_REFETCH_MS = 15_000;

export function useMonitor(storyId: string | null, options: { live?: boolean } = {}) {
  const live = options.live ?? true;

  return useQuery<MonitorSnapshot>({
    queryKey: ["monitor", storyId],
    queryFn: ({ signal }) => getMonitor(storyId as string, signal),
    enabled: Boolean(storyId),
    refetchInterval: live && storyId ? MONITOR_REFETCH_MS : false,
    refetchOnWindowFocus: live,
    retry: 1,
  });
}

/** Normalizes the history payload (array or wrapped object) into a list. */
export function useMonitorHistory(storyId: string | null, options: { live?: boolean } = {}) {
  const live = options.live ?? true;

  return useQuery<MonitorHistoryPoint[]>({
    queryKey: ["monitor", storyId, "history"],
    queryFn: async ({ signal }) => {
      const data = await getMonitorHistory(storyId as string, signal);
      if (Array.isArray(data)) return data;
      const wrapped = data as MonitorHistory;
      return wrapped?.history ?? wrapped?.entries ?? [];
    },
    enabled: Boolean(storyId),
    refetchInterval: live && storyId ? MONITOR_REFETCH_MS : false,
    retry: 1,
  });
}
