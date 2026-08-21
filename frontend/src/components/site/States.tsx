import type { ReactNode } from "react";
import { RotateCcw } from "lucide-react";
import { ApiNotConfiguredError } from "@/api/client";
import { cn } from "@/lib/utils";

export function StateShell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "border-border/70 flex min-h-[220px] flex-col items-start justify-center gap-3 rounded-lg border border-dashed px-6 py-10",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <StateShell>
      <p className="display-lg">{title}</p>
      {hint ? <p className="text-muted-foreground max-w-md text-sm">{hint}</p> : null}
    </StateShell>
  );
}

export function LoadingState({ label = "Requesting intelligence" }: { label?: string }) {
  return (
    <StateShell>
      <div className="flex items-center gap-3">
        <span className="bg-accent animate-pulse-dot size-2 rounded-full" />
        <p className="label-eyebrow text-muted-foreground">{label}</p>
      </div>
      <div className="w-full max-w-xl space-y-3 pt-2">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="bg-muted h-3 animate-pulse rounded-full"
            style={{ width: `${90 - i * 22}%`, animationDelay: `${i * 120}ms` }}
          />
        ))}
      </div>
    </StateShell>
  );
}

export function ErrorState({
  error,
  onRetry,
  label = "Retry",
}: {
  error: unknown;
  onRetry?: () => void;
  label?: string;
}) {
  const notConfigured = error instanceof ApiNotConfiguredError;
  const message =
    error instanceof Error ? error.message : "Something went wrong talking to the service.";

  return (
    <StateShell className="border-destructive/40">
      <p className="label-eyebrow text-destructive">
        {notConfigured ? "API not configured" : "Request failed"}
      </p>
      <p className="max-w-xl text-sm leading-relaxed">{message}</p>
      {onRetry && !notConfigured ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-colors hover:bg-secondary"
        >
          <RotateCcw className="size-3.5" />
          {label}
        </button>
      ) : null}
    </StateShell>
  );
}
