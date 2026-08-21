/**
 * Single HTTP entry point for the FastAPI backend.
 * Base URL comes from VITE_API_URL — never hardcode a host in components.
 */

export const API_URL = (import.meta.env["VITE_API_URL"] ?? "").replace(/\/$/, "");

/** Optional dev-mode key. Do not ship a real server secret in a public build. */
const API_KEY = import.meta.env["VITE_API_KEY"] ?? "";

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export class ApiNotConfiguredError extends Error {
  constructor() {
    super(
      "No API endpoint configured. Set VITE_API_URL to your FastAPI base URL (e.g. http://localhost:8000).",
    );
    this.name = "ApiNotConfiguredError";
  }
}

function humanMessage(status: number, detail: unknown): string {
  const detailText =
    typeof detail === "string"
      ? detail
      : detail && typeof detail === "object" && "detail" in (detail as object)
        ? String((detail as { detail: unknown }).detail)
        : "";

  switch (status) {
    case 400:
      return detailText || "That request wasn't valid. Check the values and try again.";
    case 401:
    case 403:
      return "The API rejected this request — an API key is required or invalid.";
    case 404:
      return detailText || "Not found. The backend has no data for that request yet.";
    case 422:
      return detailText || "The backend couldn't process that input. Check the format.";
    case 429:
      return "Too many requests. Wait a moment before trying again.";
    case 503:
      return "An upstream data source is unavailable right now. Try again shortly.";
    default:
      if (status >= 500) return "The intelligence service failed to respond. Try again shortly.";
      return detailText || `Request failed (${status}).`;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "DELETE" | undefined;
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined> | undefined;
  signal?: AbortSignal | undefined;
};

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (!API_URL) throw new ApiNotConfiguredError();

  const { method = "GET", body, query, signal } = options;

  const url = new URL(`${API_URL}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
    }
  }

  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (API_KEY) headers["X-API-Key"] = API_KEY;

  let response: Response;
  try {
    const init: RequestInit = { method, headers };
    if (body !== undefined) init.body = JSON.stringify(body);
    if (signal) init.signal = signal;
    response = await fetch(url.toString(), init);
  } catch {
    throw new ApiError(
      "Can't reach the intelligence service. Check that the API is running and allows this origin.",
      0,
    );
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text().catch(() => "");
    }
    throw new ApiError(humanMessage(response.status, detail), response.status, detail);
  }

  if (response.status === 204) return undefined as T;

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError("The API returned a response the app couldn't read.", response.status);
  }
}

export const apiConfigured = () => Boolean(API_URL);
