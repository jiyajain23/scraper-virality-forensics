import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PageIntro } from "@/components/site/PageIntro";
import { EmptyState, ErrorState, LoadingState } from "@/components/site/States";
import { MonitorMetrics } from "@/components/intel/MonitorMetrics";
import { ProbabilityChart } from "@/components/intel/ProbabilityChart";
import { MONITOR_REFETCH_MS, useMonitor, useMonitorHistory } from "@/hooks/useMonitor";
import { clearMonitorHistory } from "@/api/monitor";
import { dateTimeLabel, num, percentLabel } from "@/lib/format";
import { CurtainReveal, Reveal } from "@/components/motion/Reveal";
import { ScrollDrift, ScrollLift } from "@/components/motion/ScrollScene";

export const Route = createFileRoute("/monitor")({
  head: () => ({
    meta: [
      { title: "Live Monitor — track a Hacker News post's momentum" },
      {
        name: "description",
        content:
          "Poll a live Hacker News story for points, comments, rank, velocity and the model's probability trajectory, straight from the monitoring API.",
      },
      { property: "og:title", content: "Live Monitor — track a post's momentum" },
      {
        property: "og:description",
        content:
          "Points, comments, rank, velocity and probability trajectory for a live Hacker News story.",
      },
    ],
  }),
  component: MonitorPage,
});

function MonitorPage() {
  const [input, setInput] = useState("");
  const [storyId, setStoryId] = useState<string | null>(null);
  const [live, setLive] = useState(true);
  const [validationError, setValidationError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const snapshot = useMonitor(storyId, { live });
  const history = useMonitorHistory(storyId, { live });

  const clear = useMutation({
    mutationFn: () => clearMonitorHistory(storyId as string),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["monitor", storyId] }),
  });

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const cleaned = input.trim();
    if (!/^\d+$/.test(cleaned)) {
      setValidationError("A Hacker News story ID is numeric, e.g. 47283921.");
      return;
    }
    setValidationError(null);
    setStoryId(cleaned);
  };

  const points = history.data ?? [];

  return (
    <div className="pb-32">
      <PageIntro
        eyebrow="Workflow 02 — after you post"
        title="Watch momentum"
        accent="as it happens"
        description={`The service pulls the live story from Hacker News, compares it with its previous cached snapshot, derives velocity features and re-runs inference. This page refetches every ${MONITOR_REFETCH_MS / 1000} seconds.`}
      />

      <section className="mx-auto max-w-[1500px] px-5 md:px-8">
        <Reveal>
        <form onSubmit={submit} className="rule-top pt-8">
          <label htmlFor="story" className="label-eyebrow text-muted-foreground">
            Story ID
          </label>
          <div className="mt-4 flex flex-col gap-4 md:flex-row md:items-center">
            <input
              id="story"
              inputMode="numeric"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="e.g. 47283921"
              className="display-lg numeric placeholder:text-muted-foreground/50 w-full border-b bg-transparent pb-3 outline-none focus:border-foreground"
            />
            <button
              type="submit"
              className="bg-ink text-ink-foreground shrink-0 rounded-full px-6 py-3 text-sm font-medium transition-transform duration-300 hover:scale-[1.03]"
            >
              Monitor story
            </button>
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs">
            <span className="text-destructive">{validationError ?? ""}</span>
            <div className="flex items-center gap-4">
              {storyId ? (
                <button
                  type="button"
                  onClick={() => setLive((v) => !v)}
                  className="label-eyebrow border-border flex items-center gap-2 rounded-full border px-3 py-1"
                >
                  <span
                    className={
                      live
                        ? "bg-rising animate-pulse-dot size-1.5 rounded-full"
                        : "bg-muted-foreground size-1.5 rounded-full"
                    }
                  />
                  {live ? "Live" : "Paused"}
                </button>
              ) : null}
              {storyId ? (
                <button
                  type="button"
                  onClick={() => clear.mutate()}
                  disabled={clear.isPending}
                  className="label-eyebrow text-muted-foreground underline underline-offset-4 disabled:opacity-50"
                >
                  {clear.isPending ? "Clearing…" : "Clear stored history"}
                </button>
              ) : null}
            </div>
          </div>
        </form>
        </Reveal>
      </section>

      <section className="mx-auto mt-16 max-w-[1500px] px-5 md:px-8">
        {!storyId ? (
          <EmptyState
            title="No story selected"
            hint="Enter the numeric ID of a story you've already submitted to Hacker News."
          />
        ) : snapshot.isPending ? (
          <LoadingState label="Fetching live snapshot" />
        ) : snapshot.isError ? (
          <ErrorState error={snapshot.error} onRetry={() => snapshot.refetch()} />
        ) : snapshot.data ? (
          <ScrollLift>
            <MonitorMetrics snapshot={snapshot.data} />
          </ScrollLift>
        ) : null}
      </section>

      {storyId ? (
        <section className="surface-ink relative mt-24 overflow-hidden">
          <div className="mx-auto max-w-[1500px] px-5 py-20 md:px-8">
            <CurtainReveal>
              <div className="flex flex-wrap items-baseline justify-between gap-4">
                <h2 className="display-xl">
                  Probability <span className="serif-accent">trajectory</span>
                </h2>
                <p className="label-eyebrow text-ink-muted">
                  {points.length} recorded snapshot{points.length === 1 ? "" : "s"}
                </p>
              </div>
            </CurtainReveal>

            <div className="mt-10">
              {history.isPending ? (
                <p className="text-ink-muted text-sm">Loading prediction history…</p>
              ) : history.isError ? (
                <ErrorState error={history.error} onRetry={() => history.refetch()} />
              ) : points.length === 0 ? (
                <p className="text-ink-muted text-sm">
                  No monitoring history yet. The backend records a point each time this story is
                  observed.
                </p>
              ) : (
                <ScrollLift className="bg-background text-foreground rounded-lg p-6">
                  <ProbabilityChart history={points} />
                </ScrollLift>
              )}
            </div>

            {points.length ? (
              <ScrollLift className="border-ink-border mt-12 overflow-x-auto border-t pt-6">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="label-eyebrow text-ink-muted">
                      <th className="py-2 text-left font-medium">Observed</th>
                      <th className="py-2 text-right font-medium">P(class)</th>
                      <th className="py-2 text-right font-medium">Points</th>
                      <th className="py-2 text-right font-medium">Comments</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...points]
                      .reverse()
                      .slice(0, 12)
                      .map((point, index) => (
                        <tr key={index} className="border-ink-border border-t">
                          <td className="py-2">
                            {dateTimeLabel(point.timestamp ?? point.observed_at ?? point.time)}
                          </td>
                          <td className="numeric py-2 text-right">
                            {percentLabel(point.viral_probability ?? point.probability)}
                          </td>
                          <td className="numeric py-2 text-right">{num(point.points)}</td>
                          <td className="numeric py-2 text-right">
                            {num(point.num_comments ?? point.comments)}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </ScrollLift>
            ) : null}
          </div>
          <ScrollDrift className="mx-auto max-w-[1500px] px-5 pb-16 md:px-8" from={40} to={-40}>
            <p className="label-eyebrow text-ink-muted">
              live snapshot · velocity features · re-inference on every poll
            </p>
          </ScrollDrift>
          <div className="grain-overlay" />
        </section>
      ) : null}
    </div>
  );
}
