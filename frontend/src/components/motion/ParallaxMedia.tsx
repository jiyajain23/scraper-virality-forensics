import { useRef } from "react";
import { motion, useScroll, useSpring, useTransform } from "motion/react";
import { cn } from "@/lib/utils";

/** Full-bleed media that drifts against the scroll, like the reference films. */
export function ParallaxMedia({
  src,
  alt,
  className,
  height = "70vh",
  strength = 130,
  overlay = true,
  eager = false,
}: {
  src: string;
  alt: string;
  className?: string;
  height?: string;
  strength?: number;
  overlay?: boolean;
  eager?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  // Spring-smoothed so the drift keeps gliding for a beat after the wheel stops.
  const progress = useSpring(scrollYProgress, {
    stiffness: 80,
    damping: 24,
    mass: 0.35,
    restDelta: 0.0005,
  });
  const y = useTransform(progress, [0, 1], [-strength, strength]);
  const scale = useTransform(progress, [0, 0.5, 1], [1.18, 1.04, 1.18]);

  return (
    <div ref={ref} className={cn("relative w-full overflow-hidden", className)} style={{ height }}>
      <motion.img
        src={src}
        alt={alt}
        style={{ y, scale, willChange: "transform" }}
        loading={eager ? "eager" : "lazy"}
        className="absolute inset-0 h-full w-full object-cover"
      />
      {overlay ? (
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "linear-gradient(to bottom, color-mix(in oklch, var(--ink) 25%, transparent), transparent 35%, color-mix(in oklch, var(--ink) 55%, transparent))",
          }}
        />
      ) : null}
      <div className="grain-overlay" />
    </div>
  );
}
