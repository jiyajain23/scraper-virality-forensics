import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";
import ScrollExpandMedia from "@/components/ui/scroll-expansion-hero";
import { GlassCard } from "@/components/ui/glass-card";
import { ScrollWords } from "@/components/motion/ScrollWords";
import { Reveal, Stagger, StaggerItem } from "@/components/motion/Reveal";
import { ScrollLift, ScrollDrift } from "@/components/motion/ScrollScene";
import clouds from "@/assets/hero-clouds.jpg";
import grainField from "@/assets/grain-field-hero.jpg";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Virality Intel — decide what to post on Hacker News, and when" },
      {
        name: "description",
        content:
          "A client for the Hacker News virality intelligence API: score a title, monitor a live post's momentum, and read what the front page is rewarding right now.",
      },
      { property: "og:title", content: "Virality Intel — what to post on Hacker News, and when" },
      {
        property: "og:description",
        content:
          "Score a title, monitor a live post's momentum, and read what the front page is rewarding right now.",
      },
    ],
  }),
  component: Landing,
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

function Landing() {
  return (
    <div>
      <ScrollExpandMedia
        mediaType="video"
        mediaSrc="/fifnal-video.mp4"
        posterSrc={clouds}
        bgImageSrc={grainField}
        title="Post with intent"
        date="Hacker News virality intelligence"
        scrollToExpand="Scroll to expand"
      >
        {/* Editorial explainer */}
        <div>
          <section className="bg-background relative pt-24">
            <div className="mx-auto max-w-[1500px] px-5 md:px-8">
              <Reveal>
                <p className="label-eyebrow text-muted-foreground">What this is</p>
              </Reveal>
            </div>
          </section>
          <section className="bg-background relative">
            <div className="mx-auto grid max-w-[1500px] gap-12 px-5 pb-24 md:grid-cols-12 md:px-8">
              <div className="md:col-span-7">
                <Reveal>
                  <p className="text-muted-foreground max-w-xl text-base leading-relaxed">
                    Hacker News decides in the first hour. Virality Intel is a client for your
                    intelligence service: it scores a title against the successful-story corpus,
                    tracks a live submission's velocity and front-page probability, and reads which
                    topics, domains and posting windows the front page is rewarding right now.
                  </p>
                </Reveal>
                <Reveal delay={0.12}>
                  <div className="mt-10 flex flex-wrap items-center gap-4">
                    <Link
                      to="/title"
                      className="bg-primary text-primary-foreground group inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-medium transition-opacity hover:opacity-90"
                    >
                      Score a title
                      <ArrowUpRight className="size-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    </Link>
                    <Link
                      to="/overview"
                      className="label-eyebrow text-foreground inline-flex items-center gap-2 underline-offset-8 hover:underline"
                    >
                      See the live pulse <ArrowUpRight className="size-4" />
                    </Link>
                  </div>
                </Reveal>
              </div>

              <ScrollLift className="md:col-span-5">
                <GlassCard className="grid gap-8 p-8 sm:grid-cols-3">
                  {[
                    { k: "15s", v: "Live poll interval while a story climbs" },
                    { k: "4", v: "Workflows: score, monitor, trends, research" },
                    { k: "1h", v: "The window that decides the front page" },
                  ].map((stat) => (
                    <div key={stat.k}>
                      <p className="display-lg numeric">{stat.k}</p>
                      <p className="text-muted-foreground mt-2 text-xs leading-relaxed">{stat.v}</p>
                    </div>
                  ))}
                </GlassCard>
              </ScrollLift>
            </div>
          </section>
        </div>

        {/* Statement */}
        <section className="bg-background relative">
          <div className="mx-auto max-w-[1500px] px-5 pb-24 md:px-8">
            <ScrollWords
              className="display-xl text-foreground max-w-5xl"
              text="Ask the service what a title is worth, whether a live post is accelerating, and which window is open."
              emphasis={[3, 4, 5]}
            />
          </div>
        </section>
      </ScrollExpandMedia>


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

      {/* Marquee */}
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
