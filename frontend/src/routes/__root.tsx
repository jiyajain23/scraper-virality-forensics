import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
} from "@tanstack/react-router";
import { Nav } from "@/components/site/Nav";
import { Footer } from "@/components/site/Footer";
import { FloatingCta } from "@/components/site/FloatingCta";
import { SmoothScroll } from "@/components/motion/SmoothScroll";
import { Toaster } from "@/components/ui/sonner";
import { useWakeBackend } from "@/hooks/useWakeBackend";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="display-hero">404</h1>
        <h2 className="display-lg mt-4">Page not found</h2>
        <p className="text-muted-foreground mt-2 text-sm">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="bg-ink text-ink-foreground inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error("Application error:", error);
  const router = useRouter();

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="display-lg">This page didn't load</h1>
        <p className="text-muted-foreground mt-2 text-sm">
          Something went wrong. You can try refreshing or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="bg-ink text-ink-foreground inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium cursor-pointer"
          >
            Try again
          </button>
          <a
            href="/"
            className="border-input inline-flex items-center justify-center rounded-full border px-5 py-2 text-sm font-medium"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  useWakeBackend();

  return (
    <QueryClientProvider client={queryClient}>
      <SmoothScroll />
      <Nav />
      <main>
        {/* Required: nested routes render here */}
        <Outlet />
      </main>
      <Footer />
      <FloatingCta />
      <Toaster position="bottom-right" richColors />
    </QueryClientProvider>
  );
}
