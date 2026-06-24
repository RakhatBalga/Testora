const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function mediaUrl(path: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  return `${API_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

export type Test = {
  id: number;
  title: string;
  test_type: string;
  description: string | null;
  duration_minutes: number;
};

export type QuestionType =
  | "single_choice"
  | "multiple_choice"
  | "true_false_notgiven"
  | "matching"
  | "fill_blank"
  | "short_answer";

export type Question = {
  id: number;
  text: string;
  question_type: QuestionType;
  options: string[] | null;
  order: number;
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
};

export type AttemptResult = {
  id: number;
  test_id: number;
  test_title: string;
  test_type: string;
  score: number;
  total: number;
  band: number | null;
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

export type Feedback = {
  band: number;
  criteria: Record<string, number>;
  summary: string;
  suggestions: string[];
};

export type WritingTask = {
  id: number;
  task_type: number;
  title: string;
  prompt: string;
  image_url: string | null;
  min_words: number;
  duration_minutes: number;
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
  /** ISO date of the user's exam, from their goal; null if not set */
  exam_date: string | null;
};

export type Goal = {
  target_band: number;
  current_band: number | null;
  exam_date: string | null;
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

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

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
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    body: formData,
    headers,
  });

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

function audioFilename(audio: Blob): string {
  if (audio.type.includes("ogg")) return "speaking.ogg";
  if (audio.type.includes("mpeg")) return "speaking.mp3";
  if (audio.type.includes("mp4")) return "speaking.m4a";
  if (audio.type.includes("wav")) return "speaking.wav";
  return "speaking.webm";
}

export const api = {
  register: (username: string, password: string) =>
    request<{ message: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  login: (username: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  listTests: () => request<Test[]>("/tests"),

  getTest: (id: number) => request<TestDetail>(`/tests/${id}`),

  submit: (test_id: number, answers: { question_id: number; answer: AnswerValue }[]) =>
    request<AttemptResult>("/results/submit", {
      method: "POST",
      body: JSON.stringify({ test_id, answers }),
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

  listSpeakingTasks: () => request<SpeakingTask[]>("/speaking/tasks"),

  getSpeakingTask: (id: number) => request<SpeakingTask>(`/speaking/tasks/${id}`),

  submitSpeaking: (task_id: number, audio: Blob) => {
    const formData = new FormData();
    formData.append("task_id", String(task_id));
    formData.append("audio", audio, audioFilename(audio));
    return requestForm<SpeakingSubmission>("/speaking/submit", formData);
  },

  listSpeakingSubmissions: () =>
    request<SpeakingSubmissionSummary[]>("/speaking/submissions"),

  getSpeakingSubmission: (id: number) =>
    request<SpeakingSubmission>(`/speaking/submissions/${id}`),

  getWeaknesses: (limit = 6) =>
    request<{ weaknesses: Weakness[] }>(`/analytics/weaknesses?limit=${limit}`),

  // target omitted → backend uses the user's saved goal (falls back to 7.5).
  getBlockers: (target?: number) =>
    request<{ blockers: Blocker[] }>(
      `/analytics/blockers${target != null ? `?target=${target}` : ""}`,
    ),

  getBandGap: (target?: number) =>
    request<BandGapResult>(
      `/analytics/band-gap${target != null ? `?target=${target}` : ""}`,
    ),

  getRecurringMistakes: (limit = 6) =>
    request<{ recurring: RecurringMistake[] }>(`/analytics/recurring-mistakes?limit=${limit}`),

  getGoal: () => request<Goal | null>("/goals"),

  saveGoal: (goal: { target_band: number; exam_date?: string | null; current_band?: number | null }) =>
    request<Goal>("/goals", { method: "POST", body: JSON.stringify(goal) }),
};
