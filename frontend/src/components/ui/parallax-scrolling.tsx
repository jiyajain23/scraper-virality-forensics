import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { cn } from "@/lib/utils";
import sky from "@/assets/px-sky.jpg";
import mountain from "@/assets/px-mountain.png";
import figure from "@/assets/px-figure.png";

/**
 * Osmo-style layered parallax: four depth planes are pushed down at different
 * rates as the section scrolls, so the title sits *inside* the scene.
 * Smooth scrolling comes from the app's global Lenis instance.
 */
export function ParallaxScene({
  title = "Virality Forensics",
  caption,
  className,
}: {
  title?: string;
  caption?: string;
  className?: string;
}) {
  const parallaxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = parallaxRef.current;
    if (!root) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    gsap.registerPlugin(ScrollTrigger);

    const ctx = gsap.context(() => {
      const triggerElement = root.querySelector("[data-parallax-layers]");
      if (!triggerElement) return;

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: triggerElement,
          start: "0% 0%",
          end: "100% 0%",
          scrub: 0,
        },
      });

      const layers = [
        { layer: "1", yPercent: 70 },
        { layer: "2", yPercent: 55 },
        { layer: "3", yPercent: 40 },
        { layer: "4", yPercent: 10 },
      ];

      layers.forEach((layerObj, idx) => {
        tl.to(
          triggerElement.querySelectorAll(`[data-parallax-layer="${layerObj.layer}"]`),
          { yPercent: layerObj.yPercent, ease: "none" },
          idx === 0 ? undefined : "<",
        );
      });
    }, root);

    gsap.ticker.lagSmoothing(0);
    const onScroll = () => ScrollTrigger.update();
    window.addEventListener("scroll", onScroll, { passive: true });

    return () => {
      window.removeEventListener("scroll", onScroll);
      ctx.revert();
    };
  }, []);

  return (
    <div ref={parallaxRef} className={cn("relative w-full", className)}>
      <section data-parallax-layers className="relative h-[200vh] w-full">
        <div className="sticky top-0 h-screen w-full overflow-hidden bg-[#101820]">
          {/* 1 — sky */}
          <img
            data-parallax-layer="1"
            src={sky}
            alt=""
            aria-hidden
            width={1920}
            height={1080}
            className="absolute inset-0 h-full w-full scale-110 object-cover"
          />

          {/* 2 — mountain */}
          <img
            data-parallax-layer="2"
            src={mountain}
            alt=""
            aria-hidden
            width={1920}
            height={1080}
            loading="lazy"
            className="absolute inset-x-0 bottom-[14%] h-[60%] w-full object-contain object-bottom"
          />

          {/* 3 — title */}
          <div
            data-parallax-layer="3"
            className="absolute inset-0 flex items-center justify-center px-5"
          >
            <h2 className="max-w-[92vw] text-center text-[10.5vw] leading-[0.82] font-black tracking-[-0.04em] text-balance text-white uppercase">
              {title}
            </h2>
          </div>

          {/* 4 — figure + ground */}
          <div data-parallax-layer="4" className="absolute inset-0">
            {/* dark ridge the figure stands on */}
            <div
              className="absolute inset-x-0 bottom-0 h-[18%]"
              style={{
                background:
                  "radial-gradient(120% 160% at 50% 100%, #131a21 0%, #0b0f14 60%, #080b0f 100%)",
                clipPath: "ellipse(78% 100% at 50% 100%)",
              }}
            />
            <img
              src={figure}
              alt="A person standing on a ridge looking at a mountain"
              width={191}
              height={597}
              loading="lazy"
              className="absolute bottom-[16%] left-1/2 h-[17%] w-auto -translate-x-1/2 object-contain"
            />
          </div>

          {caption ? (
            <p className="label-eyebrow absolute inset-x-0 bottom-6 z-10 text-center text-white/70">
              {caption}
            </p>
          ) : null}

          <div className="grain-overlay-soft" />
        </div>
      </section>
    </div>
  );
}
