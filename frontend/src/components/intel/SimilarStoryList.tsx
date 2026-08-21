import { num, domainFromUrl } from "@/lib/format";
import type { SimilarStory } from "@/types/api";

export function SimilarStoryList({
  stories,
  emptyHint = "No stories returned.",
}: {
  stories: SimilarStory[];
  emptyHint?: string;
}) {
  if (!stories.length) {
    return <p className="text-muted-foreground text-sm">{emptyHint}</p>;
  }

  return (
    <ol className="divide-border divide-y">
      {stories.map((story, index) => {
        const points = typeof story.points === "number" ? story.points : null;
        const comments =
          typeof story.num_comments === "number"
            ? story.num_comments
            : typeof story.comments === "number"
              ? story.comments
              : null;
        const domain = story.domain ?? domainFromUrl(story.url);
        const key = `${story.story_id ?? story.objectID ?? index}-${index}`;

        return (
          <li key={key} className="group grid grid-cols-12 items-baseline gap-4 py-4">
            <span className="numeric text-muted-foreground col-span-1 text-xs">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div className="col-span-11 md:col-span-7">
              {story.url ? (
                <a
                  href={story.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-base leading-snug underline-offset-4 transition-colors group-hover:underline"
                >
                  {story.title ?? "Untitled story"}
                </a>
              ) : (
                <span className="text-base leading-snug">{story.title ?? "Untitled story"}</span>
              )}
              {domain ? (
                <span className="text-muted-foreground ml-2 text-xs">{domain}</span>
              ) : null}
            </div>
            <div className="text-muted-foreground col-span-6 text-xs md:col-span-2 md:text-right">
              {points === null ? "" : `${num(points)} points`}
            </div>
            <div className="text-muted-foreground col-span-6 text-xs md:col-span-2 md:text-right">
              {comments === null ? "" : `${num(comments)} comments`}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
