import { Link, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const links = [
  { to: "/", label: "Home" },
  { to: "/overview", label: "Overview" },
  { to: "/title", label: "Title" },
  { to: "/monitor", label: "Monitor" },
  { to: "/trends", label: "Trends" },
  { to: "/research", label: "Research" },
  { to: "/system", label: "System" },
] as const;


export function Nav() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => setOpen(false), [pathname]);

  const onDark = pathname === "/overview";

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-50 transition-colors duration-500",
        scrolled ? "backdrop-blur-md" : "",
        scrolled && !onDark ? "bg-background/80 border-b" : "",
        scrolled && onDark ? "bg-ink/60" : "",
      )}
    >
      <div
        className={cn(
          "mx-auto flex h-14 max-w-[1500px] items-center justify-between px-5 transition-colors duration-500 md:px-8",
          onDark && !scrolled ? "text-ink-foreground" : "text-foreground",
          onDark && scrolled ? "text-ink-foreground" : "",
        )}
      >
        <nav className="hidden items-center gap-6 md:flex">
          {links.slice(0, 4).map((link) => (
            <NavLink key={link.to} to={link.to} label={link.label} active={pathname === link.to} />
          ))}
        </nav>

        <Link to="/" className="label-eyebrow tracking-[0.32em] md:absolute md:left-1/2 md:-translate-x-1/2">
          Virality<span className="opacity-50">Intel</span>
        </Link>

        <div className="hidden items-center gap-6 md:flex">
          {links.slice(4).map((link) => (
            <NavLink key={link.to} to={link.to} label={link.label} active={pathname === link.to} />
          ))}
        </div>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="label-eyebrow md:hidden"
          aria-expanded={open}
        >
          {open ? "Close" : "Menu"}
        </button>
      </div>

      {open ? (
        <div className="surface-ink border-ink-border border-t px-5 py-4 md:hidden">
          <ul className="space-y-3">
            {links.map((link) => (
              <li key={link.to}>
                <Link to={link.to} className="display-lg block">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </header>
  );
}

function NavLink({ to, label, active }: { to: string; label: string; active: boolean }) {
  return (
    <Link
      to={to}
      className={cn(
        "label-eyebrow relative transition-opacity duration-300 hover:opacity-100",
        active ? "opacity-100" : "opacity-55",
      )}
    >
      {label}
      <span
        className={cn(
          "absolute -bottom-1.5 left-0 h-px w-full origin-left bg-current transition-transform duration-500",
          active ? "scale-x-100" : "scale-x-0",
        )}
      />
    </Link>
  );
}
