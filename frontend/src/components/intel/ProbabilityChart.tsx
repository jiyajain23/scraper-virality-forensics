import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { timeLabel, toPercent } from "@/lib/format";
import type { MonitorHistoryPoint } from "@/types/api";

/**
 * Renders ONLY backend-supplied history from /monitor/{id}/history.
 * No synthetic or interpolated points are ever generated here.
 */
export function ProbabilityChart({ history }: { history: MonitorHistoryPoint[] }) {
  const series = history
    .map((point) => {
      const pct = toPercent(point.viral_probability ?? point.probability);
      const stamp = point.timestamp ?? point.observed_at ?? point.time ?? null;
      if (pct === null) return null;
      return { t: timeLabel(stamp), probability: Number(pct.toFixed(2)) };
    })
    .filter((v): v is { t: string; probability: number } => v !== null);

  if (series.length < 2) {
    return (
      <p className="text-muted-foreground text-sm">
        The backend has recorded {series.length} prediction{series.length === 1 ? "" : "s"} so far —
        the trajectory chart appears once at least two snapshots exist.
      </p>
    );
  }

  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={series} margin={{ top: 10, right: 8, bottom: 0, left: -18 }}>
          <defs>
            <linearGradient id="probFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border)" vertical={false} />
          <XAxis
            dataKey="t"
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            axisLine={false}
            tickLine={false}
            minTickGap={24}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            axisLine={false}
            tickLine={false}
            width={44}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value) => [`${value}%`, "P(high-performance)"]}
          />
          <Area
            type="monotone"
            dataKey="probability"
            stroke="var(--foreground)"
            strokeWidth={1.5}
            fill="url(#probFill)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
