import { useRef } from "react";
import { motion, useScroll, useSpring, useTransform, type MotionValue } from "motion/react";
import { cn } from "@/lib/utils";

/**
 * Scroll-linked, word-by-word text reveal (the headline treatment from the
 * reference films): words start dim and ink in as the block crosses the viewport.
 * The raw scroll progress is spring-smoothed so words settle instead of snapping,
 * and each word's range overlaps its neighbours so the reveal reads as one wave.
 */
export function ScrollWords({
  text,
  className,
  emphasis,
}: {
  text: string;
  className?: string;
  /** Words at these indexes render in the serif italic accent face. */
  emphasis?: number[];
}) {
  const ref = useRef<HTMLParagraphElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 0.9", "end 0.55"],
  });
  const progress = useSpring(scrollYProgress, {
    stiffness: 90,
    damping: 26,
    mass: 0.4,
    restDelta: 0.0005,
  });

  const words = text.split(" ");

  return (
    <p ref={ref} className={cn("flex flex-wrap", className)}>
      {words.map((word, i) => {
        // All words must finish inking in well before progress hits 1, otherwise
        // the tail of the sentence stays blurred even at the end of the scroll.
        const FINISH = 0.62;
        const step = FINISH / words.length;
        // Overlapping windows (each word fades over ~2.6 slots) => continuous wave.
        const start = i * step;
        const end = Math.min(0.995, start + step * 2.6);
        return (
          <Word
            key={`${word}-${i}`}
            progress={progress}
            range={[start, end]}
            accent={emphasis?.includes(i)}
          >
            {word}
          </Word>
        );
      })}
    </p>
  );
}

function Word({
  children,
  progress,
  range,
  accent,
}: {
  children: string;
  progress: MotionValue<number>;
  range: [number, number];
  accent?: boolean | undefined;
}) {
  const opacity = useTransform(progress, range, [0.14, 1]);
  const y = useTransform(progress, range, ["0.34em", "0em"]);
  const blur = useTransform(progress, range, [6, 0]);
  const filter = useTransform(blur, (value) => `blur(${value}px)`);

  return (
    <span className="relative mr-[0.25em] inline-block overflow-hidden pb-[0.06em]">
      <motion.span
        style={{ opacity, y, filter, willChange: "transform, opacity, filter" }}
        className={cn("inline-block", accent && "serif-accent pr-[0.06em]")}
      >
        {children}
      </motion.span>
    </span>
  );
}
