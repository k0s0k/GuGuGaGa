import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  CSSProperties,
  KeyboardEvent as ReactKeyboardEvent,
  PointerEvent,
} from "react";
import type { EditorView } from "@codemirror/view";
import CodeMirror from "@uiw/react-codemirror";
import { python } from "@codemirror/lang-python";
import { cpp } from "@codemirror/lang-cpp";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  Clock3,
  Code2,
  Copy,
  ExternalLink,
  FileCode2,
  Lightbulb,
  LoaderCircle,
  Maximize2,
  Play,
  RotateCcw,
  Save,
  SlidersHorizontal,
  Sparkles,
  Star,
  Terminal,
  X,
} from "lucide-react";
import { getProblem, runCode } from "./api";
import { Difficulty } from "./App";
import type {
  AppState,
  Capabilities,
  Detail,
  Language,
  Mode,
  Problem,
  Rating,
  RunResult,
} from "./types";
import { dailyPlan, dayKey, download, dueLabel, ratingLabels } from "./utils";
import Markdown from "./Markdown";
import { codeEditingExtensions } from "./editorExtensions";
import {
  confirmedStudy,
  RatingSymbol,
  StudyFeedback,
  StudyProgress,
} from "./StudyFeedback";
import type { ConfirmedStudy } from "./StudyFeedback";
import "./workspace-upgrade.css";
import "./workspace-layout.css";

const workspaceLayoutKey = "gugugaga-workspace-layout-v1";
const defaultWorkspaceLayout = {
  question: true,
  editor: true,
  console: true,
  progress: true,
  questionShare: 44,
  codeShare: 62,
};
type WorkspaceLayout = typeof defaultWorkspaceLayout;
const boundedShare = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

function readWorkspaceLayout(): WorkspaceLayout {
  try {
    const saved: unknown = JSON.parse(
      localStorage.getItem(workspaceLayoutKey) || "null",
    );
    if (!saved || typeof saved !== "object")
      return { ...defaultWorkspaceLayout };
    const data = saved as Record<string, unknown>;
    const layout = { ...defaultWorkspaceLayout };
    for (const name of ["question", "editor", "console", "progress"] as const)
      if (typeof data[name] === "boolean") layout[name] = data[name];
    for (const name of ["questionShare", "codeShare"] as const)
      if (typeof data[name] === "number" && Number.isFinite(data[name]))
        layout[name] = boundedShare(
          data[name],
          name === "questionShare" ? 30 : 35,
          name === "questionShare" ? 65 : 80,
        );
    if (!layout.question && !layout.editor) layout.editor = true;
    return layout;
  } catch {
    return { ...defaultWorkspaceLayout };
  }
}

function WorkspaceSeparator({
  direction,
  value,
  onChange,
}: {
  direction: "columns" | "rows";
  value: number;
  onChange: (value: number) => void;
}) {
  const dragging = useRef<{
    id: number;
    start: number;
    value: number;
    size: number;
  } | null>(null);
  const columns = direction === "columns";
  const min = columns ? 30 : 35;
  const max = columns ? 65 : 80;
  const update = (next: number) =>
    onChange(Math.round(boundedShare(next, min, max)));
  const move = (event: PointerEvent<HTMLDivElement>) => {
    const drag = dragging.current;
    if (!drag || event.pointerId !== drag.id) return;
    update(
      drag.value +
        (((columns ? event.clientX : event.clientY) - drag.start) / drag.size) *
          100,
    );
  };
  const finish = (event: PointerEvent<HTMLDivElement>) => {
    if (dragging.current?.id !== event.pointerId) return;
    dragging.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId))
      event.currentTarget.releasePointerCapture(event.pointerId);
  };
  const keyboard = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    const back = columns ? "ArrowLeft" : "ArrowUp";
    const forward = columns ? "ArrowRight" : "ArrowDown";
    if (![back, forward, "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    update(
      event.key === "Home"
        ? min
        : event.key === "End"
          ? max
          : value + (event.key === back ? -1 : 1) * (event.shiftKey ? 10 : 2),
    );
  };
  return (
    <div
      className={`workspace-resizer ${direction}`}
      role="separator"
      tabIndex={0}
      aria-label={columns ? "调整题目区与代码区宽度" : "调整代码区与运行区高度"}
      aria-orientation={columns ? "vertical" : "horizontal"}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={value}
      aria-valuetext={`${columns ? "题目区" : "代码区"}占 ${value}%`}
      title={
        columns
          ? "拖动调整宽度，或使用左右方向键"
          : "拖动调整高度，或使用上下方向键"
      }
      onKeyDown={keyboard}
      onPointerDown={(event) => {
        if (event.button !== 0) return;
        event.preventDefault();
        const rect = event.currentTarget.parentElement!.getBoundingClientRect();
        dragging.current = {
          id: event.pointerId,
          start: columns ? event.clientX : event.clientY,
          value,
          size: Math.max(1, (columns ? rect.width : rect.height) - 10),
        };
        event.currentTarget.focus();
        event.currentTarget.setPointerCapture(event.pointerId);
      }}
      onPointerMove={move}
      onPointerUp={finish}
      onPointerCancel={finish}
      onLostPointerCapture={() => {
        dragging.current = null;
      }}
    >
      <span />
    </div>
  );
}

interface Props {
  id: number;
  state: AppState;
  capabilities: Capabilities;
  problems: Problem[];
  mutate: (payload: unknown) => Promise<AppState>;
  notify: (message: string) => void;
  onBack: () => void;
  onOpen: (id: number) => void;
}

export default function Workspace({
  id,
  state,
  capabilities,
  problems,
  mutate,
  notify,
  onBack,
  onOpen,
}: Props) {
  const [detail, setDetail] = useState<Detail | null>(null),
    [error, setError] = useState(""),
    [language, setLanguage] = useState<Language>(state.settings.language),
    [mode, setMode] = useState<Mode>(state.settings.mode),
    [tab, setTab] = useState("题目"),
    [noteView, setNoteView] = useState<"edit" | "preview" | "split">("split");
  const [code, setCode] = useState(""),
    [note, setNote] = useState(state.notes[id] || ""),
    [saved, setSaved] = useState(true),
    [running, setRunning] = useState(false),
    [result, setResult] = useState<RunResult | null>(null),
    [caseIndex, setCaseIndex] = useState(0),
    [consoleTab, setConsoleTab] = useState("测试用例"),
    [custom, setCustom] = useState(false),
    [stdin, setStdin] = useState(""),
    [rating, setRating] = useState<Rating | null>(null),
    [ratingBusy, setRatingBusy] = useState(false),
    [confirmReset, setConfirmReset] = useState(false);
  const [layout, setLayout] = useState(readWorkspaceLayout);
  const [narrowLayout, setNarrowLayout] = useState(false);
  const workspaceContainer = useRef<HTMLDivElement>(null);
  const answerEditor = useRef<EditorView | null>(null);
  useEffect(() => {
    const node = workspaceContainer.current;
    if (!node) return;
    const measure = () =>
      setNarrowLayout(node.getBoundingClientRect().width < 600);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [detail]);
  useEffect(() => {
    try {
      localStorage.setItem(workspaceLayoutKey, JSON.stringify(layout));
    } catch {
      /* Layout remains usable when storage is unavailable. */
    }
    const frame = requestAnimationFrame(() =>
      answerEditor.current?.requestMeasure(),
    );
    return () => cancelAnimationFrame(frame);
  }, [layout, narrowLayout]);
  const [feedback, setFeedback] = useState<ConfirmedStudy | null>(null),
    [ratingError, setRatingError] = useState("");
  const draftTimer = useRef<ReturnType<typeof setTimeout> | null>(null),
    noteTimer = useRef<ReturnType<typeof setTimeout> | null>(null),
    pendingDraft = useRef<{
      key: string;
      code: string;
      language: Language;
      mode: Mode;
    } | null>(null),
    pendingNote = useRef<string | null>(null),
    seconds = useRef(0),
    draftCache = useRef<Record<string, string>>({}),
    mount = useRef(true),
    runningRef = useRef(false);
  const key = `${id}:${language}:${mode}`;
  const editorExtensions = useMemo(
    () => [language === "python" ? python() : cpp(), ...codeEditingExtensions],
    [language],
  );
  const pendingRating = useRef<{
    type: "rate";
    problemId: number;
    rating: Rating;
    day: string;
    eventId: string;
    seconds: number;
  } | null>(null);
  const ratingInFlight = useRef(false);
  useEffect(() => {
    let current = true;
    getProblem(id)
      .then((p) => {
        if (current) {
          setDetail(p);
          setStdin(p.examples[0].stdin);
        }
      })
      .catch((e) => {
        if (current) setError(e.message);
      });
    return () => {
      current = false;
    };
  }, [id]);
  useEffect(() => {
    const timer = setInterval(() => {
      if (!document.hidden) seconds.current++;
    }, 1000);
    return () => clearInterval(timer);
  }, []);
  const persistDraft = useCallback(async () => {
    const pending = pendingDraft.current;
    if (!pending) return;
    pendingDraft.current = null;
    try {
      await mutate({
        type: "draft",
        problemId: id,
        language: pending.language,
        mode: pending.mode,
        code: pending.code,
      });
      const cached = localStorage.getItem("coderecall-pending-" + pending.key);
      if (cached === pending.code)
        localStorage.removeItem("coderecall-pending-" + pending.key);
      if (mount.current && !pendingDraft.current) setSaved(true);
    } catch {
      if (mount.current) setSaved(false);
    }
  }, [id, mutate]);
  const persistNote = useCallback(async () => {
    const value = pendingNote.current;
    if (value === null) return;
    pendingNote.current = null;
    try {
      await mutate({ type: "note", problemId: id, text: value });
      if (localStorage.getItem("coderecall-note-" + id) === value)
        localStorage.removeItem("coderecall-note-" + id);
    } catch {
      /* Locally retained until next open. */
    }
  }, [id, mutate]);
  useEffect(() => {
    mount.current = true;
    return () => {
      mount.current = false;
      if (draftTimer.current) clearTimeout(draftTimer.current);
      if (noteTimer.current) clearTimeout(noteTimer.current);
      void persistDraft();
      void persistNote();
    };
  }, [persistDraft, persistNote]);
  useEffect(() => {
    if (!detail) return;
    const cached = localStorage.getItem("coderecall-pending-" + key);
    const value =
      draftCache.current[key] ??
      cached ??
      state.drafts[key] ??
      detail.templates[language][mode];
    setCode(value);
    setResult(null);
    setCaseIndex(0);
    setSaved(cached === null);
    if (cached !== null) {
      pendingDraft.current = { key, code: cached, language, mode };
      void persistDraft();
    }
    // Each mode keeps its own draft; a state update must not reset the live editor.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail, key, language, mode]);
  useEffect(() => {
    const cached = localStorage.getItem("coderecall-note-" + id);
    if (cached !== null) {
      setNote(cached);
      pendingNote.current = cached;
      void persistNote();
    }
  }, [id, persistNote]);
  const updateCode = (value: string) => {
    setCode(value);
    draftCache.current[key] = value;
    setSaved(false);
    localStorage.setItem("coderecall-pending-" + key, value);
    pendingDraft.current = { key, code: value, language, mode };
    if (draftTimer.current) clearTimeout(draftTimer.current);
    draftTimer.current = setTimeout(() => void persistDraft(), 650);
  };
  const updateNote = (value: string) => {
    setNote(value);
    localStorage.setItem("coderecall-note-" + id, value);
    pendingNote.current = value;
    if (noteTimer.current) clearTimeout(noteTimer.current);
    noteTimer.current = setTimeout(() => void persistNote(), 650);
  };
  const switchLanguage = (value: Language) => {
    if (runningRef.current) {
      notify("请等待当前运行结束后再切换语言。");
      return;
    }
    void persistDraft();
    setLanguage(value);
  };
  const switchMode = (value: Mode) => {
    if (runningRef.current) {
      notify("请等待当前运行结束后再切换模式。");
      return;
    }
    void persistDraft();
    setMode(value);
  };
  const run = useCallback(async () => {
    if (runningRef.current) return;
    runningRef.current = true;
    setRunning(true);
    setLayout((current) => ({ ...current, editor: true, console: true }));
    setConsoleTab("运行结果");
    setResult(null);
    setCaseIndex(0);
    try {
      const response = await runCode({
        problemId: id,
        language,
        mode,
        code,
        ...(custom ? { stdin } : {}),
      });
      setResult(response);
    } catch (e) {
      setResult({ status: "error", message: (e as Error).message, cases: [] });
    } finally {
      runningRef.current = false;
      setRunning(false);
    }
  }, [id, language, mode, code, custom, stdin]);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        void run();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [run]);
  const rate = async (value: Rating) => {
    if (ratingInFlight.current) return;
    ratingInFlight.current = true;
    setRatingBusy(true);
    setRatingError("");
    pendingRating.current ??= {
      type: "rate",
      problemId: id,
      rating: value,
      day: dayKey(),
      eventId: crypto.randomUUID(),
      seconds: Math.min(14400, seconds.current),
    };
    try {
      const pending = pendingRating.current;
      const next = await mutate(pending);
      setFeedback(
        confirmedStudy(state, next, pending.rating, dueLabel(next.cards[id])),
      );
      setRating(pending.rating);
      pendingRating.current = null;
      seconds.current = 0;
      notify(
        `已记录 · ${dueLabel(next.cards[id])}${next.checkins.includes(dayKey()) ? " · 今日已打卡" : ""}`,
      );
    } catch {
      setRatingError("这次反馈还未保存，请点击下方按钮重试。");
      notify("反馈尚未确认，请重试。");
    } finally {
      ratingInFlight.current = false;
      setRatingBusy(false);
    }
  };
  const copy = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      notify("代码已复制");
    } catch {
      notify("浏览器未允许复制，请选中代码手动复制");
    }
  };
  if (error)
    return (
      <div className="workspace-loading">
        <h2>题目加载失败</h2>
        <p>{error}</p>
        <button className="secondary" onClick={onBack}>
          返回题库
        </button>
      </div>
    );
  if (!detail)
    return (
      <div className="workspace-loading">
        <LoaderCircle className="spin" />
        <p>正在打开练习工作区…</p>
      </div>
    );
  const next = dailyPlan(problems, state).find((p) => p.id !== id),
    theme = state.settings.theme === "dark" ? "dark" : "light",
    currentResult = result?.cases[caseIndex];
  return (
    <div
      ref={workspaceContainer}
      className={
        "workspace customizable-workspace" + (narrowLayout ? " is-stacked" : "")
      }
      style={
        {
          "--workspace-question-share": `${layout.questionShare}fr`,
          "--workspace-editor-share": `${100 - layout.questionShare}fr`,
          "--workspace-code-share": `${layout.codeShare}fr`,
          "--workspace-console-share": `${100 - layout.codeShare}fr`,
        } as CSSProperties
      }
    >
      <div className="workspace-heading">
        <div>
          <button className="icon-btn" title="返回" onClick={onBack}>
            <ArrowLeft size={18} />
          </button>
          <span className="workspace-file-icon">
            <FileCode2 size={17} />
          </span>
          <span>{detail.title}</span>
          <span className="outline-badge tiny">Hot 100</span>
        </div>
        <div>
          <span className="workspace-save">
            <i className={"status-dot " + (!saved ? "pending" : "")} />
            {saved ? "草稿已自动保存" : "正在保存草稿"}
          </span>
          <button
            className={
              "icon-btn " + (state.favorites.includes(id) ? "starred" : "")
            }
            title={state.favorites.includes(id) ? "取消收藏" : "收藏题目"}
            onClick={() =>
              void mutate({ type: "favorite", problemId: id }).catch(() => {})
            }
          >
            <Star
              size={17}
              fill={state.favorites.includes(id) ? "currentColor" : "none"}
            />
          </button>
          <button
            className="secondary small"
            onClick={() => {
              if (next) onOpen(next.id);
              else {
                const index = problems.findIndex((p) => p.id === id);
                onOpen(problems[(index + 1) % problems.length].id);
              }
            }}
          >
            下一题 <ChevronRight size={14} />
          </button>
        </div>
      </div>
      <div className="workspace-layout-toolbar" aria-label="工作区布局">
        <span>
          <SlidersHorizontal size={15} />
          布局
        </span>
        {(
          [
            ["question", "题目区"],
            ["editor", "代码区"],
            ["console", "运行区"],
            ["progress", "学习进度"],
          ] as const
        ).map(([name, label]) => (
          <button
            key={name}
            aria-pressed={layout[name] && (name !== "console" || layout.editor)}
            disabled={
              (name === "question" && layout.question && !layout.editor) ||
              (name === "editor" && layout.editor && !layout.question)
            }
            onClick={() =>
              setLayout((current) =>
                name === "console" && !current.editor
                  ? { ...current, editor: true, console: true }
                  : { ...current, [name]: !current[name] },
              )
            }
          >
            {label}
          </button>
        ))}
        <button
          className="workspace-layout-reset"
          onClick={() => setLayout({ ...defaultWorkspaceLayout })}
        >
          <RotateCcw size={13} />
          恢复布局
        </button>
      </div>
      <div className="workspace-progress-panel" hidden={!layout.progress}>
        <StudyProgress state={state} />
      </div>
      <div
        className={
          "workspace-split " +
          (layout.question && layout.editor
            ? "has-both-panels"
            : "single-panel")
        }
      >
        <section
          className="question-pane"
          hidden={!layout.question}
          aria-label="题目、题解与笔记"
        >
          <div className="workspace-tabs">
            {[
              { label: "题目", icon: BookOpen },
              { label: "题解", icon: Lightbulb },
              { label: "笔记", icon: FileCode2 },
            ].map(({ label, icon: Icon }) => (
              <button
                key={label}
                className={tab === label ? "selected" : ""}
                onClick={() => setTab(label)}
              >
                <Icon size={15} />
                {label}
                {label === "笔记" && note && <i className="note-dot" />}
              </button>
            ))}
            <a
              href={`https://leetcode.cn/problems/${detail.slug}/`}
              title="打开力扣原题"
              target="_blank"
              rel="noreferrer"
              className="icon-btn"
            >
              <ExternalLink size={15} />
            </a>
          </div>
          <div className="question-scroll">
            {tab === "题目" && (
              <>
                <div className="question-title">
                  <span className="eyebrow">LEETCODE #{id}</span>
                  <h1>{detail.title}</h1>
                  <div className="question-tags">
                    <Difficulty value={detail.difficulty} />
                    <span>{detail.category}</span>
                    <span className="subtle-pill">Hot 100</span>
                  </div>
                </div>
                <p className="problem-statement">{detail.summary}</p>
                {mode === "acm" && (
                  <section className="input-guide">
                    <h3>
                      <Terminal size={15} />
                      ACM 输入输出约定
                    </h3>
                    <ol>
                      {detail.inputGuide.map((line, i) => (
                        <li key={i}>{line}</li>
                      ))}
                    </ol>
                  </section>
                )}
                <div className="examples">
                  {detail.examples.map((example, i) => (
                    <section className="example" key={i}>
                      <h3>示例 {i + 1}</h3>
                      <div className="example-code">
                        {mode === "leetcode" ? (
                          <>
                            {detail.params.map((param, j) => (
                              <div key={param.name}>
                                <span>{param.name} = </span>
                                <code>{JSON.stringify(example.input[j])}</code>
                              </div>
                            ))}
                            {example.input.length > detail.params.length && (
                              <div>
                                <span>附加结构参数 = </span>
                                <code>
                                  {JSON.stringify(
                                    example.input.slice(detail.params.length),
                                  )}
                                </code>
                              </div>
                            )}
                            <div className="example-output">
                              <span>输出：</span>
                              <code>{JSON.stringify(example.output)}</code>
                            </div>
                          </>
                        ) : (
                          <>
                            <label>标准输入</label>
                            <pre>{example.stdin}</pre>
                            <label>标准输出</label>
                            <pre>{JSON.stringify(example.output)}</pre>
                          </>
                        )}
                      </div>
                      {example.explanation && (
                        <p>
                          <strong>解释：</strong>
                          {example.explanation}
                        </p>
                      )}
                    </section>
                  ))}
                </div>
                <section className="constraints">
                  <h3>提示与约束</h3>
                  <ul>
                    {detail.constraints.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </section>
                <div className="question-footnote">
                  <Lightbulb size={15} />
                  先独立思考，再打开题解。主动回忆，比看懂更重要。
                </div>
              </>
            )}
            {tab === "题解" && (
              <ProblemSolution
                key={key}
                problem={detail}
                language={language}
                mode={mode}
                personal={state.solutions?.[key]}
                theme={theme}
                mutate={mutate}
                notify={notify}
                copy={copy}
              />
            )}
            {tab === "笔记" && (
              <div className="notes-pane">
                <span className="eyebrow">WRITE IT IN YOUR OWN WORDS</span>
                <h2>留下自己的理解。</h2>
                <p>
                  为什么这样解？哪里容易错？下次看到什么信号，就该想到这个方法？
                </p>
                <div className="note-view-toolbar">
                  <div className="segmented" aria-label="笔记显示方式">
                    {(
                      [
                        { id: "edit", label: "编辑" },
                        { id: "preview", label: "预览" },
                        { id: "split", label: "分栏" },
                      ] as const
                    ).map((item) => (
                      <button
                        key={item.id}
                        className={noteView === item.id ? "selected" : ""}
                        onClick={() => setNoteView(item.id)}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                  <span>Markdown · 标题 / 列表 / 表格 / 代码块</span>
                </div>
                <div className={"note-content-layout " + noteView}>
                  {noteView !== "preview" && (
                    <textarea
                      aria-label="我的题目笔记"
                      maxLength={30000}
                      value={note}
                      onChange={(e) => updateNote(e.target.value)}
                      placeholder={
                        "## 关键信号\n\n- 核心思路\n- 易错边界\n\n```python\n# 写下值得记住的代码\n```"
                      }
                    />
                  )}
                  {noteView !== "edit" && (
                    <div className="note-preview" aria-label="笔记预览">
                      {note && <Markdown>{note}</Markdown>}
                    </div>
                  )}
                </div>
                <div className="note-footer">
                  <span>
                    <Save size={13} />
                    输入后自动保存
                  </span>
                  <span>{note.length} / 30000</span>
                </div>
              </div>
            )}
          </div>
          <div className="memory-feedback">
            {feedback && <StudyFeedback feedback={feedback} />}
            <div className="feedback-title">
              <span>
                <Sparkles size={15} />
                {rating
                  ? "这份记忆，已经留下。"
                  : "合上题解，还能自己写出来吗？"}
              </span>
              {rating && <span>{dueLabel(state.cards[id])}</span>}
            </div>
            {ratingError && (
              <p className="knowledge-error" role="alert">
                {ratingError}
              </p>
            )}
            {rating ? (
              <div className="feedback-done">
                <span>
                  <CircleCheck size={16} />
                  {ratingLabels[rating]} · 已加入复习计划
                </span>
                <button
                  className="text-button"
                  onClick={() => (next ? onOpen(next.id) : onBack())}
                >
                  {next ? "继续下一题" : "返回今日计划"}
                  <ArrowRight size={14} />
                </button>
              </div>
            ) : (
              <div className="rating-buttons study-rating-buttons">
                {(["again", "hard", "good", "easy"] as Rating[]).map((r) => (
                  <button
                    key={r}
                    disabled={ratingBusy}
                    className={"rate-" + r}
                    onClick={() => void rate(r)}
                  >
                    <RatingSymbol rating={r} />
                    <span>{ratingLabels[r]}</span>
                    <small>
                      {r === "again"
                        ? "10 分钟后"
                        : r === "hard"
                          ? "尽早再练"
                          : r === "good"
                            ? "按计划复习"
                            : "延长间隔"}
                    </small>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>
        {layout.question && layout.editor && (
          <WorkspaceSeparator
            direction="columns"
            value={layout.questionShare}
            onChange={(value) =>
              setLayout((current) => ({ ...current, questionShare: value }))
            }
          />
        )}
        <section
          className="editor-pane"
          hidden={!layout.editor}
          aria-label="代码与运行工作区"
        >
          <div className="editor-toolbar">
            <div className="editor-selects">
              <label>
                <select
                  aria-label="编程语言"
                  disabled={running}
                  value={language}
                  onChange={(e) => switchLanguage(e.target.value as Language)}
                >
                  <option value="python">Python 3</option>
                  <option value="cpp">C++ 17</option>
                </select>
                <ChevronDown size={13} />
              </label>
              <span className="vertical-line" />
              <label>
                <select
                  aria-label="答题模式"
                  disabled={running}
                  value={mode}
                  onChange={(e) => switchMode(e.target.value as Mode)}
                >
                  <option value="leetcode">LeetCode 模式</option>
                  <option value="acm">ACM 模式</option>
                </select>
                <ChevronDown size={13} />
              </label>
            </div>
            <div>
              <button
                className="icon-btn"
                title="重置当前草稿"
                onClick={() => setConfirmReset(true)}
              >
                <RotateCcw size={15} />
              </button>
              <button
                className="icon-btn"
                title="下载我的代码"
                onClick={() =>
                  download(
                    `${detail.slug}.${language === "python" ? "py" : "cpp"}`,
                    code,
                    "text/plain",
                  )
                }
              >
                <ArrowDownToLine size={15} />
              </button>
              <button
                className="icon-btn"
                title={!layout.question ? "恢复分栏" : "展开编辑器"}
                onClick={() =>
                  setLayout((current) => ({
                    ...current,
                    editor: true,
                    question: !current.question,
                  }))
                }
              >
                <Maximize2 size={15} />
              </button>
            </div>
          </div>
          <div className="editor-filename">
            <Code2 size={14} />
            {mode === "leetcode" ? "solution" : "main"}.
            {language === "python" ? "py" : "cpp"}
            <span>
              {mode === "leetcode"
                ? "实现题目要求的方法"
                : "包含 main / 标准输入输出的完整程序"}
            </span>
          </div>
          <div
            className={
              "answer-output-split " +
              (layout.console ? "with-console" : "without-console")
            }
          >
            <div className="answer-editor-area">
              <div className="code-editor">
                <CodeMirror
                  value={code}
                  height="100%"
                  minHeight="0"
                  onCreateEditor={(view) => {
                    answerEditor.current = view;
                  }}
                  extensions={editorExtensions}
                  indentWithTab={false}
                  theme={theme}
                  onChange={updateCode}
                  basicSetup={{
                    lineNumbers: true,
                    foldGutter: true,
                    autocompletion: false,
                    completionKeymap: false,
                    highlightActiveLine: true,
                    bracketMatching: true,
                  }}
                />
              </div>
              <div className="editor-keyboard-hint">
                Enter 换行并缩进 · Tab 接受补全 / 缩进 · Shift + Tab 取消缩进 ·
                Ctrl + Space 补全 · 4 空格
              </div>
              <div className="editor-status">
                <span>
                  {language === "python"
                    ? `Python ${capabilities.python.version}`
                    : "C++ 17"}
                  <span className="text-dot">·</span>UTF-8
                </span>
                <span>
                  {code.split("\n").length} 行
                  <span className="text-dot">·</span>
                  {mode === "leetcode"
                    ? "节点结构与常用导入已提供"
                    : "标准输入 / 标准输出"}
                </span>
              </div>
            </div>
            {layout.console && (
              <WorkspaceSeparator
                direction="rows"
                value={layout.codeShare}
                onChange={(value) =>
                  setLayout((current) => ({ ...current, codeShare: value }))
                }
              />
            )}
            <div className="console-pane" hidden={!layout.console}>
              <div className="console-tabs">
                <div>
                  {["测试用例", "运行结果"].map((t) => (
                    <button
                      className={consoleTab === t ? "selected" : ""}
                      key={t}
                      onClick={() => setConsoleTab(t)}
                    >
                      {t === "测试用例" ? (
                        <Terminal size={14} />
                      ) : (
                        <CircleCheck size={14} />
                      )}{" "}
                      {t}
                      {t === "运行结果" && result && (
                        <i
                          className={
                            result.status === "passed"
                              ? "result-dot passed"
                              : "result-dot"
                          }
                        />
                      )}
                    </button>
                  ))}
                </div>
                <button
                  className="run-button"
                  disabled={running}
                  onClick={() => void run()}
                >
                  {running ? (
                    <LoaderCircle className="spin" size={14} />
                  ) : (
                    <Play size={14} fill="currentColor" />
                  )}
                  {running ? "运行中…" : "运行代码"}
                  <kbd>⌃ ↵</kbd>
                </button>
              </div>
              <div className="console-content">
                {consoleTab === "测试用例" ? (
                  <>
                    <div className="case-tabs">
                      {detail.examples.map((_, i) => (
                        <button
                          className={
                            !custom && caseIndex === i ? "selected" : ""
                          }
                          key={i}
                          onClick={() => {
                            setCustom(false);
                            setCaseIndex(i);
                          }}
                        >
                          样例 {i + 1}
                        </button>
                      ))}
                      <button
                        className={custom ? "selected" : ""}
                        onClick={() => setCustom(true)}
                      >
                        自定义输入
                      </button>
                    </div>
                    {custom ? (
                      <div className="custom-input">
                        <p>
                          按左侧 ACM 输入约定填写标准输入，运行后查看输出结果。
                        </p>
                        <textarea
                          aria-label="自定义标准输入"
                          value={stdin}
                          maxLength={20000}
                          onChange={(e) => setStdin(e.target.value)}
                        />
                        <button
                          className="text-button"
                          onClick={() => {
                            setTab("题目");
                            switchMode("acm");
                          }}
                        >
                          查看输入约定 <ArrowRight size={13} />
                        </button>
                      </div>
                    ) : (
                      <div className="test-preview">
                        <div>
                          <label>输入</label>
                          <pre>
                            {
                              detail.examples[
                                Math.min(caseIndex, detail.examples.length - 1)
                              ]?.stdin
                            }
                          </pre>
                        </div>
                        <div>
                          <label>期望输出</label>
                          <pre>
                            {JSON.stringify(
                              detail.examples[
                                Math.min(caseIndex, detail.examples.length - 1)
                              ]?.output,
                            )}
                          </pre>
                        </div>
                      </div>
                    )}
                  </>
                ) : running ? (
                  <div className="console-empty">
                    <LoaderCircle className="spin" size={20} />
                    <p>
                      {language === "cpp"
                        ? "正在编译并运行本地样例…"
                        : "正在运行本地样例…"}
                    </p>
                  </div>
                ) : result ? (
                  <>
                    <div
                      className={
                        "result-banner " +
                        (["passed", "executed"].includes(result.status)
                          ? "success"
                          : "failure")
                      }
                    >
                      {["passed", "executed"].includes(result.status) ? (
                        <CircleCheck size={17} />
                      ) : (
                        <Terminal size={17} />
                      )}
                      <span>{result.message}</span>
                      {currentResult && (
                        <small>{currentResult.elapsedMs} ms</small>
                      )}
                    </div>
                    {result.cases.length > 0 && (
                      <>
                        <div className="case-tabs">
                          {result.cases.map((c, i) => (
                            <button
                              key={i}
                              className={caseIndex === i ? "selected" : ""}
                              onClick={() => setCaseIndex(i)}
                            >
                              {c.passed === true ? (
                                <Check size={12} />
                              ) : c.error || c.passed === false ? (
                                <X size={12} />
                              ) : null}
                              用例 {i + 1}
                            </button>
                          ))}
                        </div>
                        {currentResult && (
                          <div className="result-content">
                            {currentResult.error && (
                              <p className="error-text">
                                {currentResult.error}
                              </p>
                            )}
                            {currentResult.stderr && (
                              <pre className="stderr">
                                {currentResult.stderr}
                              </pre>
                            )}
                            <label>实际输出</label>
                            <pre>{currentResult.stdout || "（无输出）"}</pre>
                            {currentResult.passed !== null && (
                              <>
                                <label>期望输出</label>
                                <pre>
                                  {JSON.stringify(currentResult.expected)}
                                </pre>
                              </>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </>
                ) : (
                  <div className="console-empty">
                    <Terminal size={23} />
                    <p>写下思路，运行第一组样例。</p>
                    <span>Ctrl / ⌘ + Enter 快速运行</span>
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="runner-footnote" hidden={!layout.console}>
            本地样例测试 · 请运行可信代码
          </div>
        </section>
      </div>
      {confirmReset && (
        <div className="modal-backdrop">
          <section className="modal" role="dialog" aria-modal="true">
            <h2>重置当前代码？</h2>
            <p>当前语言与模式的代码将恢复为初始模板。其他模式的草稿会保留。</p>
            <div className="button-group">
              <button
                className="secondary"
                onClick={() => setConfirmReset(false)}
              >
                取消
              </button>
              <button
                className="primary"
                onClick={() => {
                  download(
                    `${detail.slug}-before-reset.${language === "python" ? "py" : "cpp"}`,
                    code,
                    "text/plain",
                  );
                  updateCode(detail.templates[language][mode]);
                  setConfirmReset(false);
                  notify("已下载旧代码备份，并恢复初始模板");
                }}
              >
                备份并重置
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

type PersonalSolution = {
  brief: string;
  annotated: string;
  explanation: string;
};
type SolutionSection = keyof PersonalSolution;

function referenceSolution(
  problem: Detail,
  language: Language,
  mode: Mode,
): PersonalSolution {
  return {
    ...problem.solutions[language][mode],
    explanation: [
      "## 解题思路",
      problem.approach,
      problem.steps.map((step, i) => `${i + 1}. ${step}`).join("\n"),
      "## 为什么这样做是对的？",
      problem.correctness,
      "## 复杂度分析",
      `- 时间复杂度：${problem.time}\n- 额外空间复杂度：${problem.space}`,
      "## 这些细节值得记住",
      problem.pitfalls.map((item) => `- ${item}`).join("\n"),
    ].join("\n\n"),
  };
}

function readSolutionDraft(key: string): PersonalSolution | null {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) || "null");
    if (
      value &&
      typeof value === "object" &&
      ["brief", "annotated", "explanation"].every(
        (field) =>
          typeof (value as Record<string, unknown>)[field] === "string",
      )
    ) {
      return value as PersonalSolution;
    }
  } catch {
    /* Keep invalid browser data out of the editor. */
  }
  return null;
}

function ProblemSolution({
  problem,
  language,
  mode,
  personal,
  theme,
  mutate,
  notify,
  copy,
}: {
  problem: Detail;
  language: Language;
  mode: Mode;
  personal: (PersonalSolution & { updatedAt: string }) | undefined;
  theme: "light" | "dark";
  mutate: Props["mutate"];
  notify: Props["notify"];
  copy: (value: string) => Promise<void>;
}) {
  const storageKey = `coderecall-solution-draft-${problem.id}:${language}:${mode}`;
  const reference = referenceSolution(problem, language, mode);
  const [initialDraft] = useState(() => readSolutionDraft(storageKey));
  const [source, setSource] = useState<"reference" | "personal">(
    personal || initialDraft ? "personal" : "reference",
  );
  const [editing, setEditing] = useState(Boolean(initialDraft));
  const [value, setValue] = useState<PersonalSolution>(
    initialDraft ?? personal ?? reference,
  );
  const [answerTab, setAnswerTab] = useState<SolutionSection>("brief");
  const [saving, setSaving] = useState(false);
  const [draftStored, setDraftStored] = useState(Boolean(initialDraft));
  const [confirmAction, setConfirmAction] = useState<"cancel" | "reset" | null>(
    null,
  );
  const storageWarning = useRef(false);
  const shown = source === "reference" ? reference : editing ? value : personal;
  const editorExtensions = useMemo(
    () => [language === "python" ? python() : cpp(), ...codeEditingExtensions],
    [language],
  );

  const remember = (next: PersonalSolution) => {
    setValue(next);
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
      setDraftStored(true);
    } catch {
      setDraftStored(false);
      if (!storageWarning.current) {
        storageWarning.current = true;
        notify("浏览器草稿空间不足，请先保存题解再切换页面。");
      }
    }
  };
  useEffect(() => {
    if (!editing || draftStored) return;
    const guard = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [editing, draftStored]);
  const removeDraft = (savedValue?: PersonalSolution) => {
    try {
      // A save can finish after navigating away and editing this variant again.
      // Never remove a newer local draft in that case.
      if (
        savedValue &&
        localStorage.getItem(storageKey) !== JSON.stringify(savedValue)
      )
        return;
      localStorage.removeItem(storageKey);
    } catch {
      /* Browser may prohibit storage. */
    }
    setDraftStored(false);
  };
  const begin = () => {
    setSource("personal");
    if (!editing) {
      remember(
        personal
          ? {
              brief: personal.brief,
              annotated: personal.annotated,
              explanation: personal.explanation,
            }
          : reference,
      );
      setEditing(true);
    }
  };
  const save = async () => {
    if (saving) return;
    if (value.brief.length > 100000 || value.annotated.length > 100000) {
      notify("每个代码版本最多 100000 字，请缩短后保存。");
      return;
    }
    setSaving(true);
    try {
      await mutate({
        type: "solution",
        problemId: problem.id,
        language,
        mode,
        solution: value,
      });
      removeDraft(value);
      setEditing(false);
      notify("我的题解已保存 · 简洁版、注释版与完整解析");
    } catch {
      notify("保存失败，题解草稿已保留，请重试。");
    } finally {
      setSaving(false);
    }
  };
  const confirm = async () => {
    if (confirmAction === "cancel") {
      removeDraft();
      setEditing(false);
      setConfirmAction(null);
      setSource(personal ? "personal" : "reference");
      return;
    }
    setSaving(true);
    try {
      await mutate({
        type: "solution-reset",
        problemId: problem.id,
        language,
        mode,
      });
      removeDraft();
      setEditing(false);
      setSource("reference");
      setConfirmAction(null);
      notify("当前语言与模式已恢复使用内置题解");
    } catch {
      notify("恢复失败，原题解已保留，请重试。");
    } finally {
      setSaving(false);
    }
  };
  return (
    <>
      <div className="solution-title">
        <span className="eyebrow">MAKE THE SOLUTION YOUR OWN</span>
        <h2>{source === "reference" ? problem.approach : "我的题解"}</h2>
        {source === "reference" ? (
          <div className="complexity">
            <span>
              <Clock3 size={14} />
              时间 {problem.time}
            </span>
            <span>
              <Code2 size={14} />
              空间 {problem.space}
            </span>
          </div>
        ) : (
          <p className="solution-personal-meta">
            {language === "python" ? "Python 3" : "C++ 17"} ·{" "}
            {mode === "leetcode" ? "LeetCode" : "ACM"} ·
            用自己的思路整理三个版本
          </p>
        )}
      </div>
      <div className="solution-source-bar">
        <div className="segmented" aria-label="题解来源">
          <button
            className={source === "reference" ? "selected" : ""}
            onClick={() => setSource("reference")}
          >
            内置题解
          </button>
          <button
            className={source === "personal" ? "selected" : ""}
            onClick={() => setSource("personal")}
          >
            我的题解{personal && " · 已保存"}
          </button>
        </div>
        <button className="secondary small" disabled={saving} onClick={begin}>
          {editing ? "继续编辑" : personal ? "编辑我的题解" : "创建我的题解"}
        </button>
      </div>
      {editing && source === "reference" && (
        <div className="solution-draft-notice">
          我的题解草稿已保留。切换回“我的题解”可继续编辑。
        </div>
      )}
      {source === "personal" && editing && (
        <div className="solution-edit-actions">
          <span className="solution-save-state">
            <Save size={13} />
            {draftStored ? "草稿已保留，点击保存后生效" : "编辑中，请及时保存"}
          </span>
          <div>
            <button
              className="secondary small"
              disabled={saving}
              onClick={() => setConfirmAction("cancel")}
            >
              取消编辑
            </button>
            <button
              className="primary small"
              disabled={saving}
              onClick={() => void save()}
            >
              {saving ? "正在保存…" : "保存题解"}
            </button>
          </div>
        </div>
      )}
      {shown ? (
        <>
          <div className="segmented solution-tabs">
            {(
              [
                { id: "brief", label: "简洁版" },
                { id: "annotated", label: "注释版" },
                { id: "explanation", label: "完整解析" },
              ] as const
            ).map((item) => (
              <button
                key={item.id}
                className={answerTab === item.id ? "selected" : ""}
                onClick={() => setAnswerTab(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          {answerTab === "explanation" ? (
            source === "personal" && editing ? (
              <>
                <textarea
                  className="solution-description-edit"
                  aria-label="我的完整解析 Markdown"
                  value={value.explanation}
                  maxLength={30000}
                  disabled={saving}
                  onChange={(event) =>
                    remember({ ...value, explanation: event.target.value })
                  }
                  placeholder="## 解题思路\n用你自己的语言解释为什么这样做。"
                />
                <div className="solution-explanation-preview">
                  <span>Markdown 预览</span>
                  <Markdown>{value.explanation}</Markdown>
                </div>
              </>
            ) : (
              <Markdown>{shown.explanation || "_尚未填写完整解析。_"}</Markdown>
            )
          ) : (
            <div className="solution-code">
              <div className="code-toolbar">
                <span>
                  {language === "python" ? "Python 3" : "C++ 17"}
                  <span className="text-dot">·</span>
                  {mode === "leetcode" ? "LeetCode" : "ACM"}
                  {source === "personal" && editing ? " · 可编辑" : ""}
                </span>
                <div>
                  <button
                    className="icon-btn"
                    title="复制题解"
                    onClick={() => void copy(shown[answerTab])}
                  >
                    <Copy size={14} />
                  </button>
                  <button
                    className="icon-btn"
                    title="下载题解"
                    onClick={() =>
                      download(
                        `${problem.slug}-${mode}-${answerTab}.${language === "python" ? "py" : "cpp"}`,
                        shown[answerTab],
                        "text/plain",
                      )
                    }
                  >
                    <ArrowDownToLine size={14} />
                  </button>
                </div>
              </div>
              <CodeMirror
                key={answerTab}
                aria-label={
                  answerTab === "brief" ? "简洁版题解代码" : "注释版题解代码"
                }
                value={shown[answerTab]}
                extensions={editorExtensions}
                indentWithTab={false}
                theme={theme}
                editable={source === "personal" && editing && !saving}
                onChange={(text) => {
                  if (source === "personal" && editing)
                    remember({ ...value, [answerTab]: text });
                }}
                basicSetup={{
                  lineNumbers: true,
                  foldGutter: false,
                  highlightActiveLine: editing,
                  highlightActiveLineGutter: editing,
                  autocompletion: false,
                  completionKeymap: false,
                }}
              />
            </div>
          )}
        </>
      ) : (
        <div className="solution-personal-empty">
          <p>从内置题解开始，写下更适合自己的解法。</p>
          <button className="primary small" onClick={begin}>
            从内置题解开始编辑
          </button>
        </div>
      )}
      {source === "personal" && personal && !editing && (
        <div className="solution-edit-actions">
          <span>
            已保存于 {new Date(personal.updatedAt).toLocaleString("zh-CN")}
          </span>
          <button
            className="text-button"
            onClick={() => setConfirmAction("reset")}
          >
            <RotateCcw size={13} />
            恢复内置题解
          </button>
        </div>
      )}
      <div className="question-footnote">
        <Sparkles size={15} />
        {editing
          ? "三个版本独立编辑；切换语言或模式会保留各自草稿。"
          : "理解后合上题解，再尝试独立实现一次。"}
      </div>
      {confirmAction && (
        <div className="modal-backdrop solution-revert-modal">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={
              confirmAction === "cancel" ? "放弃题解草稿" : "恢复内置题解"
            }
          >
            <h2>
              {confirmAction === "cancel"
                ? "放弃本次题解草稿？"
                : "恢复内置题解？"}
            </h2>
            <p>
              {confirmAction === "cancel"
                ? "仅删除当前语言与模式尚未保存的修改，已保存的题解会保留。"
                : "当前语言与模式的自定义题解将被删除。其他语言和模式的题解会保留。"}
            </p>
            <div className="button-group">
              <button
                className="secondary"
                disabled={saving}
                onClick={() => setConfirmAction(null)}
              >
                继续保留
              </button>
              <button
                className="primary"
                disabled={saving}
                onClick={() => void confirm()}
              >
                {saving
                  ? "处理中…"
                  : confirmAction === "cancel"
                    ? "放弃草稿"
                    : "确认恢复"}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
