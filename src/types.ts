export type Language = "python" | "cpp";
export type Mode = "leetcode" | "acm";
export type Rating = "again" | "hard" | "good" | "easy";
export type View =
  | "today"
  | "knowledge"
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
  knowledgeId?: string;
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
  includeHot100: boolean;
  studyDeckIds?: string[];
  avatar: string;
  workspaceName: string;
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
  solutions: Record<string, SavedSolution>;
  decks: Record<string, KnowledgeDeck>;
  knowledge: Record<string, KnowledgeItem>;
  knowledgeCards: Record<string, Card>;
  knowledgeNotes: Record<string, string>;
  knowledgeFavorites: string[];
  knowledgeEvents: KnowledgeEvent[];
  stones?: StoneWalletState;
}
export interface StoneWalletState {
  balance: number;
  totalEarned: number;
  totalSpent: number;
  rules: {
    learn: number;
    review: number;
    checkin: number;
    makeup: number;
    makeupWindowDays: number;
  };
  startedOn: string;
  makeups: { day: string; spentAt: string; cost: number }[];
}
export interface SavedSolution {
  brief: string;
  annotated: string;
  explanation: string;
  updatedAt: string;
}
export type KnowledgeKind = "qa" | "cloze" | "procedure";
export interface KnowledgeDeck {
  id: string;
  title: string;
  description: string;
  createdAt: string;
  updatedAt: string;
}
export interface KnowledgeItem {
  id: string;
  deckId: string;
  title: string;
  kind: KnowledgeKind;
  prompt: string;
  answer: string;
  tags: string[];
  source: string;
  archived: boolean;
  createdAt: string;
  updatedAt: string;
}
export interface KnowledgeEvent extends Omit<StudyEvent, "problemId"> {
  itemId: string;
}
export interface KnowledgeDocument {
  format: "coderecall.knowledge";
  version: 1;
  deck: { id?: string; title: string; description?: string };
  items: {
    id?: string;
    title: string;
    kind: KnowledgeKind;
    prompt: string;
    answer: string;
    tags?: string[];
    source?: string;
  }[];
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
