import { Link, useRouterState } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";
import { motion } from "motion/react";

/** The persistent pill CTA that floats above the scroll on every page. */
export function FloatingCta() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const target = pathname === "/title" ? "/monitor" : "/title";
  const label = pathname === "/title" ? "Monitor a post" : "Analyze a title";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center"
    >
      <Link
        to={target}
        className="pointer-events-auto group flex items-center gap-3 rounded-full bg-background/95 py-2 pr-2 pl-5 text-sm font-medium shadow-[0_10px_40px_-12px_rgba(0,0,0,0.45)] backdrop-blur transition-transform duration-300 hover:scale-[1.03]"
      >
        {label}
        <span className="bg-ink text-ink-foreground flex size-8 items-center justify-center rounded-full transition-transform duration-300 group-hover:rotate-45">
          <ArrowUpRight className="size-4" />
        </span>
      </Link>
    </motion.div>
  );
}
