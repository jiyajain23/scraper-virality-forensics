import { ArrowUpRight, Check } from "lucide-react";
import { Reveal } from "@/components/motion/Reveal";
import { SimilarStoryList } from "@/components/intel/SimilarStoryList";
import { PostingWindow } from "@/components/intel/PostingWindow";
import { decimal, num } from "@/lib/format";
import type { TitleAnalysis as TitleAnalysisData } from "@/types/api";

function firstNumber(...values: unknown[]): number | null {
  for (const value of values) {
    if (typeof value === "number" && !Number.isNaN(value)) return value;
  }
  return null;
}

export function TitleAnalysisResult({ data }: { data: TitleAnalysisData }) {
  const rawScore = firstNumber(data.pattern_score, data.score);
  const scoreOutOfTen = rawScore === null ? null : rawScore <= 1 ? rawScore * 10 : rawScore;
  const phrases = data.matched_phrases ?? data.matched_topics ?? [];
  const flags = data.structural_flags ?? [];
  const stories = data.similar_stories ?? [];
  const posting = data.best_posting_time ?? data.recommended_posting_time ?? null;

  return (
    <div className="space-y-20">
      <Reveal className="grid gap-10 md:grid-cols-12">
        <div className="md:col-span-5">
          <p className="label-eyebrow text-muted-foreground">Pattern score</p>
          <p className="numeric-xl mt-4">
            {scoreOutOfTen === null ? "—" : decimal(scoreOutOfTen, 1)}
            <span className="text-muted-foreground text-2xl"> / 10</span>
          </p>
          <p className="text-muted-foreground mt-4 max-w-sm text-sm leading-relaxed">
            Similarity of this title to historically high-performing Hacker News submissions, as
            computed by the title engine. Not a guarantee of outcome.
          </p>
          {firstNumber(data.structural_score) !== null ? (
            <p className="label-eyebrow text-muted-foreground mt-6">
              Structural score {decimal(data.structural_score, 2)}
            </p>
          ) : null}
        </div>

        <div className="md:col-span-3">
          <p className="label-eyebrow text-muted-foreground">Shape</p>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex items-baseline justify-between border-b pb-2">
              <dt className="text-muted-foreground">Characters</dt>
              <dd className="numeric">{num(data.title_length)}</dd>
            </div>
            <div className="flex items-baseline justify-between border-b pb-2">
              <dt className="text-muted-foreground">Words</dt>
              <dd className="numeric">{num(data.title_word_count)}</dd>
            </div>
          </dl>
        </div>

        <div className="md:col-span-4">
          <p className="label-eyebrow text-muted-foreground">Matched phrases</p>
          {phrases.length ? (
            <ul className="mt-4 flex flex-wrap gap-2">
              {phrases.map((phrase) => (
                <li
                  key={phrase}
                  className="border-border rounded-full border px-3 py-1 text-xs tracking-wide"
                >
                  {phrase}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground mt-4 text-sm">
              No salient phrases matched the successful corpus.
            </p>
          )}
        </div>
      </Reveal>

      {flags.length ? (
        <Reveal className="rule-top pt-8">
          <p className="label-eyebrow text-muted-foreground">Structural signals</p>
          <ul className="mt-5 grid gap-x-10 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
            {flags.map((flag) => (
              <li key={flag} className="flex items-start gap-3 border-b pb-3 text-sm">
                <Check className="text-accent mt-0.5 size-4 shrink-0" />
                <span>{flag}</span>
              </li>
            ))}
          </ul>
        </Reveal>
      ) : null}

      {posting ? (
        <Reveal className="rule-top pt-8">
          <p className="label-eyebrow text-muted-foreground">Recommended posting window</p>
          <div className="mt-6">
            <PostingWindow window={posting} />
          </div>
        </Reveal>
      ) : null}

      <Reveal className="rule-top pt-8">
        <div className="flex items-baseline justify-between gap-4">
          <p className="label-eyebrow text-muted-foreground">Similar successful stories</p>
          <ArrowUpRight className="text-muted-foreground size-4" />
        </div>
        <div className="mt-6">
          <SimilarStoryList stories={stories} emptyHint="The corpus returned no close matches." />
        </div>
      </Reveal>
    </div>
  );
}
