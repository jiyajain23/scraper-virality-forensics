import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { PageIntro } from "@/components/site/PageIntro";
import { EmptyState, ErrorState, LoadingState } from "@/components/site/States";
import { SimilarStoryList } from "@/components/intel/SimilarStoryList";
import { useSimilarStories } from "@/hooks/useFeeds";
import { ScrollWords } from "@/components/motion/ScrollWords";
import { ScrollLift, ScrollDrift } from "@/components/motion/ScrollScene";
import { Reveal } from "@/components/motion/Reveal";

const RANGES = [12, 24, 48, 72];

export const Route = createFileRoute("/research")({
  head: () => ({
    meta: [
      { title: "Research — has this Hacker News story been told already?" },
      {
        name: "description",
        content:
          "Search recent Hacker News captures by topic to see whether a similar story already ran and how well it performed.",
      },
      { property: "og:title", content: "Research — find similar Hacker News stories" },
      {
        property: "og:description",
        content: "Search recent captures by topic and see how similar submissions performed.",
      },
    ],
  }),
  component: ResearchPage,
});

function ResearchPage() {
  const [draft, setDraft] = useState("");
  const [topic, setTopic] = useState("");
  const [hours, setHours] = useState(48);

  const similar = useSimilarStories(topic, hours);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setTopic(draft.trim());
  };

  return (
    <div className="pb-32">
      <PageIntro
        eyebrow="Workflow 04 — competitive read"
        title="Find out who"
        accent="already posted this"
        description="Topic search runs against recent captures held by the service. Use it to check whether your idea has already had its moment, and how those submissions performed."
        aside={
          <div className="flex flex-wrap gap-2">
            {RANGES.map((value) => (
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
                last {value}h
              </button>
            ))}
          </div>
        }
      />

      <section className="mx-auto max-w-[1500px] px-5 md:px-8">
        <Reveal>
        <form onSubmit={submit} className="rule-top pt-8">
          <label htmlFor="topic" className="label-eyebrow text-muted-foreground">
            Topic
          </label>
          <div className="mt-4 flex flex-col gap-4 md:flex-row md:items-center">
            <input
              id="topic"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="vector database"
              className="display-lg placeholder:text-muted-foreground/50 w-full border-b bg-transparent pb-3 outline-none focus:border-foreground"
            />
            <button
              type="submit"
              className="bg-ink text-ink-foreground shrink-0 rounded-full px-6 py-3 text-sm font-medium transition-transform duration-300 hover:scale-[1.03]"
            >
              Search stories
            </button>
          </div>
        </form>
        </Reveal>
      </section>

      <section className="mx-auto mt-16 max-w-[1500px] px-5 md:px-8">
        {!topic ? (
          <EmptyState
            title="Enter a topic to search"
            hint="For example: local LLM, Rust compiler, vector database."
          />
        ) : similar.isPending ? (
          <LoadingState label="Searching recent captures" />
        ) : similar.isError ? (
          <ErrorState error={similar.error} onRetry={() => similar.refetch()} />
        ) : (
          <ScrollLift>
            <SimilarStoryList
              stories={similar.data ?? []}
              emptyHint={`No stories matched “${topic}” in the last ${hours} hours.`}
            />
          </ScrollLift>
        )}
      </section>

      <section className="mx-auto max-w-[1500px] px-5 pt-28 md:px-8">
        <ScrollWords
          className="display-xl max-w-4xl"
          text="Timing beats novelty. A saturated topic buries a good post; an empty week lifts an ordinary one."
          emphasis={[0, 1, 2]}
        />
        <ScrollDrift className="mt-10" from={40} to={-40}>
          <p className="label-eyebrow text-muted-foreground">
            recent captures · topic match · performance history
          </p>
        </ScrollDrift>
      </section>
    </div>
  );
}
