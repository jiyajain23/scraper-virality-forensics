import { createFileRoute } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { PageIntro } from "@/components/site/PageIntro";
import { ErrorState } from "@/components/site/States";
import { useHealth } from "@/hooks/useHealth";
import { triggerCollect } from "@/api/core";
import { API_URL } from "@/api/client";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/system")({
  head: () => ({
    meta: [
      { title: "System — intelligence service status" },
      {
        name: "description",
        content:
          "Liveness, model artifact and authentication status reported by the virality intelligence API, plus manual data collection.",
      },
      { property: "og:title", content: "System — intelligence service status" },
      {
        property: "og:description",
        content: "Liveness, model artifact and auth status reported by the API.",
      },
    ],
  }),
  component: SystemPage,
});

function StatusRow({ label, value, ok }: { label: string; value: string; ok: boolean | null }) {
  return (
    <div className="flex items-center justify-between border-b py-4">
      <div className="flex items-center gap-3">
        <span
          className={cn(
            "size-2 rounded-full",
            ok === true && "bg-rising",
            ok === false && "bg-falling",
            ok === null && "bg-muted-foreground",
          )}
        />
        <span className="label-eyebrow">{label}</span>
      </div>
      <span className="text-muted-foreground text-sm">{value}</span>
    </div>
  );
}

function SystemPage() {
  const health = useHealth();
  const collect = useMutation({ mutationFn: triggerCollect });

  const data = health.data;
  const modelLoaded =
    typeof data?.model_loaded === "boolean"
      ? data.model_loaded
      : data?.model
        ? true
        : null;
  const authEnabled =
    typeof data?.auth_enabled === "boolean"
      ? data.auth_enabled
      : typeof data?.auth === "boolean"
        ? data.auth
        : null;

  return (
    <div className="pb-32">
      <PageIntro
        eyebrow="Service"
        title="System"
        accent="status"
        description="Only statuses the /health endpoint actually reports are shown here. Everything else stays out of the interface."
      />

      <section className="mx-auto max-w-[1500px] px-5 md:px-8">
        <div className="rule-top grid gap-16 pt-8 md:grid-cols-2">
          <div>
            <p className="label-eyebrow text-muted-foreground">Reported status</p>
            <div className="mt-4">
              {health.isError ? (
                <ErrorState error={health.error} onRetry={() => health.refetch()} />
              ) : (
                <>
                  <StatusRow
                    label="API"
                    value={health.isPending ? "checking…" : (data?.status ?? "unknown")}
                    ok={health.isPending ? null : Boolean(data?.status)}
                  />
                  <StatusRow
                    label="ML model artifact"
                    value={
                      modelLoaded === null ? "not reported" : modelLoaded ? "loaded" : "missing"
                    }
                    ok={modelLoaded}
                  />
                  <StatusRow
                    label="Authentication"
                    value={
                      authEnabled === null
                        ? typeof data?.auth === "string"
                          ? data.auth
                          : "not reported"
                        : authEnabled
                          ? "API key required"
                          : "developer mode"
                    }
                    ok={authEnabled === null ? null : true}
                  />
                  {data?.version ? (
                    <StatusRow label="Version" value={String(data.version)} ok={true} />
                  ) : null}
                </>
              )}
            </div>
          </div>

          <div>
            <p className="label-eyebrow text-muted-foreground">Configuration</p>
            <div className="mt-4 space-y-4 text-sm">
              <div className="border-b pb-4">
                <p className="label-eyebrow text-muted-foreground">VITE_API_URL</p>
                <p className="mt-2 break-all">{API_URL || "not set"}</p>
              </div>
              <p className="text-muted-foreground leading-relaxed">
                The API base URL is read from the environment at build time. If the browser can't
                reach it, confirm the service is running and that its CORS configuration allows this
                origin.
              </p>
            </div>

            <div className="mt-10 border-t pt-6">
              <p className="label-eyebrow text-muted-foreground">Manual collection</p>
              <p className="text-muted-foreground mt-3 max-w-md text-sm leading-relaxed">
                The service already refreshes data on its own schedule. This triggers real
                collection work on the backend — it is not a page refresh.
              </p>
              <button
                type="button"
                onClick={() => collect.mutate()}
                disabled={collect.isPending}
                className="bg-ink text-ink-foreground mt-5 rounded-full px-5 py-2.5 text-sm font-medium disabled:opacity-50"
              >
                {collect.isPending ? "Collection requested…" : "Trigger collection"}
              </button>
              {collect.isSuccess ? (
                <p className="text-muted-foreground mt-3 text-sm">
                  {collect.data?.status
                    ? `Service reported: ${String(collect.data.status)}`
                    : "Request accepted by the service."}
                </p>
              ) : null}
              {collect.isError ? (
                <p className="text-destructive mt-3 text-sm">{collect.error.message}</p>
              ) : null}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
