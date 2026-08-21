import { motion } from "motion/react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { decimal, num, percentLabel, signedDelta } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { MonitorSnapshot } from "@/types/api";

function pick(...values: unknown[]): number | null {
  for (const value of values) {
    if (typeof value === "number" && !Number.isNaN(value)) return value;
  }
  return null;
}

export function TrajectoryBadge({ trajectory }: { trajectory: string | null | undefined }) {
  const value = (trajectory ?? "").toLowerCase();
  const Icon = value === "rising" ? ArrowUpRight : value === "falling" ? ArrowDownRight : Minus;
  return (
    <span
      className={cn(
        "label-eyebrow inline-flex items-center gap-2 rounded-full border px-3 py-1",
        value === "rising" && "border-rising/50 text-rising",
        value === "falling" && "border-falling/50 text-falling",
        value !== "rising" && value !== "falling" && "border-border text-muted-foreground",
      )}
    >
      <Icon className="size-3.5" />
      {trajectory ?? "unknown"}
    </span>
  );
}

export function MonitorMetrics({ snapshot }: { snapshot: MonitorSnapshot }) {
  const probability = pick(snapshot.viral_probability, snapshot.probability);
  const delta = pick(snapshot.probability_delta, snapshot.delta);
  const comments = pick(snapshot.num_comments, snapshot.comments);
  const rank = pick(snapshot.rank, snapshot.approx_rank);
  const deltaLabel = delta === null ? null : signedDelta(delta);

  const metrics: { label: string; value: string }[] = [
    { label: "Points", value: num(snapshot.points) },
    { label: "Comments", value: num(comments) },
    { label: "Rank", value: rank === null ? "—" : `#${num(rank)}` },
    {
      label: "Points velocity",
      value: snapshot.points_velocity === null ? "—" : decimal(snapshot.points_velocity, 2),
    },
    {
      label: "Comments velocity",
      value: snapshot.comments_velocity === null ? "—" : decimal(snapshot.comments_velocity, 2),
    },
    {
      label: "Engagement ratio",
      value: snapshot.engagement_ratio === null ? "—" : decimal(snapshot.engagement_ratio, 2),
    },
  ];

  return (
    <div className="space-y-12">
      <div className="grid gap-8 md:grid-cols-12 md:items-end">
        <div className="md:col-span-7">
          <p className="label-eyebrow text-muted-foreground">Story</p>
          <h2 className="display-xl mt-4">{snapshot.title ?? "Untitled story"}</h2>
          {snapshot.url ? (
            <a
              href={snapshot.url}
              target="_blank"
              rel="noreferrer noopener"
              className="text-muted-foreground mt-3 inline-block text-sm underline underline-offset-4"
            >
              Open source
            </a>
          ) : null}
        </div>

        <div className="md:col-span-5 md:text-right">
          <p className="label-eyebrow text-muted-foreground">
            Estimated probability of the high-performance class
          </p>
          <motion.p
            key={String(probability)}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="numeric-xl mt-4"
          >
            {percentLabel(probability)}
          </motion.p>
          <div className="mt-4 flex flex-wrap gap-3 md:justify-end">
            <TrajectoryBadge trajectory={snapshot.trajectory} />
            {deltaLabel ? (
              <span className="label-eyebrow text-muted-foreground border-border rounded-full border px-3 py-1">
                {deltaLabel} vs previous snapshot
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-px md:grid-cols-3 lg:grid-cols-6">
        {metrics.map((metric) => (
          <div key={metric.label} className="border-t pt-4">
            <dt className="label-eyebrow text-muted-foreground">{metric.label}</dt>
            <dd className="numeric mt-3 text-2xl">{metric.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
