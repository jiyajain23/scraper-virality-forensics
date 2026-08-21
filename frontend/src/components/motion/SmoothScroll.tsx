import { useEffect } from "react";

/**
 * Inertial (lerped) scrolling — the single biggest reason the reference films
 * feel liquid. Every scroll-linked animation inherits this smoothing.
 * Disabled for users who ask for reduced motion.
 */
export function SmoothScroll() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let raf = 0;
    let lenis: { raf: (t: number) => void; destroy: () => void } | null = null;
    let cancelled = false;

    void import("lenis").then(({ default: Lenis }) => {
      if (cancelled) return;
      const instance = new Lenis({
        duration: 1.35,
        easing: (t: number) => 1 - Math.pow(1 - t, 3.2),
        touchMultiplier: 1.6,
        wheelMultiplier: 0.9,
      });
      lenis = instance as unknown as typeof lenis;
      const loop = (time: number) => {
        instance.raf(time);
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    });

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      lenis?.destroy();
    };
  }, []);

  return null;
}
