import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cn } from "@/lib/utils";

type GlassVariant = "paper" | "ink";

export interface GlassCardOwnProps {
  variant?: GlassVariant;
  /** Adds the shared hover lift + border/shadow intensification. */
  interactive?: boolean;
  className?: string;
  children?: ReactNode;
}

/**
 * The single glass-morphism surface used by every card across the site.
 * Blur, borders, inner highlight, shadow and hover lift all live in the
 * `glass-card` / `glass-card-ink` / `glass-card-hover` utilities so the
 * treatment stays identical everywhere.
 */
export function GlassCard<T extends ElementType = "div">({
  as,
  variant = "paper",
  interactive = false,
  className,
  children,
  ...rest
}: GlassCardOwnProps & { as?: T } & Omit<
    ComponentPropsWithoutRef<T>,
    keyof GlassCardOwnProps | "as"
  >) {
  const Component = (as ?? "div") as ElementType;

  return (
    <Component
      className={cn(
        variant === "ink" ? "glass-card-ink" : "glass-card",
        interactive && "glass-card-hover",
        className,
      )}
      {...rest}
    >
      {children}
    </Component>
  );
}

export default GlassCard;
