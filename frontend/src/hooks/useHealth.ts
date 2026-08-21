import { useQuery } from "@tanstack/react-query";
import { getHealth } from "@/api/core";
import type { HealthResponse } from "@/types/api";

export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: ({ signal }) => getHealth(signal),
    refetchInterval: 60_000,
    retry: 0,
  });
}
