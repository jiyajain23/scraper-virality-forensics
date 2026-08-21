import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";
import { ScrollWords } from "@/components/motion/ScrollWords";
import { Reveal, CurtainReveal, Stagger, StaggerItem } from "@/components/motion/Reveal";
import { ScrollScene, ScrollLift, ScrollDrift } from "@/components/motion/ScrollScene";
import { ParallaxScene } from "@/components/ui/parallax-scrolling";
import { TrendingTopics } from "@/components/intel/TrendingTopics";
import { PostingWindow } from "@/components/intel/PostingWindow";
import { ErrorState, LoadingState } from "@/components/site/States";
import { GlassCard } from "@/components/ui/glass-card";
import { useBestTime, useTrending } from "@/hooks/useFeeds";
import { useHealth } from "@/hooks/useHealth";

export const Route = createFileRoute("/overview")({
  head: () => ({
    meta: [
      { title: "Live overview — Hacker News pulse and posting window" },
      {
        name: "description",
        content:
          "The live Hacker News pulse: trending topics from recent captures, the recommended posting window, and jump-off points into title scoring and monitoring.",
      },
      { property: "og:title", content: "Live overview — Hacker News pulse and posting window" },
      {
        property: "og:description",
        content:
          "Trending topics from recent captures, the recommended posting window, and jump-off points into title scoring and monitoring.",
      },
    ],
  }),

  component: Overview,
});

const QUICK_ACTIONS = [
  {
    to: "/title" as const,
    label: "Analyze a title",
    copy: "Score a draft against the successful-story corpus.",
  },
  {
    to: "/monitor" as const,
    label: "Monitor a story",
    copy: "Poll a live submission for velocity and probability.",
  },
  {
    to: "/trends" as const,
    label: "Explore trends",
    copy: "Topics, domains and the best posting window.",
  },
  {
    to: "/research" as const,
    label: "Research a topic",
    copy: "See whether a similar story already ran.",
  },
];

function Overview() {
  const trending = useTrending({ hours: 5, top_n: 6 });
  const bestTime = useBestTime();
  const health = useHealth();

  const recommended =
    bestTime.data?.best_window ??
    bestTime.data?.recommended_window ??
    bestTime.data?.recommendation ??
    null;

  return (
    <div>
      {/* Layered parallax hero */}
      <ParallaxScene title="Virality Forensics" caption="Hacker News virality intelligence" />

      {/* Intro band */}
      <section className="surface-ink relative">
        <div className="text-ink-foreground mx-auto max-w-[1500px] px-5 py-24 md:px-8">
          <p className="label-eyebrow text-ink-muted">Hacker News virality intelligence</p>
          <CurtainReveal className="mt-6">
            <h1 className="display-hero max-w-5xl">
              Post with <span className="serif-accent">intent,</span> not hope
            </h1>
          </CurtainReveal>
          <div className="border-ink-border mt-12 grid gap-6 border-t pt-6 md:grid-cols-4">
            <p className="text-ink-muted max-w-sm text-sm leading-relaxed md:col-span-2">
              An interface for the intelligence service you already run: title scoring, live post
              monitoring, trend aggregation and topic research.
            </p>
            <div className="text-ink-muted label-eyebrow md:col-span-2 md:text-right">
              {health.isSuccess ? (
                <span className="inline-flex items-center gap-2">
                  <span className="bg-rising animate-pulse-dot size-1.5 rounded-full" />
                  Service {health.data?.status ?? "responding"}
                </span>
              ) : health.isError ? (
                <Link to="/system" className="underline underline-offset-4">
                  Service unreachable — check configuration
                </Link>
              ) : (
                <span>Checking service…</span>
              )}
            </div>
          </div>
        </div>
        <div className="grain-overlay" />
      </section>

      {/* Scroll-linked statement — pinned while the words ink in */}
      <section className="surface-ink relative">
        <ScrollScene track="220vh">
          <div className="mx-auto max-w-[1500px] px-5 md:px-8">
            <ScrollWords
              className="display-xl text-ink-foreground max-w-5xl"
              text="Hacker News decides in the first hour. This interface asks the service what a title is worth, whether a live post is accelerating, and which window is open."
              emphasis={[5, 6, 7]}
            />
          </div>
        </ScrollScene>
        <div className="grain-overlay" />
      </section>

      {/* Live pulse */}
      <section className="mx-auto max-w-[1500px] px-5 py-24 md:px-8">
        <CurtainReveal>
          <div className="flex flex-wrap items-baseline justify-between gap-4">
            <h2 className="display-xl">
              Current <span className="serif-accent">pulse</span>
            </h2>
            <Link to="/trends" className="label-eyebrow inline-flex items-center gap-2">
              All topic intelligence <ArrowUpRight className="size-4" />
            </Link>
          </div>
        </CurtainReveal>

        <ScrollLift className="mt-10">
          <GlassCard className="p-6 md:p-8">
          {trending.isPending ? (
            <LoadingState label="Reading recent captures" />
          ) : trending.isError ? (
            <ErrorState error={trending.error} onRetry={() => trending.refetch()} />
          ) : (
            <TrendingTopics topics={trending.data ?? []} />
          )}
          </GlassCard>
        </ScrollLift>
      </section>

      {/* Best posting time band */}
      <section className="surface-ink relative overflow-hidden">
        <div className="mx-auto max-w-[1500px] px-5 py-24 md:px-8">
          <Reveal>
            <p className="label-eyebrow text-ink-muted">When to post</p>
          </Reveal>
          <CurtainReveal className="mt-5">
            <h2 className="display-xl">
              The window that <span className="serif-accent">keeps working</span>
            </h2>
          </CurtainReveal>
          <ScrollLift className="mt-12">
            <GlassCard variant="ink" className="p-6 md:p-8">
            {bestTime.isPending ? (
              <p className="text-ink-muted text-sm">Reading engagement history…</p>
            ) : bestTime.isError ? (
              <ErrorState error={bestTime.error} onRetry={() => bestTime.refetch()} />
            ) : recommended ? (
              <PostingWindow window={recommended} />
            ) : (
              <p className="text-ink-muted text-sm">
                The service hasn't returned a recommended window yet.
              </p>
            )}
            </GlassCard>
          </ScrollLift>
        </div>
        <div className="grain-overlay" />
      </section>



      {/* Quick actions */}
      <section className="mx-auto max-w-[1500px] px-5 py-28 md:px-8">
        <Reveal>
          <p className="label-eyebrow text-muted-foreground">Quick actions</p>
        </Reveal>
        <Stagger className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4" gap={0.1}>
          {QUICK_ACTIONS.map((action) => (
            <StaggerItem key={action.to} className="h-full">
              <GlassCard
                as={Link}
                interactive
                to={action.to}
                className="group flex h-full flex-col justify-between p-6"
              >
                <span className="display-lg">{action.label}</span>
                <span className="text-muted-foreground mt-8 text-sm">{action.copy}</span>
                <ArrowUpRight className="mt-6 size-5 transition-transform duration-300 group-hover:translate-x-1 group-hover:-translate-y-1" />
              </GlassCard>
            </StaggerItem>
          ))}
        </Stagger>
      </section>

      {/* Marquee — scroll-linked drift on top of the constant crawl */}
      <section className="border-t py-6">
        <ScrollDrift from={-70} to={70}>
          <div className="animate-marquee flex w-max gap-10 whitespace-nowrap">
            {Array.from({ length: 2 }).map((_, copy) => (
              <div key={copy} className="label-eyebrow text-muted-foreground flex gap-10">
                <span>Title scoring</span>
                <span>·</span>
                <span>Live monitoring</span>
                <span>·</span>
                <span>Velocity features</span>
                <span>·</span>
                <span>TF-IDF corpus matching</span>
                <span>·</span>
                <span>Domain leaderboards</span>
                <span>·</span>
                <span>Posting windows</span>
                <span>·</span>
                <span>Probability trajectory</span>
                <span>·</span>
              </div>
            ))}
          </div>
        </ScrollDrift>
      </section>
    </div>
  );
}
