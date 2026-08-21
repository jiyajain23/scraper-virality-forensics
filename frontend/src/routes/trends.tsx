import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { PageIntro } from "@/components/site/PageIntro";
import { ErrorState, LoadingState } from "@/components/site/States";
import { TrendingTopics } from "@/components/intel/TrendingTopics";
import { DomainLeaderboard } from "@/components/intel/DomainLeaderboard";
import { PostingWindow } from "@/components/intel/PostingWindow";
import { useBestTime, useTrending, useTrendingDomains } from "@/hooks/useFeeds";
import { CurtainReveal, Reveal, Stagger, StaggerItem } from "@/components/motion/Reveal";
import { ScrollDrift, ScrollLift } from "@/components/motion/ScrollScene";
import { ParallaxMedia } from "@/components/motion/ParallaxMedia";
import { decimal, hourWindow, num } from "@/lib/format";
import sphere from "@/assets/dark-sphere.jpg";

const WINDOWS = [5, 12, 24, 48];

export const Route = createFileRoute("/trends")({
  head: () => ({
    meta: [
      { title: "Topic Intelligence — what's working on Hacker News now" },
      {
        name: "description",
        content:
          "Trending phrases, domain performance and the best posting window, aggregated by the virality intelligence service from recent Hacker News captures.",
      },
      { property: "og:title", content: "Topic Intelligence — what's working on HN now" },
      {
        property: "og:description",
        content: "Trending phrases, domain leaderboard and recommended posting windows.",
      },
    ],
  }),
  component: TrendsPage,
});

function TrendsPage() {
  const [hours, setHours] = useState(5);
  const [topN, setTopN] = useState(10);

  const trending = useTrending({ hours, top_n: topN });
  const domains = useTrendingDomains({ top_n: 15 });
  const bestTime = useBestTime();

  const recommended =
    bestTime.data?.best_window ??
    bestTime.data?.recommended_window ??
    bestTime.data?.recommendation ??
    null;
  const slots = bestTime.data?.slots ?? bestTime.data?.by_day ?? bestTime.data?.by_hour ?? [];

  return (
    <div className="pb-32">
      <PageIntro
        eyebrow="Workflow 03 — the room you're walking into"
        title="What the front page"
        accent="is rewarding"
        description="Trending phrases, domain performance and posting windows are ranked by the feed engine from recent captures. The interface renders the ranking; it never computes it."
        aside={
          <div className="flex flex-wrap gap-2">
            {WINDOWS.map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setHours(value)}
                className={
                  hours === value
                    ? "bg-ink text-ink-foreground label-eyebrow rounded-full px-3 py-1.5"
                    : "label-eyebrow border-border rounded-full border px-3 py-1.5"
                }
              >
                {value}h
              </button>
            ))}
            <button
              type="button"
              onClick={() => setTopN((v) => (v === 10 ? 20 : 10))}
              className="label-eyebrow border-border rounded-full border px-3 py-1.5"
            >
              Top {topN}
            </button>
          </div>
        }
      />

      <section className="mx-auto max-w-[1500px] px-5 md:px-8">
        <Reveal>
          <h2 className="label-eyebrow text-muted-foreground rule-top pt-8">Trending topics</h2>
        </Reveal>
        <div className="mt-6">
          {trending.isPending ? (
            <LoadingState label="Aggregating recent captures" />
          ) : trending.isError ? (
            <ErrorState error={trending.error} onRetry={() => trending.refetch()} />
          ) : (
            <ScrollLift>
              <TrendingTopics topics={trending.data ?? []} />
            </ScrollLift>
          )}
        </div>
      </section>

      <section className="mt-24">
        <CurtainReveal>
          <ParallaxMedia src={sphere} alt="Dark sphere with orbiting rings" height="65vh" />
        </CurtainReveal>
      </section>

      <section className="surface-ink relative">
        <div className="mx-auto max-w-[1500px] px-5 py-20 md:px-8">
          <CurtainReveal>
            <h2 className="display-xl">
              Best posting <span className="serif-accent">window</span>
            </h2>
          </CurtainReveal>
          <div className="mt-10">
            {bestTime.isPending ? (
              <p className="text-ink-muted text-sm">Reading engagement history…</p>
            ) : bestTime.isError ? (
              <ErrorState error={bestTime.error} onRetry={() => bestTime.refetch()} />
            ) : recommended ? (
              <ScrollLift>
                <PostingWindow window={recommended} />
              </ScrollLift>
            ) : (
              <p className="text-ink-muted text-sm">
                The service returned no recommended window yet.
              </p>
            )}
          </div>

          {slots.length ? (
            <Stagger className="border-ink-border mt-14 grid gap-px border-t pt-6 sm:grid-cols-2 lg:grid-cols-4">
              {slots.slice(0, 8).map((slot, index) => (
                <StaggerItem key={index} className="py-4">
                  <p className="label-eyebrow text-ink-muted">
                    {slot.day ?? slot.day_of_week ?? "—"}
                  </p>
                  <p className="numeric mt-2 text-xl">
                    {hourWindow(slot.hour ?? slot.hour_utc) ?? "—"}
                  </p>
                  <p className="text-ink-muted mt-2 text-xs">
                    {typeof slot.avg_points === "number"
                      ? `Avg ${decimal(slot.avg_points, 0)} points`
                      : ""}
                    {typeof slot.story_count === "number" ? ` · ${num(slot.story_count)} stories` : ""}
                  </p>
                </StaggerItem>
              ))}
            </Stagger>
          ) : null}
        </div>
        <div className="grain-overlay" />
      </section>

      <section className="mx-auto max-w-[1500px] px-5 pt-24 md:px-8">
        <Reveal>
          <h2 className="label-eyebrow text-muted-foreground rule-top pt-8">Domain performance</h2>
        </Reveal>
        <div className="mt-6">
          {domains.isPending ? (
            <LoadingState label="Ranking domains" />
          ) : domains.isError ? (
            <ErrorState error={domains.error} onRetry={() => domains.refetch()} />
          ) : (
            <ScrollLift>
              <DomainLeaderboard domains={domains.data ?? []} />
            </ScrollLift>
          )}
        </div>
        <ScrollDrift className="mt-12" from={-40} to={40}>
          <p className="label-eyebrow text-muted-foreground">
            aggregated by the feed engine · ranking computed server-side
          </p>
        </ScrollDrift>
      </section>
    </div>
  );
}
