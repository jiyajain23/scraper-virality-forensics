import { useMutation } from "@tanstack/react-query";
import { scoreTitle } from "@/api/title";
import type { TitleAnalysis } from "@/types/api";

export function useTitleAnalysis() {
  return useMutation<TitleAnalysis, Error, string>({
    mutationKey: ["score_title"],
    mutationFn: (title: string) => scoreTitle(title),
  });
}
