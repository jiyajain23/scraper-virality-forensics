import { useQuery } from "@tanstack/react-query";
import { getBestTime, getSimilar, getTrending, getTrendingDomains } from "@/api/feeds";
import type {
  BestTimeResponse,
  DomainStat,
  SimilarStory,
  TrendingTopic,
} from "@/types/api";

const FIVE_MIN = 5 * 60 * 1000;

export function useTrending(params: { hours?: number; top_n?: number } = {}) {
  return useQuery<TrendingTopic[]>({
    queryKey: ["trending", params.hours ?? 5, params.top_n ?? 10],
    queryFn: async ({ signal }) => {
      const data = await getTrending(params, signal);
      if (Array.isArray(data)) return data as TrendingTopic[];
      return data?.topics ?? data?.trending ?? [];
    },
    staleTime: FIVE_MIN,
    retry: 1,
  });
}

export function useTrendingDomains(params: { top_n?: number } = {}) {
  return useQuery<DomainStat[]>({
    queryKey: ["trending", "domains", params.top_n ?? 15],
    queryFn: async ({ signal }) => {
      const data = await getTrendingDomains(params, signal);
      if (Array.isArray(data)) return data as DomainStat[];
      return data?.domains ?? [];
    },
    staleTime: FIVE_MIN,
    retry: 1,
  });
}

export function useBestTime() {
  return useQuery<BestTimeResponse>({
    queryKey: ["trending", "best_time"],
    queryFn: ({ signal }) => getBestTime(signal),
    staleTime: FIVE_MIN,
    retry: 1,
  });
}

export function useSimilarStories(topic: string, hours = 48) {
  const cleaned = topic.trim();

  return useQuery<SimilarStory[]>({
    queryKey: ["similar", cleaned, hours],
    queryFn: async ({ signal }) => {
      const data = await getSimilar({ topic: cleaned, hours }, signal);
      if (Array.isArray(data)) return data as SimilarStory[];
      return data?.stories ?? data?.results ?? [];
    },
    enabled: cleaned.length > 1,
    staleTime: FIVE_MIN,
    retry: 1,
  });
}
