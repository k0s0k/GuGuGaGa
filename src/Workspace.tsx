import { useCallback, useEffect, useRef, useState } from "react";
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
    [answerTab, setAnswerTab] = useState<"brief" | "annotated" | "explanation">(
      "brief",
    );
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
    [confirmReset, setConfirmReset] = useState(false),
    [expanded, setExpanded] = useState(false);
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
      setRating(pending.rating);
      pendingRating.current = null;
      seconds.current = 0;
      notify(
        `已记录 · ${dueLabel(next.cards[id])}${next.checkins.includes(dayKey()) ? " · 今日已打卡" : ""}`,
      );
    } catch {
      notify("反馈尚未确认，请再次点击重试；不会重复计入学习记录。");
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
    answer = detail.solutions[language][mode],
    extension = language === "python" ? python() : cpp(),
    theme = state.settings.theme === "dark" ? "dark" : "light",
    currentResult = result?.cases[caseIndex];
  return (
    <div className={"workspace " + (expanded ? "editor-expanded" : "")}>
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
      <div className="workspace-split">
        <section className="question-pane">
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
              <>
                <div className="solution-title">
                  <span className="eyebrow">
                    ONE PROBLEM, ONE CLEAR SOLUTION
                  </span>
                  <h2>{detail.approach}</h2>
                  <div className="complexity">
                    <span>
                      <Clock3 size={14} />
                      时间 {detail.time}
                    </span>
                    <span>
                      <Code2 size={14} />
                      空间 {detail.space}
                    </span>
                  </div>
                </div>
                <div className="segmented solution-tabs">
                  {(
                    [
                      { id: "brief", label: "简洁版" },
                      { id: "annotated", label: "注释版" },
                      { id: "explanation", label: "完整解析" },
                    ] as const
                  ).map((t) => (
                    <button
                      className={answerTab === t.id ? "selected" : ""}
                      onClick={() => setAnswerTab(t.id)}
                      key={t.id}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
                {answerTab === "explanation" ? (
                  <div className="explanation">
                    <section>
                      <h3>解题思路</h3>
                      <p>{detail.approach}</p>
                      <ol>
                        {detail.steps.map((step, i) => (
                          <li key={i}>
                            <span>{String(i + 1).padStart(2, "0")}</span>
                            <p>{step}</p>
                          </li>
                        ))}
                      </ol>
                    </section>
                    <section>
                      <h3>为什么这样做是对的？</h3>
                      <p>{detail.correctness}</p>
                    </section>
                    <section>
                      <h3>复杂度分析</h3>
                      <p>
                        时间复杂度：<code>{detail.time}</code>
                        <br />
                        额外空间复杂度：<code>{detail.space}</code>
                      </p>
                    </section>
                    <section className="pitfalls">
                      <h3>
                        <Lightbulb size={16} />
                        这些细节值得记住
                      </h3>
                      <ul>
                        {detail.pitfalls.map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                      </ul>
                    </section>
                  </div>
                ) : (
                  <div className="solution-code">
                    <div className="code-toolbar">
                      <span>
                        {language === "python" ? "Python 3" : "C++ 17"}
                        <span className="text-dot">·</span>
                        {mode === "leetcode" ? "LeetCode" : "ACM"}
                      </span>
                      <div>
                        <button
                          className="icon-btn"
                          title="复制题解"
                          onClick={() => void copy(answer[answerTab])}
                        >
                          <Copy size={14} />
                        </button>
                        <button
                          className="icon-btn"
                          title="下载题解"
                          onClick={() =>
                            download(
                              `${detail.slug}-${mode}.${language === "python" ? "py" : "cpp"}`,
                              answer[answerTab],
                              "text/plain",
                            )
                          }
                        >
                          <ArrowDownToLine size={14} />
                        </button>
                      </div>
                    </div>
                    <CodeMirror
                      value={answer[answerTab]}
                      extensions={[extension]}
                      theme={theme}
                      editable={false}
                      basicSetup={{
                        lineNumbers: true,
                        foldGutter: false,
                        highlightActiveLine: false,
                        highlightActiveLineGutter: false,
                      }}
                    />
                  </div>
                )}
                <div className="question-footnote">
                  <Sparkles size={15} />
                  简洁版与注释版使用相同算法。建议理解后关掉题解，再独立实现一次。
                </div>
              </>
            )}
            {tab === "笔记" && (
              <div className="notes-pane">
                <span className="eyebrow">WRITE IT IN YOUR OWN WORDS</span>
                <h2>留下自己的理解。</h2>
                <p>
                  为什么这样解？哪里容易错？下次看到什么信号，就该想到这个方法？
                </p>
                <textarea
                  aria-label="我的题目笔记"
                  maxLength={30000}
                  value={note}
                  onChange={(e) => updateNote(e.target.value)}
                  placeholder={
                    "可以从这几个问题开始：\n\n• 这道题的关键信号是什么？\n• 核心思路，用一句话怎么说？\n• 我曾经忽略了哪个边界条件？"
                  }
                />
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
            <div className="feedback-title">
              <span>
                <Sparkles size={15} />
                {rating
                  ? "这份记忆，已经留下。"
                  : "合上题解，还能自己写出来吗？"}
              </span>
              {rating && <span>{dueLabel(state.cards[id])}</span>}
            </div>
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
              <div className="rating-buttons">
                {(["again", "hard", "good", "easy"] as Rating[]).map((r) => (
                  <button
                    key={r}
                    disabled={ratingBusy}
                    className={"rate-" + r}
                    onClick={() => void rate(r)}
                  >
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
        <section className="editor-pane">
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
                title={expanded ? "恢复分栏" : "展开编辑器"}
                onClick={() => setExpanded(!expanded)}
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
          <div className="code-editor">
            <CodeMirror
              value={code}
              height="100%"
              extensions={[extension]}
              theme={theme}
              onChange={updateCode}
              basicSetup={{
                lineNumbers: true,
                foldGutter: true,
                autocompletion: true,
                highlightActiveLine: true,
                bracketMatching: true,
              }}
            />
          </div>
          <div className="editor-status">
            <span>
              {language === "python"
                ? `Python ${capabilities.python.version}`
                : "C++ 17"}
              <span className="text-dot">·</span>UTF-8
            </span>
            <span>
              {code.split("\n").length} 行<span className="text-dot">·</span>
              {mode === "leetcode"
                ? "节点结构与常用导入已提供"
                : "标准输入 / 标准输出"}
            </span>
          </div>
          <div className="console-pane">
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
                        className={!custom && caseIndex === i ? "selected" : ""}
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
                        按左侧 ACM
                        输入约定填写标准输入；自定义输入仅运行，不判定正确性。
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
                            <p className="error-text">{currentResult.error}</p>
                          )}
                          {currentResult.stderr && (
                            <pre className="stderr">{currentResult.stderr}</pre>
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
          <div className="runner-footnote">
            本地执行 · 仅运行可信代码 · 样例验证不等同于力扣全量判题
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
