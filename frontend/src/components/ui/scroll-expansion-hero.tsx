import { useRef, type ReactNode } from "react";
import { motion, useScroll, useSpring, useTransform } from "motion/react";
import { cn } from "@/lib/utils";

interface ScrollExpandMediaProps {
  mediaType?: "video" | "image";
  mediaSrc: string;
  posterSrc?: string;
  bgImageSrc?: string;
  title?: string;
  date?: string;
  scrollToExpand?: string;
  textBlend?: boolean;
  className?: string;
  children?: ReactNode;
}


/**
 * Scroll-expansion hero: a small media card grows to full-bleed as the section
 * scrolls, while the title halves drift apart. Scroll-linked (not wheel-hijacked)
 * and spring-smoothed, so it inherits the site's inertial scrolling.
 */
export default function ScrollExpandMedia({
  mediaType = "video",
  mediaSrc,
  posterSrc,
  bgImageSrc,
  title,
  date,
  scrollToExpand,
  textBlend = false,
  className,
  children,
}: ScrollExpandMediaProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: trackRef,
    offset: ["start start", "end end"],
  });
  const progress = useSpring(scrollYProgress, {
    stiffness: 80,
    damping: 24,
    mass: 0.35,
    restDelta: 0.0005,
  });

  // Card grows from a small framed clip to full-bleed.
  const scale = useTransform(progress, [0, 0.85], [0.34, 1]);
  const radius = useTransform(progress, [0, 0.85], [24, 0]);
  const veil = useTransform(progress, [0, 0.85], [0.3, 0.12]);
  const cardShadow = useTransform(
    progress,
    [0, 0.85],
    ["0 40px 120px -40px color-mix(in oklch, var(--ink) 45%, transparent)", "0 0 0 rgba(0,0,0,0)"],
  );

  const bgOpacity = useTransform(progress, [0, 0.7], [1, 0.15]);
  const bgScale = useTransform(progress, [0, 1], [1.12, 1]);

  // Title halves drift apart as the media opens, then fade out.
  const driftLeft = useTransform(progress, [0, 0.9], ["0vw", "-46vw"]);
  const driftRight = useTransform(progress, [0, 0.9], ["0vw", "46vw"]);
  const titleOpacity = useTransform(progress, [0, 0.72, 0.95], [1, 1, 0]);
  const hintOpacity = useTransform(progress, [0, 0.25], [1, 0]);

  const firstWord = title ? title.split(" ")[0] : "";
  const restOfTitle = title ? title.split(" ").slice(1).join(" ") : "";

  return (
    <div className={cn("relative bg-background", className)}>
      <div ref={trackRef} className="relative h-[320vh]">
        <div className="sticky top-0 flex h-screen items-center justify-center overflow-hidden">
          {/* Soft paper plate — a warm, blurred wash instead of a hard image */}
          <motion.div
            aria-hidden
            style={{ opacity: bgOpacity, scale: bgScale, willChange: "transform, opacity" }}
            className="absolute inset-0"
          >
            <div className="bg-background absolute inset-0" />
            <div
              className="absolute inset-0"
              style={{
                background:
                  "radial-gradient(120% 90% at 50% 8%, color-mix(in oklch, var(--accent) 14%, transparent), transparent 62%)",
              }}
            />
            {bgImageSrc ? (
              <img
                src={bgImageSrc}
                alt=""
                aria-hidden
                className="absolute inset-0 h-full w-full object-cover opacity-90"
                style={{
                  maskImage:
                    "linear-gradient(to bottom, transparent 2%, black 30%, black 88%, transparent 100%)",
                  WebkitMaskImage:
                    "linear-gradient(to bottom, transparent 2%, black 30%, black 88%, transparent 100%)",
                }}
              />
            ) : null}
            <div
              aria-hidden
              className="absolute inset-0"
              style={{
                background:
                  "linear-gradient(to bottom, color-mix(in oklch, var(--background) 78%, transparent) 0%, color-mix(in oklch, var(--background) 22%, transparent) 30%, transparent 62%, color-mix(in oklch, var(--background) 55%, transparent) 92%, var(--background) 100%)",
              }}
            />
            <div className="grain-overlay" aria-hidden />
          </motion.div>


          {/* Expanding media */}
          <motion.div
            style={{
              scale,
              borderRadius: radius,
              boxShadow: cardShadow,
              willChange: "transform",
            }}

            className="relative h-screen w-screen overflow-hidden"
          >
            {mediaType === "video" ? (
              <video
                src={mediaSrc}
                poster={posterSrc}
                autoPlay
                muted
                loop
                playsInline
                preload="auto"
                controls={false}
                disablePictureInPicture
                className="pointer-events-none h-full w-full object-cover"
              />
            ) : (
              <img src={mediaSrc} alt={title ?? "Media"} className="h-full w-full object-cover" />
            )}
            <motion.div
              style={{ opacity: veil }}
              className="pointer-events-none absolute inset-0"
              aria-hidden
            >
              <div className="bg-background absolute inset-0" />
            </motion.div>
            <div
              className="pointer-events-none absolute inset-x-0 bottom-0 h-[28%]"
              aria-hidden
              style={{
                background:
                  "linear-gradient(to bottom, transparent, color-mix(in oklch, var(--background) 92%, transparent))",
              }}
            />
            <div className="grain-overlay-soft" />
          </motion.div>

          {/* Title */}
          <motion.div
            style={{ opacity: titleOpacity }}
            className={cn(
              "pointer-events-none absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 px-5 text-center",
              textBlend ? "mix-blend-difference" : "",
            )}
          >
            {date ? (
              <motion.p style={{ x: driftLeft }} className="label-eyebrow text-foreground/70 mb-4">
                {date}
              </motion.p>
            ) : null}
            <motion.h1 style={{ x: driftLeft }} className="display-hero text-foreground">
              {firstWord}
            </motion.h1>
            <motion.h1 style={{ x: driftRight }} className="display-hero text-foreground">
              <span className="serif-accent">{restOfTitle}</span>
            </motion.h1>
            {scrollToExpand ? (
              <motion.p
                style={{ opacity: hintOpacity }}
                className="label-eyebrow text-foreground/60 mt-10"
              >
                {scrollToExpand}
              </motion.p>
            ) : null}
          </motion.div>
        </div>
      </div>

      {children ? <div className="relative z-10">{children}</div> : null}
    </div>
  );
}
