import {
  CircleCheck,
  CircleHelp,
  RotateCcw,
  Sparkles,
  Target,
  Trophy,
  Zap,
} from "lucide-react";
import type { AppState, Rating } from "./types";
import { dayKey, ratingLabels } from "./utils";
import "./study-feedback.css";

/** One item counts once per day, even when it needs another review. */
export function studyProgress(state: AppState, day = dayKey()) {
  const learned = new Set([
    ...state.events
      .filter((event) => event.day === day)
      .map((event) => `problem:${event.problemId}`),
    ...state.knowledgeEvents
      .filter((event) => event.day === day)
      .map((event) => `knowledge:${event.itemId}`),
  ]);
  return {
    completed: learned.size,
    goal: Math.max(1, state.settings.dailyGoal),
  };
}

export function StudyProgress({ state }: { state: AppState }) {
  const { completed, goal } = studyProgress(state);
  const achieved = completed >= goal;
  return (
    <section
      className={`study-progress ${achieved ? "is-complete" : ""}`}
      aria-label="今日学习进度"
    >
      <span className="study-progress-icon" aria-hidden="true">
        {achieved ? <Trophy size={19} /> : <Target size={19} />}
      </span>
      <div className="study-progress-main">
        <div className="study-progress-label">
          <strong>{achieved ? "今日目标已达成" : "每天一点，慢慢变强"}</strong>
          <span>
            {completed} / {goal}
            <small> 项</small>
          </span>
        </div>
        <div
          className="study-progress-track"
          role="progressbar"
          aria-label="今日学习目标"
          aria-valuemin={0}
          aria-valuemax={goal}
          aria-valuenow={Math.min(completed, goal)}
          aria-valuetext={`今天已学习 ${completed} 项，目标 ${goal} 项`}
        >
          <span
            style={{ width: `${Math.min(100, (completed / goal) * 100)}%` }}
          />
        </div>
      </div>
    </section>
  );
}

export interface ConfirmedStudy {
  rating: Rating;
  due: string;
  goalReached: boolean;
  completed: number;
}

export function confirmedStudy(
  before: AppState,
  after: AppState,
  rating: Rating,
  due: string,
  day = dayKey(),
): ConfirmedStudy {
  const previous = studyProgress(before, day);
  const current = studyProgress(after, day);
  return {
    rating,
    due,
    completed: current.completed,
    goalReached:
      previous.completed < current.goal && current.completed >= current.goal,
  };
}

export function RatingSymbol({ rating }: { rating: Rating }) {
  const Icon = {
    again: RotateCcw,
    hard: CircleHelp,
    good: CircleCheck,
    easy: Zap,
  }[rating];
  return <Icon className="study-rating-symbol" size={18} aria-hidden="true" />;
}

export function StudyFeedback({ feedback }: { feedback: ConfirmedStudy }) {
  return (
    <div
      className={`study-confirmed ${feedback.goalReached ? "goal-reached" : ""}`}
      role="status"
      aria-live="polite"
    >
      <span className="study-confirmed-icon" aria-hidden="true">
        {feedback.goalReached ? (
          <Trophy size={24} />
        ) : (
          <CircleCheck size={23} />
        )}
      </span>
      <div className="study-confirmed-copy">
        <strong>
          {feedback.goalReached ? "今日目标达成！" : "这次学习，记下啦！"}
        </strong>
        <span>
          {feedback.goalReached
            ? `今天已学习 ${feedback.completed} 项，每一步都算数。`
            : `${ratingLabels[feedback.rating]} · ${feedback.due}`}
        </span>
      </div>
      {feedback.goalReached && (
        <Sparkles className="study-celebration" size={24} aria-hidden="true" />
      )}
    </div>
  );
}
