import type { ReactNode } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

/** House easing: long, decelerating settle (matches the reference films). */
const EASE = [0.16, 1, 0.3, 1] as const;

/** Enter-on-scroll wrapper with the house easing curve. */
export function Reveal({
  children,
  className,
  delay = 0,
  y = 34,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  y?: number;
}) {
  return (
    <motion.div
      className={cn(className)}
      initial={{ opacity: 0, y, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-12% 0px -12% 0px" }}
      transition={{ duration: 1.15, delay, ease: EASE }}
      style={{ willChange: "transform, opacity, filter" }}
    >
      {children}
    </motion.div>
  );
}

/** Clip-path curtain reveal used for large media and headline blocks. */
export function CurtainReveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      className={cn("overflow-hidden", className)}
      initial={{ clipPath: "inset(105% 0% 0% 0%)", y: 30 }}
      whileInView={{ clipPath: "inset(-5% 0% 0% 0%)", y: 0 }}
      viewport={{ once: true, margin: "-8% 0px" }}
      transition={{ duration: 1.5, delay, ease: EASE }}
      style={{ willChange: "transform, clip-path" }}
    >
      {children}
    </motion.div>
  );
}

/** Staggered children container — use with <StaggerItem>. */
export function Stagger({
  children,
  className,
  gap = 0.09,
}: {
  children: ReactNode;
  className?: string;
  gap?: number;
}) {
  return (
    <motion.div
      className={cn(className)}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, margin: "-10% 0px" }}
      variants={{ hidden: {}, shown: { transition: { staggerChildren: gap } } }}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className,
  y = 28,
}: {
  children: ReactNode;
  className?: string;
  y?: number;
}) {
  return (
    <motion.div
      className={cn(className)}
      variants={{
        hidden: { opacity: 0, y, filter: "blur(5px)" },
        shown: { opacity: 1, y: 0, filter: "blur(0px)" },
      }}
      transition={{ duration: 1.05, ease: EASE }}
      style={{ willChange: "transform, opacity, filter" }}
    >
      {children}
    </motion.div>
  );
}
