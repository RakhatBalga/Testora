import { API_URL, mediaUrl } from "./config";
import { NetworkError, detailToMessage, handleUnauthorized } from "./errors";
import { getStoredAuthToken } from "./token";

/** Render's free tier needs ~45 s to wake, so one attempt gets a full minute. */
export const REQUEST_TIMEOUT_MS = 60_000;
const RETRY_BACKOFF_MS = [1_000, 2_000];
const RETRY_STATUSES = new Set([502, 503, 504]);

type RequestConfig = {
  /** Per-attempt timeout. */
  timeoutMs?: number;
  /** Extra attempts after a network error/timeout/502-504. GET defaults to 2. */
  retries?: number;
};

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/** Failed to parse/consume a response body: surface the server message when it
 *  sends one, and a friendly "waking up" error for gateway statuses. */
async function failureFor(res: Response): Promise<Error> {
  if (RETRY_STATUSES.has(res.status)) return new NetworkError("unavailable");
  let message = "Request failed";
  try {
    const data = await res.json();
    message = detailToMessage(data.detail);
  } catch {
    // ignore non-JSON error bodies
  }
  return new Error(message);
}

/**
 * One fetch attempt with a timeout. Resolves with the Response, or throws
 * NetworkError (timeout/offline) or the caller's own AbortError.
 */
async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const outer = init.signal;
  const onOuterAbort = () => controller.abort();
  if (outer) {
    if (outer.aborted) controller.abort();
    else outer.addEventListener("abort", onOuterAbort, { once: true });
  }
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (timedOut) throw new NetworkError("timeout");
    if (outer?.aborted) throw error; // deliberate cancel by the caller
    if (error instanceof TypeError) throw new NetworkError("network");
    throw error;
  } finally {
    clearTimeout(timer);
    outer?.removeEventListener("abort", onOuterAbort);
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
  config: RequestConfig = {},
): Promise<T> {
  const token = getStoredAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const method = (options.method ?? "GET").toUpperCase();
  const retries = config.retries ?? (method === "GET" ? RETRY_BACKOFF_MS.length : 0);
  const timeoutMs = config.timeoutMs ?? REQUEST_TIMEOUT_MS;

  for (let attempt = 0; ; attempt++) {
    let res: Response | null = null;
    let failure: Error | null = null;
    try {
      res = await fetchWithTimeout(`${API_URL}${path}`, { ...options, headers }, timeoutMs);
    } catch (error) {
      if (!(error instanceof NetworkError)) throw error;
      failure = error;
    }

    if (res) {
      if (res.status === 401) {
        handleUnauthorized();
        throw new Error("Your session has expired. Please sign in again.");
      }
      if (res.ok) return res.json();
      failure = await failureFor(res);
      if (!(failure instanceof NetworkError)) throw failure;
    }

    if (attempt >= retries) throw failure;
    await sleep(RETRY_BACKOFF_MS[Math.min(attempt, RETRY_BACKOFF_MS.length - 1)]);
  }
}

export async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  const token = getStoredAuthToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetchWithTimeout(
    `${API_URL}${path}`,
    { method: "POST", body: formData, headers },
    120_000,
  );

  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Your session has expired. Please sign in again.");
  }
  if (!res.ok) throw await failureFor(res);
  return res.json();
}

export function requestFormWithProgress<T>(
  path: string,
  formData: FormData,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${API_URL}${path}`);
    const token = getStoredAuthToken();
    if (token) request.setRequestHeader("Authorization", `Bearer ${token}`);
    request.responseType = "json";
    // Uploads can be large and the host may be cold; fail instead of hanging at 100%.
    request.timeout = 120_000;
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () => reject(new Error("Upload failed. Check your connection and try again."));
    request.ontimeout = () => reject(new NetworkError("timeout"));
    request.onload = () => {
      if (request.status === 401) {
        handleUnauthorized();
        reject(new Error("Your session has expired. Please sign in again."));
        return;
      }
      if (RETRY_STATUSES.has(request.status)) {
        reject(new NetworkError("unavailable"));
        return;
      }
      if (request.status < 200 || request.status >= 300) {
        reject(new Error(detailToMessage(request.response?.detail)));
        return;
      }
      resolve(request.response as T);
    };
    request.send(formData);
  });
}

export async function fetchAuthenticatedMedia(path: string | null): Promise<string | null> {
  const url = mediaUrl(path);
  if (!url) return null;

  const token = getStoredAuthToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetchWithTimeout(url, { headers, cache: "no-store" }, REQUEST_TIMEOUT_MS);

  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Your session has expired. Please sign in again.");
  }
  if (!res.ok) {
    throw new Error("Recording failed to load.");
  }
  return URL.createObjectURL(await res.blob());
}

export function audioFilename(audio: Blob): string {
  if (audio.type.includes("ogg")) return "speaking.ogg";
  if (audio.type.includes("mpeg")) return "speaking.mp3";
  if (audio.type.includes("mp4")) return "speaking.m4a";
  if (audio.type.includes("wav")) return "speaking.wav";
  return "speaking.webm";
}

export function queryString(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

let warmedUp = false;

/**
 * Wake the free-tier backend while the user is still reading the landing page
 * or typing credentials. Opaque no-cors request: the answer is irrelevant and
 * the response needs no CORS headers. Fires at most once per page load.
 */
export function warmUpServer(): void {
  if (warmedUp || typeof window === "undefined") return;
  warmedUp = true;
  try {
    fetch(`${API_URL}/health/live`, { mode: "no-cors", cache: "no-store" }).catch(() => {});
  } catch {
    /* best effort */
  }
}
