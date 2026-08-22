import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { getHealth } from "@/api/core";
import { apiConfigured } from "@/api/client";

const MAX_ATTEMPTS = 10;      // ~60 s total
const RETRY_DELAY_MS = 6000;

/**
 * Fires a /health ping as soon as the app mounts.
 * If the backend is sleeping (Render free tier), it silently retries
 * every 6 s and shows a dismissible toast so the user knows it's warming up.
 */
export function useWakeBackend() {
  const toastId = useRef<string | number | null>(null);
  const attempt = useRef(0);
  const timer   = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!apiConfigured()) return;

    async function ping() {
      try {
        await getHealth();
        // Backend is up — dismiss the wake-up toast if it was shown
        if (toastId.current !== null) {
          toast.dismiss(toastId.current);
          toast.success("Backend is ready.", { duration: 3000 });
          toastId.current = null;
        }
      } catch {
        attempt.current += 1;

        if (attempt.current === 1) {
          // First failure — show the wake-up notice
          toastId.current = toast.loading("Waking up the backend… this takes ~30 s on the free tier.", {
            duration: Infinity,
          });
        }

        if (attempt.current < MAX_ATTEMPTS) {
          timer.current = setTimeout(ping, RETRY_DELAY_MS);
        } else {
          // Give up — update toast to an error
          if (toastId.current !== null) {
            toast.dismiss(toastId.current);
            toast.error("Backend didn't respond. Check the Render dashboard.", { duration: 10000 });
            toastId.current = null;
          }
        }
      }
    }

    ping();

    return () => {
      if (timer.current) clearTimeout(timer.current);
      if (toastId.current !== null) toast.dismiss(toastId.current);
    };
  }, []);
}
