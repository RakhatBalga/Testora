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
  avatar: string | null;
  target_band: number;
  current_level: number | null;
  current_level_source: string | null;
  exam_date: string | null;
  weekly_study_days: number;
  daily_study_minutes: 15 | 30 | 45 | 60 | 90;
  primary_focus: "writing" | "reading" | "speaking" | "balanced";
  onboarding_completed: boolean;
  native_language: string | null;
};

export type UserProfileUpdate = Partial<Omit<UserProfile, "username" | "current_level_source">>;

// ---- Vocabulary builder ----------------------------------------------------
export type SavedWordEnrichment = {
  meaning?: string;
  part_of_speech?: string;
  synonyms?: string[];
  alternatives?: string[];
  translation?: string;
  example?: string;
};

export type SavedWord = {
  id: number;
  word: string;
  context: string | null;
  source: string | null;
  training: boolean;
  status: "new" | "learning" | "mastered";
  enrichment: SavedWordEnrichment | null;
  enriched: boolean;
  created_at: string | null;
};

export type VocabularyList = {
  items: SavedWord[];
  total: number;
  training_count: number;
  page: number;
  page_size: number;
};

export type VocabQuizQuestion = {
  word: string;
  prompt: string;
  kind: string;
  options: string[];
};

export type DailyQuiz = {
  quiz_date: string | null;
  completed: boolean;
  score: number | null;
  total: number;
  questions: VocabQuizQuestion[];
};

export type QuizResultItem = {
  word: string;
  prompt: string;
  options: string[];
  answer_index: number;
  your_answer: number | null;
  correct: boolean;
  explanation: string;
};

export type QuizResult = { score: number; total: number; results: QuizResultItem[] };

export type DiagnosticState = {
  id: number | null;
  status: "not_started" | "in_progress" | "completed" | "skipped";
  skills: ("writing" | "reading")[];
  writing_submission_id: number | null;
  reading_attempt_id: number | null;
  provisional_level: number | null;
  started_at: string | null;
  completed_at: string | null;
  writing_task_id: number | null;
  reading_test_id: number | null;
};

export type StudyPlanItem = {
  id: number;
  stable_id: string;
  title: string;
  reason: string;
  minutes: number;
  skill: "writing" | "reading";
  action_type: "practice" | "review" | "diagnostic";
  href: string;
  status: "pending" | "completed" | "skipped";
  scheduled_date: string;
  source: { type: string; ref: string | null };
};

export type StudyPlan = {
  week_start: string;
  week_end: string;
  completed: number;
  total: number;
  progress: number;
  items: StudyPlanItem[];
};

export type NotebookItem = {
  id: string;
  source_id: number;
  skill: "writing" | "reading" | "listening";
  status: "new" | "reviewing" | "mastered";
  category: string;
  label: string;
  quote: string | null;
  user_answer: string | null;
  correct_answer: string | null;
  explanation: string | null;
  evidence: EvidenceSpan[] | null;
  source_href: string;
  source_title: string;
  created_at: string;
};

export type ListeningMode = "exam" | "practice";

export type ListeningCatalogItem = {
  id: number;
  title: string;
  description: string | null;
  duration_minutes: number;
  difficulty: string | null;
  question_count: number;
  content_version: string;
  calibration_status: "draft" | "provisional" | "reviewed" | "calibrated" | "retired";
  authorship: string;
};

export type ListeningQuestion = {
  id: number;
  order: number;
  text: string;
  question_type: QuestionType;
  options: string[] | null;
  word_limit: number | null;
};

export type ListeningSection = {
  id: number;
  order: number;
  title: string;
  instructions: string | null;
  audio_url: string | null;
  audio_start: number;
  audio_end: number;
  map_asset: string | null;
  questions: ListeningQuestion[];
};

export type ListeningTest = ListeningCatalogItem & {
  schema_version: "testora.listening-public.v1";
  intro_notice: string;
  sections: ListeningSection[];
};

export type ListeningProgress = {
  content_version: string;
  mode: ListeningMode;
  answers: Record<string, AnswerValue>;
  current_section: number;
  audio_position: number;
  max_audio_position: number;
  status: string;
  updated_at: string;
};

export type ListeningSubmitResult = {
  schema_version: "testora.listening-submit.v1";
  attempt_id: number;
  test_id: number;
  content_version: string;
  mode: ListeningMode;
  score: number;
  total: number;
  band: number | null;
  accuracy: number;
  breakdown: BreakdownItem[];
  created_at: string;
};

export type ListeningReview = Omit<ListeningSubmitResult, "schema_version"> & {
  schema_version: "testora.listening-review.v1";
  test_title: string;
  duration_seconds: number | null;
  sections: {
    id: number;
    order: number;
    title: string;
    transcript_segments: { id: string; speaker: string; text: string; start: number; end: number }[];
  }[];
  answers: {
    question_id: number;
    order: number;
    section_order: number;
    text: string;
    question_type: QuestionType;
    user_answer: string | null;
    correct_answer: string;
    is_correct: boolean;
    explanation: string | null;
    target_skill: string | null;
    evidence: { segment_id: string | null; start: number | null; end: number | null; quote: string }[];
  }[];
};

export type NotebookPage = {
  items: NotebookItem[];
  total: number;
  page: number;
  page_size: number;
};

export type LearningDashboard = {
  profile: {
    target_band: number;
    current_level: number | null;
    current_level_source: string | null;
    exam_date: string | null;
    days_to_exam: number | null;
    onboarding_completed: boolean;
  };
  weekly_plan: StudyPlan;
  today: StudyPlanItem | null;
  weaknesses: {
    writing: { label: string; value: number; href: string } | null;
    reading: { label: string; value: number; href: string } | null;
  };
  recent: {
    id: string;
    skill: "writing" | "reading";
    title: string;
    band: number | null;
    created_at: string;
    href: string;
  }[];
  mistakes: { total: number; new: number; reviewing: number; mastered: number };
  diagnostic: DiagnosticState;
};

export type WritingTask = {
  id: number;
  task_type: number;
  essay_type: string | null;
  title: string;
  prompt: string;
  image_url: string | null;
  visual_data: WritingVisualData | null;
  min_words: number;
  duration_minutes: number;
};

/** Free-tier AI review allowance (writing / speaking). */
export type FreeQuota = {
  limit: number;
  used: number;
  remaining: number;
  exempt: boolean;
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
  improved_text: string | null;
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
