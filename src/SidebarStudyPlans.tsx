import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  BookOpen,
  Folder,
  LoaderCircle,
  MoreHorizontal,
  Plus,
  Search,
  X,
} from "lucide-react";
import type { AppState, Problem } from "./types";
import { studyDeckIds } from "./knowledgeProjection";
import "./study-plans.css";

interface Props {
  state: AppState;
  problems: Problem[];
  mutate: (payload: unknown) => Promise<AppState>;
  notify: (message: string) => void;
  onHot100: () => void;
  onDeck: (id: string) => void;
  onKnowledge: () => void;
}

export default function SidebarStudyPlans(props: Props) {
  const { state, problems, onHot100, onDeck } = props;
  const [editing, setEditing] = useState(false);
  const decks = studyDeckIds(state).map((id) => state.decks[id]);
  const items = Object.values(state.knowledge).filter((item) => !item.archived);
  const hot100 = state.settings.includeHot100 !== false;
  const learnedProblems = problems.filter(
    (problem) => state.cards[problem.id],
  ).length;
  return (
    <section
      className="sidebar-section sidebar-study-plans"
      aria-label="我的学习计划"
    >
      <div className="nav-label">
        我的学习计划
        <button
          className="icon-btn study-plan-manager"
          aria-label="管理学习计划"
          title="管理学习计划"
          aria-haspopup="dialog"
          onClick={() => setEditing(true)}
        >
          <MoreHorizontal size={17} />
        </button>
      </div>
      {hot100 && (
        <PlanEntry
          title="LeetCode Hot 100"
          learned={learnedProblems}
          total={problems.length}
          onClick={onHot100}
        />
      )}
      {decks.map((deck) => {
        const records = items.filter((item) => item.deckId === deck.id);
        return (
          <PlanEntry
            key={deck.id}
            title={deck.title}
            learned={
              records.filter((item) => state.knowledgeCards[item.id]).length
            }
            total={records.length}
            knowledge
            onClick={() => onDeck(deck.id)}
          />
        );
      })}
      {!hot100 && !decks.length && (
        <p className="study-plan-empty">选择想学的内容，开启下一段旅程。</p>
      )}
      {!decks.length && (
        <button className="study-plan-add" onClick={() => setEditing(true)}>
          <Plus size={14} />
          添加知识库
        </button>
      )}
      {editing && <PlanDialog {...props} close={() => setEditing(false)} />}
    </section>
  );
}

function PlanEntry({
  title,
  learned,
  total,
  knowledge = false,
  onClick,
}: {
  title: string;
  learned: number;
  total: number;
  knowledge?: boolean;
  onClick: () => void;
}) {
  return (
    <div className="study-plan-entry">
      <button
        className="plan-link"
        title={title}
        aria-label={`打开学习计划：${title}`}
        onClick={onClick}
      >
        {knowledge ? <BookOpen size={16} /> : <Folder size={16} />}
        <span>{title}</span>
      </button>
      <div
        className="sidebar-progress"
        role="progressbar"
        aria-label={`${title}学习进度`}
        aria-valuemin={0}
        aria-valuemax={Math.max(1, total)}
        aria-valuenow={learned}
        aria-valuetext={`已学习 ${learned} / ${total} 项`}
      >
        <span
          style={{
            width: `${total ? Math.min(100, (learned / total) * 100) : 0}%`,
          }}
        />
      </div>
      <div className="sidebar-progress-label">
        <span>{total ? "持续积累，直到掌握" : "等待加入知识点"}</span>
        <span>
          {learned}/{total}
        </span>
      </div>
    </div>
  );
}

function PlanDialog({
  state,
  mutate,
  notify,
  onKnowledge,
  close,
}: Props & { close: () => void }) {
  const [selected, setSelected] = useState(() => new Set(studyDeckIds(state)));
  const [hot100, setHot100] = useState(state.settings.includeHot100 !== false);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const inFlight = useRef(false);
  const mounted = useRef(true);
  const titleId = useId();
  const descriptionId = useId();
  const decks = Object.values(state.decks);
  const visible = decks.filter((deck) =>
    `${deck.title} ${deck.description}`
      .toLowerCase()
      .includes(search.trim().toLowerCase()),
  );
  const counts = new Map<string, number>();
  for (const item of Object.values(state.knowledge)) {
    if (!item.archived)
      counts.set(item.deckId, (counts.get(item.deckId) ?? 0) + 1);
  }
  useEffect(() => {
    mounted.current = true;
    const element = dialog.current;
    element?.showModal();
    return () => {
      mounted.current = false;
      if (element?.open) element.close();
    };
  }, []);
  const save = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      await mutate({
        type: "settings",
        settings: {
          studyDeckIds: decks
            .filter((deck) => selected.has(deck.id))
            .map((deck) => deck.id),
          includeHot100: hot100,
        },
      });
      notify("学习计划已保存");
      if (mounted.current) close();
    } catch (reason) {
      if (mounted.current)
        setError(
          reason instanceof Error
            ? reason.message
            : "学习计划保存失败，请重试。",
        );
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  };
  return createPortal(
    <dialog
      ref={dialog}
      className="study-plan-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      onKeyDown={(event) => {
        if (event.key === "Escape") event.stopPropagation();
      }}
      onCancel={(event) => {
        event.preventDefault();
        if (!inFlight.current) close();
      }}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <div className="study-plan-dialog-heading">
          <div>
            <span className="eyebrow">LEARN AT YOUR OWN PACE</span>
            <h2 id={titleId}>我的学习计划</h2>
          </div>
          <button
            type="button"
            className="icon-btn"
            disabled={busy}
            aria-label="关闭学习计划"
            onClick={close}
          >
            <X size={20} />
          </button>
        </div>
        <p id={descriptionId} className="study-plan-description">
          选择知识库，加入每日学习与到期复习。
        </p>
        <label className="study-plan-choice built-in">
          <input
            type="checkbox"
            aria-label="LeetCode Hot 100"
            checked={hot100}
            disabled={busy}
            onChange={(event) => setHot100(event.target.checked)}
          />
          <Folder size={20} aria-hidden="true" />
          <span>
            <strong>LeetCode Hot 100</strong>
            <small>内置题库 · Python / C++</small>
          </span>
        </label>
        <div className="study-plan-deck-heading">
          <strong>我的知识库</strong>
          <span>已选择 {selected.size} 个</span>
        </div>
        {decks.length > 5 && (
          <label className="study-plan-search">
            <Search size={16} aria-hidden="true" />
            <input
              aria-label="搜索计划知识库"
              placeholder="搜索知识库"
              value={search}
              disabled={busy}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        )}
        <div className="study-plan-choices">
          {visible.map((deck) => (
            <label className="study-plan-choice" key={deck.id}>
              <input
                type="checkbox"
                aria-label={deck.title}
                checked={selected.has(deck.id)}
                disabled={busy}
                onChange={(event) =>
                  setSelected((current) => {
                    const next = new Set(current);
                    if (event.target.checked) next.add(deck.id);
                    else next.delete(deck.id);
                    return next;
                  })
                }
              />
              <BookOpen size={20} aria-hidden="true" />
              <span>
                <strong>{deck.title}</strong>
                <small>
                  {counts.get(deck.id) ?? 0} 个知识点
                  {deck.description ? ` · ${deck.description}` : ""}
                </small>
              </span>
            </label>
          ))}
          {!decks.length && (
            <div className="study-plan-dialog-empty">
              <BookOpen size={28} />
              <p>还没有自己的知识库</p>
              <button
                type="button"
                className="text-button"
                disabled={busy}
                onClick={() => {
                  close();
                  onKnowledge();
                }}
              >
                前往创建知识库
              </button>
            </div>
          )}
          {decks.length > 0 && !visible.length && (
            <p className="study-plan-empty">没有找到匹配的知识库。</p>
          )}
        </div>
        <p className="study-plan-hint">
          取消勾选会保留知识库、笔记和学习记录。
        </p>
        {error && (
          <p className="knowledge-error" role="alert">
            {error}
          </p>
        )}
        <div className="study-plan-dialog-actions">
          <button
            className="secondary"
            type="button"
            disabled={busy}
            onClick={close}
          >
            取消
          </button>
          <button className="primary" disabled={busy} aria-busy={busy}>
            {busy && (
              <LoaderCircle size={16} className="spin" aria-hidden="true" />
            )}
            {busy ? "保存中…" : "保存学习计划"}
          </button>
        </div>
      </form>
    </dialog>,
    document.body,
  );
}
