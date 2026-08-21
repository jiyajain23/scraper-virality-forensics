import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { PageIntro } from "@/components/site/PageIntro";
import { ErrorState, EmptyState, LoadingState } from "@/components/site/States";
import { TitleAnalysisResult } from "@/components/intel/TitleAnalysis";
import { useTitleAnalysis } from "@/hooks/useTitleAnalysis";
import { ParallaxMedia } from "@/components/motion/ParallaxMedia";
import { ScrollWords } from "@/components/motion/ScrollWords";
import { ScrollLift, ScrollDrift } from "@/components/motion/ScrollScene";
import { CurtainReveal, Reveal } from "@/components/motion/Reveal";
import clouds from "@/assets/hero-clouds.jpg";

export const Route = createFileRoute("/title")({
  head: () => ({
    meta: [
      { title: "Title Intelligence — score a Hacker News title before posting" },
      {
        name: "description",
        content:
          "Score a draft Hacker News title against the successful-story corpus: matched phrases, structure, similar stories, and the recommended posting window.",
      },
      { property: "og:title", content: "Title Intelligence — score a title before posting" },
      {
        property: "og:description",
        content:
          "Matched phrases, structural signals, similar successful stories and a recommended posting window for your draft title.",
      },
    ],
  }),
  component: TitleIntelligencePage,
});

function TitleIntelligencePage() {
  const [title, setTitle] = useState("");
  const [touched, setTouched] = useState(false);
  const analysis = useTitleAnalysis();

  const trimmed = title.trim();
  const invalid = touched && trimmed.length < 5;

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setTouched(true);
    if (trimmed.length < 5) return;
    analysis.mutate(trimmed);
  };

  return (
    <div className="pb-32">
      <PageIntro
        eyebrow="Workflow 01 — before you post"
        title="Read the title"
        accent="before Hacker News does"
        description="The title engine extracts n-gram phrases, compares them against the successful-story corpus with TF-IDF similarity, checks structure and returns a posting window. Nothing is computed in the browser."
      />

      <section className="mx-auto max-w-[1500px] px-5 md:px-8">
        <Reveal>
        <form onSubmit={submit} className="rule-top pt-8">
          <label htmlFor="title" className="label-eyebrow text-muted-foreground">
            Draft title
          </label>
          <div className="mt-4 flex flex-col gap-4 md:flex-row md:items-center">
            <input
              id="title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Show HN: I built a local AI coding assistant in Rust"
              className="display-lg placeholder:text-muted-foreground/50 w-full border-b bg-transparent pb-3 outline-none focus:border-foreground"
            />
            <button
              type="submit"
              disabled={analysis.isPending}
              className="bg-ink text-ink-foreground shrink-0 rounded-full px-6 py-3 text-sm font-medium transition-transform duration-300 hover:scale-[1.03] disabled:opacity-50"
            >
              {analysis.isPending ? "Analyzing…" : "Analyze title"}
            </button>
          </div>
          <div className="mt-3 flex justify-between text-xs">
            <span className="text-destructive">
              {invalid ? "Enter at least 5 characters before analyzing." : ""}
            </span>
            <span className="numeric text-muted-foreground">{title.length} characters</span>
          </div>
        </form>
        </Reveal>
      </section>

      <section className="mx-auto mt-16 max-w-[1500px] px-5 md:px-8">
        {analysis.isPending ? <LoadingState label="Scoring against the corpus" /> : null}
        {analysis.isError ? (
          <ErrorState
            error={analysis.error}
            onRetry={() => analysis.mutate(trimmed)}
            label="Analyze again"
          />
        ) : null}
        {!analysis.isPending && !analysis.isError && !analysis.data ? (
          <EmptyState
            title="Enter a title to begin analysis"
            hint="Nothing is requested until you submit — the interface never calls the API on every keystroke."
          />
        ) : null}
        {analysis.data && !analysis.isPending ? (
          <ScrollLift>
            <TitleAnalysisResult data={analysis.data} />
          </ScrollLift>
        ) : null}
      </section>

      <section className="mt-28">
        <CurtainReveal>
          <ParallaxMedia src={clouds} alt="High-altitude cloud layer" height="60vh" />
        </CurtainReveal>
      </section>

      <section className="mx-auto max-w-[1500px] px-5 pt-20 md:px-8">
        <ScrollWords
          className="display-xl max-w-4xl"
          text="A score is a signal, not a promise. The model estimates the probability that a story reaches the high-performance class — the rest is timing, topic and luck."
          emphasis={[3, 4, 5]}
        />
        <ScrollDrift className="mt-10" from={-40} to={40}>
          <p className="label-eyebrow text-muted-foreground">
            n-gram phrases · TF-IDF similarity · structural signals · posting window
          </p>
        </ScrollDrift>
      </section>
    </div>
  );
}
