import { hourWindow, num, decimal } from "@/lib/format";
import type { PostingTime } from "@/types/api";

export function PostingWindow({ window: slot }: { window: PostingTime }) {
  const day = slot.day ?? slot.day_of_week ?? null;
  const windowLabel =
    slot.window ?? slot.window_utc ?? hourWindow(slot.hour ?? slot.hour_utc) ?? null;

  return (
    <div className="grid gap-6 md:grid-cols-12 md:items-end">
      <div className="md:col-span-5">
        <p className="display-xl">{day ?? "—"}</p>
      </div>
      <div className="md:col-span-4">
        <p className="numeric display-lg">{windowLabel ?? "—"}</p>
      </div>
      <div className="text-muted-foreground md:col-span-3 md:text-right">
        {typeof slot.avg_points === "number" ? (
          <p className="text-sm">Avg {decimal(slot.avg_points, 0)} points</p>
        ) : null}
        {typeof slot.story_count === "number" ? (
          <p className="text-sm">{num(slot.story_count)} stories observed</p>
        ) : null}
      </div>
    </div>
  );
}
