import { motion } from "motion/react";
import { num } from "@/lib/format";
import type { TrendingTopic } from "@/types/api";

export function TrendingTopics({ topics }: { topics: TrendingTopic[] }) {
  if (!topics.length) {
    return <p className="text-muted-foreground text-sm">No trend data available.</p>;
  }

  const max = Math.max(
    ...topics.map((t) =>
      typeof t.score === "number" ? t.score : ((t.total_points ?? t.points ?? 1) as number),
    ),
    1,
  );

  return (
    <ol className="divide-border divide-y">
      {topics.map((topic, index) => {
        const label = topic.topic ?? topic.phrase ?? topic.keyword ?? "—";
        const stories = topic.story_count ?? topic.count ?? null;
        const points = topic.total_points ?? topic.points ?? null;
        const weight =
          typeof topic.score === "number" ? topic.score : ((points ?? 0) as number);

        return (
          <li key={`${label}-${index}`} className="group relative py-5">
            <motion.span
              className="bg-secondary absolute inset-y-0 left-0 -z-10"
              initial={{ width: 0 }}
              whileInView={{ width: `${Math.max(6, (weight / max) * 100)}%` }}
              viewport={{ once: true }}
              transition={{ duration: 1, ease: [0.16, 1, 0.3, 1], delay: index * 0.04 }}
            />
            <div className="grid grid-cols-12 items-baseline gap-4 px-2">
              <span className="numeric text-muted-foreground col-span-2 text-xs md:col-span-1">
                #{index + 1}
              </span>
              <span className="display-lg col-span-10 md:col-span-7">{label}</span>
              <span className="numeric col-span-6 text-sm md:col-span-2 md:text-right">
                {stories === null ? "" : `${num(stories)} stories`}
              </span>
              <span className="numeric col-span-6 text-sm md:col-span-2 md:text-right">
                {points === null ? "" : `${num(points)} points`}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
