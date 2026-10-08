export type Language = "python" | "cpp";
export type Mode = "leetcode" | "acm";
export type Rating = "again" | "hard" | "good" | "easy";
export type View =
  | "today"
  | "library"
  | "review"
  | "calendar"
  | "path"
  | "favorites"
  | "settings";
export interface Problem {
  id: number;
  title: string;
  slug: string;
  difficulty: string;
  category: string;
  approach: string;
  time: string;
  space: string;
  order: number;
}
export interface Card {
  stability: number;
  due: string;
  lastReview: string;
  reviews: number;
  lapses: number;
  rating: Rating;
  status: string;
}
export interface StudyEvent {
  eventId: string;
  problemId: number;
  day: string;
  rating: Rating;
  kind: "new" | "review";
  time: string;
  seconds: number;
}
export interface Settings {
  dailyGoal: number;
  newPerDay: number;
  language: Language;
  mode: Mode;
  retention: number;
  theme: "light" | "dark";
}
export interface AppState {
  version: number;
  settings: Settings;
  cards: Record<string, Card>;
  notes: Record<string, string>;
  favorites: number[];
  drafts: Record<string, string>;
  events: StudyEvent[];
  checkins: string[];
}
export interface Capabilities {
  python: { available: boolean; version: string };
  cpp: { available: boolean; compiler: string | null };
}
export interface Example {
  input: unknown[];
  output: unknown;
  explanation: string;
  stdin: string;
}
export interface Detail extends Problem {
  summary: string;
  constraints: string[];
  examples: Example[];
  steps: string[];
  correctness: string;
  pitfalls: string[];
  inputGuide: string[];
  params: { name: string; type: string }[];
  solutions: Record<
    Language,
    Record<Mode, { brief: string; annotated: string }>
  >;
  templates: Record<Language, Record<Mode, string>>;
}
export interface RunCase {
  stdout: string;
  stderr: string;
  exitCode: number;
  elapsedMs: number;
  error: string | null;
  input: string;
  expected: unknown;
  passed: boolean | null;
}
export interface RunResult {
  status: string;
  message: string;
  cases: RunCase[];
}
