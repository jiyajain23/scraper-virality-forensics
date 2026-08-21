import { useRef, type ReactNode } from "react";
import { motion, useScroll, useSpring, useTransform } from "motion/react";
import { cn } from "@/lib/utils";

/** House spring — same settle as the hero, so every section shares one timing. */
function useSmoothProgress(target: React.RefObject<HTMLElement | null>, offset: string[]) {
  const { scrollYProgress } = useScroll({
    target,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    offset: offset as any,
  });
  return useSpring(scrollYProgress, {
    stiffness: 85,
    damping: 25,
    mass: 0.35,
    restDelta: 0.0005,
  });
}

/**
 * Scroll-linked lift: content rises, un-blurs and settles as the block crosses
 * the viewport, then eases back out as it leaves — continuous, not a one-shot.
 */
export function ScrollLift({
  children,
  className,
  distance = 70,
}: {
  children: ReactNode;
  className?: string;
  distance?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const progress = useSmoothProgress(ref, ["start 0.95", "end 0.35"]);
  const y = useTransform(progress, [0, 1], [distance, 0]);
  const opacity = useTransform(progress, [0, 0.55, 1], [0, 0.85, 1]);
  const blurValue = useTransform(progress, [0, 0.7], [8, 0]);
  const filter = useTransform(blurValue, (v) => `blur(${v}px)`);

  return (
    <motion.div
      ref={ref}
      className={cn(className)}
      style={{ y, opacity, filter, willChange: "transform, opacity, filter" }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Pinned scene: the inner content sticks while the outer track scrolls, and the
 * content scales/fades on the way out — the signature move in the reference film.
 */
export function ScrollScene({
  children,
  className,
  track = "180vh",
}: {
  children: ReactNode;
  className?: string;
  /** Height of the scroll track that drives the pin. */
  track?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const progress = useSmoothProgress(ref, ["start start", "end end"]);
  const scale = useTransform(progress, [0, 0.75, 1], [1, 1, 0.94]);
  const opacity = useTransform(progress, [0, 0.75, 1], [1, 1, 0]);
  const y = useTransform(progress, [0, 1], [0, -60]);

  return (
    <div ref={ref} className={cn("relative", className)} style={{ height: track }}>
      <div className="sticky top-0 flex h-screen items-center overflow-hidden">
        <motion.div
          style={{ scale, opacity, y, willChange: "transform, opacity" }}
          className="w-full"
        >
          {children}
        </motion.div>
      </div>
    </div>
  );
}

/** Scroll-linked horizontal drift, used for the marquee / eyebrow rules. */
export function ScrollDrift({
  children,
  className,
  from = -80,
  to = 80,
}: {
  children: ReactNode;
  className?: string;
  from?: number;
  to?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const progress = useSmoothProgress(ref, ["start end", "end start"]);
  const x = useTransform(progress, [0, 1], [from, to]);

  return (
    <div ref={ref} className={cn("overflow-hidden", className)}>
      <motion.div style={{ x, willChange: "transform" }}>{children}</motion.div>
    </div>
  );
}
