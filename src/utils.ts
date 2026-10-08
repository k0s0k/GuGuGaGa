import type { AppState, Card, Problem } from "./types";
export function dayKey(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
export function dateShift(date: Date, days: number) {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}
export function retention(card: Card | undefined, now = new Date()) {
  if (!card) return 0;
  return Math.pow(
    0.9,
    Math.max(
      0,
      (now.getTime() - new Date(card.lastReview).getTime()) / 86400000,
    ) / Math.max(0.1, card.stability),
  );
}
export function isDue(card: Card | undefined, now = new Date()) {
  return !!card && new Date(card.due) <= now;
}
export function streak(state: AppState, now = new Date()) {
  let current = new Date(now);
  let count = 0;
  if (!state.checkins.includes(dayKey(current)))
    current = dateShift(current, -1);
  while (state.checkins.includes(dayKey(current))) {
    count++;
    current = dateShift(current, -1);
  }
  return count;
}
export function dueLabel(card?: Card) {
  if (!card) return "尚未学习";
  const date = new Date(card.due);
  if (date <= new Date()) return "等待复习";
  if (dayKey(date) === dayKey())
    return (
      "今天 " +
      date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
    );
  if (dayKey(date) === dayKey(dateShift(new Date(), 1))) return "明天复习";
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日复习`;
}
export function dailyPlan(
  problems: Problem[],
  state: AppState,
  now = new Date(),
) {
  const due = problems
    .filter((p) => isDue(state.cards[p.id], now))
    .sort(
      (a, b) =>
        new Date(state.cards[a.id].due).getTime() -
        new Date(state.cards[b.id].due).getTime(),
    );
  const learnedToday = state.events.filter(
    (e) => e.day === dayKey(now) && e.kind === "new",
  ).length;
  const next = problems
    .filter((p) => !state.cards[p.id])
    .slice(0, Math.max(0, state.settings.newPerDay - learnedToday));
  return [...due, ...next];
}
export function download(
  name: string,
  content: string,
  type = "application/json",
) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const ratingLabels = {
  again: "忘记了",
  hard: "有点模糊",
  good: "记住了",
  easy: "很熟练",
};
