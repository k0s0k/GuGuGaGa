import type { AppState, Problem } from "./types";

/** A read-only view lets the existing calendar and planner show both kinds of learning.
 * Synthetic negative IDs never leave this module's UI projection or reach persistence.
 */
export function knowledgeProjection(problems: Problem[], state: AppState) {
  const ids = Object.keys(state.knowledge || {}).sort();
  const reverse = new Map<number, string>();
  const forward = new Map<string, number>();
  const knowledge = ids.map((id, index): Problem => {
    const item = state.knowledge[id];
    const number = -index - 1;
    reverse.set(number, id);
    forward.set(id, number);
    return {
      id: number,
      knowledgeId: id,
      title: item.title,
      slug: "",
      difficulty: { qa: "问答", cloze: "填空", procedure: "实践" }[item.kind],
      category: state.decks[item.deckId]?.title || "我的知识库",
      approach: item.tags.join(" · "),
      time: "",
      space: "",
      order: index + 1,
    };
  });
  const cards = { ...state.cards };
  for (const [id, card] of Object.entries(state.knowledgeCards || {})) {
    const number = forward.get(id);
    if (number !== undefined) cards[number] = card;
  }
  const events = [
    ...state.events.map((e) => ({ ...e, eventId: `problem:${e.eventId}` })),
    ...(state.knowledgeEvents || [])
      .filter((e) => forward.has(e.itemId))
      .map((e) => ({
        ...e,
        eventId: `knowledge:${e.eventId}`,
        problemId: forward.get(e.itemId)!,
      })),
  ].sort((a, b) => a.time.localeCompare(b.time));
  const combined: AppState = {
    ...state,
    cards,
    events,
    favorites: [
      ...state.favorites,
      ...(state.knowledgeFavorites || [])
        .filter((id) => forward.has(id))
        .map((id) => forward.get(id)!),
    ],
  };
  const activeKnowledge = knowledge.filter(
    (p) => !state.knowledge[p.knowledgeId!].archived,
  );
  return {
    all: [...problems, ...knowledge],
    active: [...activeKnowledge, ...problems],
    planned: [
      ...activeKnowledge,
      ...(state.settings.includeHot100 === false ? [] : problems),
    ],
    state: combined,
    reverse,
  };
}
