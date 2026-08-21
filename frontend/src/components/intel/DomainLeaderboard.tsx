import { decimal, num } from "@/lib/format";
import type { DomainStat } from "@/types/api";

export function DomainLeaderboard({ domains }: { domains: DomainStat[] }) {
  if (!domains.length) {
    return <p className="text-muted-foreground text-sm">No domain data available.</p>;
  }

  return (
    <table className="w-full border-collapse text-sm">
      <thead>
        <tr className="text-muted-foreground label-eyebrow border-b">
          <th className="py-3 text-left font-medium">Rank</th>
          <th className="py-3 text-left font-medium">Domain</th>
          <th className="py-3 text-right font-medium">Avg peak points</th>
          <th className="py-3 text-right font-medium">Stories</th>
        </tr>
      </thead>
      <tbody>
        {domains.map((entry, index) => {
          const avg = entry.avg_peak_points ?? entry.avg_points ?? null;
          const count = entry.story_count ?? entry.count ?? null;
          return (
            <tr
              key={`${entry.domain}-${index}`}
              className="hover:bg-secondary/60 border-b transition-colors"
            >
              <td className="numeric text-muted-foreground py-3">
                {String(index + 1).padStart(2, "0")}
              </td>
              <td className="py-3">{entry.domain ?? "—"}</td>
              <td className="numeric py-3 text-right">{avg === null ? "—" : decimal(avg, 0)}</td>
              <td className="numeric text-muted-foreground py-3 text-right">
                {count === null ? "—" : num(count)}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
