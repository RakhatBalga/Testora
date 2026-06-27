const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const AUTH_TOKEN_KEY = "testora.auth.token";
const AUTH_USERNAME_KEY = "testora.auth.username";
const LEGACY_TOKEN_KEY = "token";
const LEGACY_USERNAME_KEY = "username";

export function mediaUrl(path: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  return `${API_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

function browserSessionStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage;
}

export function getStoredAuthToken(): string | null {
  const storage = browserSessionStorage();
  if (!storage) return null;

  const token = storage.getItem(AUTH_TOKEN_KEY);
  if (token) return token;

  const legacy = localStorage.getItem(LEGACY_TOKEN_KEY);
  if (!legacy) return null;
  storage.setItem(AUTH_TOKEN_KEY, legacy);
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  return legacy;
}

export function getStoredUsername(): string | null {
  const storage = browserSessionStorage();
  if (!storage) return null;

  const username = storage.getItem(AUTH_USERNAME_KEY);
  if (username) return username;

  const legacy = localStorage.getItem(LEGACY_USERNAME_KEY);
  if (!legacy) return null;
  storage.setItem(AUTH_USERNAME_KEY, legacy);
  localStorage.removeItem(LEGACY_USERNAME_KEY);
  return legacy;
}

export function storeAuth(token: string, username: string): void {
  const storage = browserSessionStorage();
  if (!storage) return;
  storage.setItem(AUTH_TOKEN_KEY, token);
  storage.setItem(AUTH_USERNAME_KEY, username);
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  localStorage.removeItem(LEGACY_USERNAME_KEY);
}

export function clearStoredAuth(): void {
  const storage = browserSessionStorage();
  storage?.removeItem(AUTH_TOKEN_KEY);
  storage?.removeItem(AUTH_USERNAME_KEY);
  if (typeof window === "undefined") return;
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  localStorage.removeItem(LEGACY_USERNAME_KEY);
}

export type Test = {
  id: number;
  title: string;
  test_type: string;
  description: string | null;
  duration_minutes: number;
  difficulty?: string | null;
  question_count?: number;
};

export type QuestionType =
  | "single_choice"
  | "multiple_choice"
  | "true_false_notgiven"
  | "yes_no_not_given"
  | "matching"
  | "matching_headings"
  | "matching_information"
  | "sentence_completion"
  | "summary_completion"
  | "fill_blank"
  | "short_answer";

export type EvidenceSpan = {
  paragraph: number;
  text: string;
};

export type Question = {
  id: number;
  text: string;
  question_type: QuestionType;
  options: string[] | null;
  order: number;
  /** Where the answer is supported in the passage (Reading Review highlight). */
  evidence?: EvidenceSpan[] | null;
};

export type Section = {
  id: number;
  order: number;
  title: string;
  instructions: string | null;
  passage: string | null;
  audio_url: string | null;
  questions: Question[];
};

export type TestDetail = Test & {
  sections: Section[];
};

export type AnswerResult = {
  question_id: number;
  text: string;
  question_type: QuestionType;
  user_answer: string | null;
  correct_answer: string;
  is_correct: boolean;
  marked_for_review: boolean;
  explanation?: string | null;
};

export type BreakdownItem = {
  question_type: QuestionType;
  label: string;
  correct: number;
  total: number;
  accuracy: number;
};

export type AttemptResult = {
  id: number;
  test_id: number;
  test_title: string;
  test_type: string;
  score: number;
  total: number;
  band: number | null;
  correct: number;
  incorrect: number;
  accuracy: number;
  duration_seconds: number | null;
  breakdown: BreakdownItem[];
  created_at: string;
  answers: AnswerResult[];
};

export type AttemptSummary = {
  id: number;
  test_id: number;
  test_title: string;
  test_type: string;
  score: number;
  total: number;
  band: number | null;
  created_at: string;
};

export type AnswerValue = string | string[] | null;

export type RoadmapStep = {
  target_band: number;
  actions: string[];
};

export type Feedback = {
  band: number;
  criteria: Record<string, number>;
  summary: string;
  suggestions: string[];
  // Two-stage coaching extras (optional — older submissions omit them).
  criteria_notes?: Record<string, string>;
  strengths?: string[];
  weaknesses?: string[];
  actions?: string[];
  roadmap?: RoadmapStep[];
  why_not_higher_band?: string;
};

export type UserProfile = {
  username: string;
  target_band: number;
};

export type WritingTask = {
  id: number;
  task_type: number;
  title: string;
  prompt: string;
  image_url: string | null;
  visual_data: WritingVisualData | null;
  min_words: number;
  duration_minutes: number;
};

export type WritingVisualSeries = {
  name: string;
  values: number[];
};

export type WritingVisualData = {
  kind: "line" | "bar" | "table" | "pie" | "process" | "map";
  title?: string;
  unit?: string;
  categories?: string[];
  series?: WritingVisualSeries[];
  columns?: string[];
  rows?: (string | number)[][];
  charts?: { title: string; values: { name: string; value: number }[] }[];
  steps?: string[];
  before?: string[];
  after?: string[];
};

export type WritingSubmission = {
  id: number;
  task_id: number;
  task_title: string;
  task_prompt: string;
  text: string;
  word_count: number;
  status: string;
  band: number | null;
  feedback: Feedback | null;
  created_at: string;
};

export type WritingSubmissionSummary = {
  id: number;
  task_id: number;
  task_title: string;
  word_count: number;
  status: string;
  band: number | null;
  created_at: string;
};

export type SpeakingTask = {
  id: number;
  part: number;
  questions: string[];
  prep_seconds: number;
  speak_seconds: number;
};

export type SpeakingSubmission = {
  id: number;
  task_id: number;
  task_part: number;
  questions: string[];
  audio_url: string;
  transcript: string | null;
  band: number | null;
  feedback: Feedback | null;
  created_at: string;
};

export type SpeakingSubmissionSummary = {
  id: number;
  task_id: number;
  task_part: number;
  audio_url: string;
  band: number | null;
  created_at: string;
};

/* ----------------------------- Analytics ------------------------------- */

export type Weakness = {
  skill: string;
  category: string;
  subskill: string;
  label: string;
  score: number; // 0..1 intensity
  frequency: number;
  avg_severity: number;
  recurring: boolean;
};

export type Blocker = {
  skill: string;
  criterion: string;
  band_cap: number;
  explanation: string;
  fix_href: string;
};

export type BandGapResult = {
  current: number | null;
  target: number;
  gap: number | null;
  per_skill: Record<string, number>;
  lowest_skill: string | null;
  has_data: boolean;
};

export type BandTrajectoryPoint = {
  label: string;
  band: number;
};

export type BandTrajectoryResult = {
  points: BandTrajectoryPoint[];
  delta: number | null;
  has_data: boolean;
};

export type WeeklyWeakest = {
  has_data: boolean;
  skill: "writing" | "speaking" | "reading" | "listening" | null;
  band: number | null;
  attempts: number;
  days: number;
};

export type Streak = {
  current_streak: number;
  active_today: boolean;
};

export type BlockerHistoryPoint = {
  label: string;
  blocker: string;
  skill: string;
  changed: boolean;
};

export type BlockerHistory = {
  has_data: boolean;
  history: BlockerHistoryPoint[];
  note: string | null;
};

export type DailyPlanTask = {
  id: string;
  title: string;
  detail: string;
  skill: string | null;
  href: string;
  source: "blocker" | "band_gap" | "weakness" | "last_activity" | "cold_start";
  estimated_minutes: number;
};

export type DailyPlan = {
  generated_for: string;
  has_data: boolean;
  plan: DailyPlanTask[];
};

export type ProgressCriterion = {
  name: string;
  from: number;
  to: number;
  delta: number;
  direction: "up" | "down" | "none";
};

export type ProgressMistakeItem = {
  category: string;
  label: string;
  from: number;
  to: number;
};

export type ProgressImpact = {
  skill: string;
  supported: boolean;
  found?: boolean;
  has_previous: boolean;
  previous?: { submission_id: number; band: number | null; created_at: string | null };
  current?: { submission_id: number; band: number | null; created_at: string | null };
  band_delta?: number | null;
  criteria?: ProgressCriterion[];
  mistakes?: {
    resolved: ProgressMistakeItem[];
    improved: ProgressMistakeItem[];
    worsened: ProgressMistakeItem[];
    new: ProgressMistakeItem[];
  };
  blocker?: { from: string | null; to: string | null; changed: boolean };
};

/* ----------------------------- History ---------------------------------- */

export type HistoryItem = {
  id: string;
  skill: "writing" | "speaking" | "reading" | "listening";
  ref_id: number;
  title: string;
  band: number | null;
  score: number | null;
  total: number | null;
  status: string;
  created_at: string | null;
  href: string;
};

export type CompareSide = {
  id: string;
  ref_id: number;
  band: number | null;
  created_at: string | null;
  // Writing/Speaking only
  criteria?: Record<string, number>;
  summary?: string | null;
  // Reading/Listening only
  score?: string | null;
};

export type CriteriaDiffItem = {
  name: string;
  a: number;
  b: number;
  delta: number;
  direction: "up" | "down" | "none";
};

export type MistakeDiffItem = {
  category: string;
  label: string;
  a: number;
  b: number;
};

export type QTypeDiffItem = {
  question_type: string;
  label: string;
  a_accuracy: number;
  b_accuracy: number;
  a_correct: number | null;
  b_correct: number | null;
  a_total: number | null;
  b_total: number | null;
  delta: number;
  direction: "up" | "down" | "none";
};

export type CompareResult = {
  skill: string;
  a: CompareSide;
  b: CompareSide;
  band_delta: number | null;
  // Writing/Speaking
  criteria_diff?: CriteriaDiffItem[];
  mistakes?: {
    resolved: MistakeDiffItem[];
    improved: MistakeDiffItem[];
    worsened: MistakeDiffItem[];
    new: MistakeDiffItem[];
  };
  blocker?: { a: string | null; b: string | null; changed: boolean };
  // Reading/Listening
  question_type_diff?: QTypeDiffItem[];
};

export type Recommendation = {
  id: string;
  title: string;
  reason: string;
  source: "blocker" | "band_gap" | "recurring_mistake" | "question_type" | "inactivity" | "cold_start";
  skill: string | null;
  priority: number;
  estimated_impact: "High" | "Medium" | "Low";
  href: string;
  estimated_minutes: number;
};

export type RecurringMistake = {
  skill: string;
  category: string;
  subskill: string;
  label: string;
  occurrences: number;
  window: number;
  message: string;
};

/**
 * Global handler for an expired/invalid session. Clears stored credentials and
 * bounces the user to /login (preserving where they were) instead of leaving
 * them stuck on a screen full of failed requests. Safe to call repeatedly.
 */
function handleUnauthorized(): void {
  if (typeof window === "undefined") return;
  clearStoredAuth();
  const { pathname, search } = window.location;
  if (pathname !== "/login") {
    const next = encodeURIComponent(pathname + search);
    window.location.assign(`/login?next=${next}`);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Your session has expired. Please sign in again.");
  }
  if (!res.ok) {
    let detail = "Request failed";
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }
  return res.json();
}

async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  const token = getStoredAuthToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    body: formData,
    headers,
  });

  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Your session has expired. Please sign in again.");
  }
  if (!res.ok) {
    let detail = "Request failed";
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }
  return res.json();
}

function requestFormWithProgress<T>(
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
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () => reject(new Error("Upload failed. Check your connection and try again."));
    request.onload = () => {
      if (request.status === 401) {
        handleUnauthorized();
        reject(new Error("Your session has expired. Please sign in again."));
        return;
      }
      if (request.status < 200 || request.status >= 300) {
        reject(new Error(request.response?.detail || "Request failed"));
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

  const res = await fetch(url, {
    headers,
    cache: "no-store",
  });

  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Your session has expired. Please sign in again.");
  }
  if (!res.ok) {
    throw new Error("Recording failed to load.");
  }
  return URL.createObjectURL(await res.blob());
}

function audioFilename(audio: Blob): string {
  if (audio.type.includes("ogg")) return "speaking.ogg";
  if (audio.type.includes("mpeg")) return "speaking.mp3";
  if (audio.type.includes("mp4")) return "speaking.m4a";
  if (audio.type.includes("wav")) return "speaking.wav";
  return "speaking.webm";
}

function queryString(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

export const api = {
  register: (username: string, password: string, target_band = 7.5) =>
    request<{ message: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password, target_band }),
    }),

  login: (username: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  getProfile: () => request<UserProfile>("/auth/me"),

  updateProfile: (target_band: number) =>
    request<UserProfile>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify({ target_band }),
    }),

  listTests: () => request<Test[]>("/tests"),

  getTest: (id: number) => request<TestDetail>(`/tests/${id}`),

  submit: (
    test_id: number,
    answers: { question_id: number; answer: AnswerValue; marked_for_review?: boolean }[],
    duration_seconds?: number
  ) =>
    request<AttemptResult>("/results/submit", {
      method: "POST",
      body: JSON.stringify({ test_id, answers, duration_seconds }),
    }),

  listAttempts: () => request<AttemptSummary[]>("/results"),

  getAttempt: (id: number) => request<AttemptResult>(`/results/${id}`),

  listWritingTasks: () => request<WritingTask[]>("/writing/tasks"),

  getWritingTask: (id: number) => request<WritingTask>(`/writing/tasks/${id}`),

  submitWriting: (task_id: number, text: string) =>
    request<WritingSubmission>("/writing/submit", {
      method: "POST",
      body: JSON.stringify({ task_id, text }),
    }),

  listWritingSubmissions: () =>
    request<WritingSubmissionSummary[]>("/writing/submissions"),

  getWritingSubmission: (id: number) =>
    request<WritingSubmission>(`/writing/submissions/${id}`),

  retryWritingSubmission: (id: number) =>
    request<WritingSubmission>(`/writing/submissions/${id}/retry`, {
      method: "POST",
    }),

  listSpeakingTasks: () => request<SpeakingTask[]>("/speaking/tasks"),

  getSpeakingTask: (id: number) => request<SpeakingTask>(`/speaking/tasks/${id}`),

  submitSpeaking: (task_id: number, audio: Blob, onProgress?: (percent: number) => void) => {
    const formData = new FormData();
    formData.append("task_id", String(task_id));
    formData.append("audio", audio, audioFilename(audio));
    return onProgress
      ? requestFormWithProgress<SpeakingSubmission>("/speaking/submit", formData, onProgress)
      : requestForm<SpeakingSubmission>("/speaking/submit", formData);
  },

  listSpeakingSubmissions: () =>
    request<SpeakingSubmissionSummary[]>("/speaking/submissions"),

  getSpeakingSubmission: (id: number) =>
    request<SpeakingSubmission>(`/speaking/submissions/${id}`),

  getWeaknesses: (limit = 6) =>
    request<{ weaknesses: Weakness[] }>(`/analytics/weaknesses?limit=${limit}`),

  getBlockers: (target?: number) =>
    request<{ blockers: Blocker[] }>(`/analytics/blockers${queryString({ target })}`),

  getBandGap: (target?: number) =>
    request<BandGapResult>(`/analytics/band-gap${queryString({ target })}`),

  getBandTrajectory: () => request<BandTrajectoryResult>("/analytics/band-trajectory"),

  getWeeklyWeakest: () => request<WeeklyWeakest>("/analytics/weekly-weakest"),

  getProgressImpact: (skill: "writing" | "speaking", submissionId: number) =>
    request<ProgressImpact>(`/analytics/progress-impact?skill=${skill}&submission_id=${submissionId}`),

  getDailyPlan: (target?: number, limit = 3) =>
    request<DailyPlan>(`/analytics/daily-plan${queryString({ target, limit })}`),

  getBlockerHistory: () => request<BlockerHistory>("/analytics/blocker-history"),

  getStreak: () => request<Streak>("/analytics/streak"),

  getRecurringMistakes: (limit = 6) =>
    request<{ recurring: RecurringMistake[] }>(`/analytics/recurring-mistakes?limit=${limit}`),

  getRecommendations: (target?: number, limit = 5) =>
    request<{ recommendations: Recommendation[] }>(
      `/analytics/recommendations${queryString({ target, limit })}`
    ),

  getHistory: (skill?: string, sort = "newest") => {
    const params = new URLSearchParams({ sort });
    if (skill) params.set("skill", skill);
    return request<{ items: HistoryItem[]; total: number }>(`/history?${params}`);
  },

  getHistoryItem: (itemId: string) => request<HistoryItem & { feedback?: Feedback | null; breakdown?: BreakdownItem[] }>(`/history/${itemId}`),

  compareHistory: (a: string, b: string) =>
    request<CompareResult>(`/history/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`),
};
