import { Link } from "@tanstack/react-router";
import { API_URL } from "@/api/client";

export function Footer() {
  return (
    <footer className="surface-ink relative overflow-hidden">
      <div className="mx-auto max-w-[1500px] px-5 pt-24 pb-28 md:px-8">
        <p className="display-hero text-ink-foreground/90">
          Post <span className="serif-accent">deliberately</span>
        </p>

        <div className="border-ink-border mt-16 grid gap-10 border-t pt-8 md:grid-cols-4">
          <div>
            <p className="label-eyebrow text-ink-muted">Workflows</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link to="/title">Title intelligence</Link>
              </li>
              <li>
                <Link to="/monitor">Live monitor</Link>
              </li>
              <li>
                <Link to="/trends">Topic intelligence</Link>
              </li>
              <li>
                <Link to="/research">Research</Link>
              </li>
            </ul>
          </div>

          <div>
            <p className="label-eyebrow text-ink-muted">Service</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link to="/system">System status</Link>
              </li>
              <li className="text-ink-muted break-all">{API_URL || "VITE_API_URL not set"}</li>
            </ul>
          </div>

          <div className="md:col-span-2 md:justify-self-end md:text-right">
            <p className="label-eyebrow text-ink-muted">Method</p>
            <p className="mt-3 max-w-sm text-sm leading-relaxed md:ml-auto">
              Every number on this site is computed by the FastAPI intelligence service — ML
              inference, TF-IDF matching, feed aggregation. The interface only asks and renders.
            </p>
          </div>
        </div>

        <div className="text-ink-muted label-eyebrow mt-14 flex flex-wrap justify-between gap-4">
          <span>Hacker News virality intelligence</span>
          <span>Interface layer only — no client-side modelling</span>
        </div>
      </div>
      <div className="grain-overlay" />
    </footer>
  );
}
