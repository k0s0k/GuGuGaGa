import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  Bell,
  BookOpen,
  CalendarDays,
  CheckCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Circle,
  CircleCheck,
  CircleHelp,
  Code2,
  Command,
  Flame,
  Folder,
  Github,
  Layers,
  LoaderCircle,
  Menu,
  Moon,
  MoreHorizontal,
  PanelLeftClose,
  RotateCcw,
  Search,
  Settings2,
  Sprout,
  Star,
  Sun,
  Target,
  Upload,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { action, bootstrap } from "./api";
import Knowledge, { KnowledgeStudy } from "./Knowledge";
import LearningDashboard from "./LearningDashboard";
import { knowledgeProjection } from "./knowledgeProjection";
import AvatarSettings, { Avatar } from "./AvatarSettings";
import type { AppState, Capabilities, Problem, View } from "./types";
import {
  dateShift,
  dayKey,
  download,
  dueLabel,
  isDue,
  ratingLabels,
  retention,
  streak,
} from "./utils";
const Workspace = lazy(() => import("./Workspace"));

const navigation: { id: View; label: string; icon: LucideIcon }[] = [
  { id: "today", label: "今日学习", icon: Sun },
  { id: "knowledge", label: "我的知识库", icon: BookOpen },
  { id: "library", label: "Hot 100 题库", icon: Code2 },
  { id: "review", label: "复习计划", icon: RotateCcw },
  { id: "calendar", label: "学习日历", icon: CalendarDays },
  { id: "path", label: "知识路线", icon: Layers },
  { id: "favorites", label: "我的收藏", icon: Star },
];
const categoryIcons: Record<string, string> = {
  哈希表: "#",
  数组: "[ ]",
  链表: "↔",
  二叉树: "⑂",
  动态规划: "ƒ",
  回溯: "↶",
  图论: "◇",
  双指针: "⇄",
  滑动窗口: "▤",
  矩阵: "▦",
  二分查找: "½",
  栈与队列: "≡",
  贪心: "↗",
  字符串: "Aa",
  技巧: "⌘",
  堆: "△",
  单调栈: "⌁",
};

function Empty({
  icon: Icon = Sprout,
  title,
  children,
}: {
  icon?: LucideIcon;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon size={25} />
      </div>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function Difficulty({ value }: { value: string }) {
  return (
    <span
      className={
        "difficulty " +
        ({ 简单: "easy", 中等: "medium", 困难: "hard" }[value] || "")
      }
    >
      {value}
    </span>
  );
}
function MemoryChart({ stability = 1 }: { stability?: number }) {
  const curve = (strength: number) =>
    Array.from(
      { length: 61 },
      (_, i) => `${20 + i * 4},${110 - 90 * Math.pow(0.9, i / 6 / strength)}`,
    ).join(" ");
  return (
    <svg
      viewBox="0 0 280 143"
      className="memory-chart"
      role="img"
      aria-label="记忆保留率随时间衰减的示意曲线，复习提高记忆稳定性"
    >
      {[20, 65, 110].map((y, i) => (
        <g key={y}>
          <line x1="20" x2="263" y1={y} y2={y} className="chart-grid" />
          <text x="0" y={y + 3}>
            {[100, 50, 0][i]}
          </text>
        </g>
      ))}
      <polyline
        points={curve(0.65)}
        fill="none"
        stroke="var(--text-faint)"
        strokeWidth="1.5"
        strokeDasharray="4 4"
      />
      <polyline
        points={curve(Math.max(2, stability))}
        fill="none"
        stroke="var(--green)"
        strokeWidth="2.4"
      />
      <circle cx="20" cy="20" r="3.5" fill="var(--green)" />
      {[0, 2, 4, 6, 8, 10].map((i) => (
        <text key={i} x={20 + i * 24} y="136" textAnchor="middle">
          {i === 0 ? "今天" : `${i} 天`}
        </text>
      ))}
    </svg>
  );
}

export default function App() {
  const [problems, setProblems] = useState<Problem[]>([]),
    [state, setState] = useState<AppState | null>(null),
    [capabilities, setCapabilities] = useState<Capabilities | null>(null),
    [categories, setCategories] = useState<string[]>([]);
  const [view, setView] = useState<View>("today"),
    [selected, setSelected] = useState<number | null>(null),
    [selectedKnowledge, setSelectedKnowledge] = useState<string | null>(null),
    [error, setError] = useState(""),
    [toast, setToast] = useState(""),
    [sideOpen, setSideOpen] = useState(false),
    [help, setHelp] = useState(false),
    [category, setCategory] = useState("全部专题");
  const [, setClock] = useState(0);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const notify = useCallback((message: string) => {
    setToast(message);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(""), 4500);
  }, []);
  useEffect(() => {
    bootstrap()
      .then((data) => {
        setProblems(data.problems);
        setState(data.state);
        setCapabilities(data.capabilities);
        setCategories(
          [
            ...new Set([
              ...data.categories,
              ...data.problems.map((p) => p.category),
            ]),
          ].filter((c) => data.problems.some((p) => p.category === c)),
        );
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    const tick = setInterval(() => setClock((n) => n + 1), 30000);
    return () => clearInterval(tick);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = state?.settings.theme || "light";
  }, [state?.settings.theme]);
  useEffect(() => {
    const parse = () => {
      const knowledgeMatch = location.hash.match(
        /^#knowledge\/([A-Za-z0-9_.:-]+)$/,
      );
      if (knowledgeMatch) {
        setSelected(null);
        setSelectedKnowledge(knowledgeMatch[1]);
        return;
      }
      setSelectedKnowledge(null);
      const match = location.hash.match(/^#problem\/(\d+)/);
      if (match) setSelected(Number(match[1]));
      else {
        setSelected(null);
        const key = location.hash.slice(1);
        if ([...navigation.map((n) => n.id), "settings"].includes(key))
          setView(key as View);
      }
    };
    parse();
    window.addEventListener("hashchange", parse);
    return () => window.removeEventListener("hashchange", parse);
  }, []);
  const navigate = useCallback((next: View) => {
    setSelected(null);
    setSelectedKnowledge(null);
    setView(next);
    location.hash = next;
    setSideOpen(false);
  }, []);
  const openProblem = useCallback((id: number) => {
    setSelected(id);
    setSelectedKnowledge(null);
    location.hash = `problem/${id}`;
    setSideOpen(false);
  }, []);
  const openKnowledge = useCallback((id: string) => {
    setSelected(null);
    setSelectedKnowledge(id);
    location.hash = `knowledge/${id}`;
    setSideOpen(false);
  }, []);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "k") {
        event.preventDefault();
        if (document.querySelector('[role="dialog"][aria-modal="true"]'))
          return;
        navigate("knowledge");
        setTimeout(
          () => document.getElementById("knowledge-search")?.focus(),
          80,
        );
      }
      if (event.key === "Escape") {
        setHelp(false);
        setSideOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate]);
  const mutate = useCallback(
    async (payload: unknown) => {
      try {
        const next = await action(payload);
        setState(next);
        return next;
      } catch (e) {
        notify((e as Error).message);
        throw e;
      }
    },
    [notify],
  );
  const favorite = (id: number) => {
    const itemId = projection.reverse.get(id);
    void mutate(
      itemId
        ? { type: "knowledge-favorite", itemId }
        : { type: "favorite", problemId: id },
    ).catch(() => {});
  };
  if (error)
    return (
      <div className="boot-screen">
        <div className="brand-mark">
          <img src="/gugugaga-icon.png" alt="GuGuGaGa" />
        </div>
        <h1>连接本地服务失败</h1>
        <p>{error}</p>
        <p>
          请运行 <code>python -m server.app</code>，然后刷新页面。
        </p>
        <button className="primary" onClick={() => location.reload()}>
          重新连接
        </button>
      </div>
    );
  if (!state || !capabilities)
    return (
      <div className="boot-screen">
        <div className="brand-mark">
          <img src="/gugugaga-icon.png" alt="GuGuGaGa" />
        </div>
        <LoaderCircle className="spin" />
        <p>正在打开你的学习工作台…</p>
      </div>
    );
  const projection = knowledgeProjection(problems, state);
  const workspaceName = state.settings.workspaceName || "我的工作空间";
  const openStudy = (id: number) => {
    const itemId = projection.reverse.get(id);
    if (itemId) openKnowledge(itemId);
    else openProblem(id);
  };
  const due = projection.planned.filter((p) =>
      isDue(projection.state.cards[p.id]),
    ),
    count = Object.keys(state.cards).length;
  const title = selectedKnowledge
    ? "知识复习"
    : selected
      ? "练习工作区"
      : view === "settings"
        ? "偏好设置"
        : navigation.find((n) => n.id === view)?.label;
  return (
    <div className="app-shell">
      {sideOpen && (
        <div className="sidebar-scrim" onClick={() => setSideOpen(false)} />
      )}
      <aside className={"sidebar " + (sideOpen ? "open" : "")}>
        <button className="brand" onClick={() => navigate("today")}>
          <span className="brand-mark">
            <img src="/gugugaga-icon.png" alt="" />
          </span>
          <span>
            GuGuGaGa<span className="brand-sub">任何知识，都值得记住</span>
          </span>
          <ChevronDown size={14} className="muted" />
        </button>
        <div className="sidebar-scroll">
          <button
            className="quick-search"
            onClick={() => {
              navigate("knowledge");
              setTimeout(
                () => document.getElementById("knowledge-search")?.focus(),
                80,
              );
            }}
          >
            <Search size={15} />
            <span>搜索知识</span>
            <kbd>⌃ K</kbd>
          </button>
          <div className="nav-label">工作空间</div>
          <nav>
            {navigation.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                className={
                  "nav-item " +
                  (view === id && !selected && !selectedKnowledge
                    ? "active"
                    : "")
                }
                onClick={() => navigate(id)}
              >
                <Icon size={17} />
                <span>{label}</span>
                {id === "review" && due.length > 0 && (
                  <span className="nav-count">{due.length}</span>
                )}
                {id === "library" && <span className="nav-tiny">100</span>}
              </button>
            ))}
          </nav>
          <div className="sidebar-section">
            <div className="nav-label">
              我的学习计划 <MoreHorizontal size={15} />
            </div>
            <button className="plan-link" onClick={() => navigate("path")}>
              <Folder size={16} />
              <span>LeetCode Hot 100</span>
            </button>
            <div className="sidebar-progress">
              <span style={{ width: `${count}%` }} />
            </div>
            <div className="sidebar-progress-label">
              <span>持续积累，直到掌握</span>
              <span>{count}/100</span>
            </div>
          </div>
          <div className="little-quote">
            <Sprout size={17} />
            <p>
              把看过的知识，
              <br />
              变成自己的能力。
            </p>
          </div>
        </div>
        <div className="sidebar-bottom">
          <button
            className={"nav-item " + (view === "settings" ? "active" : "")}
            onClick={() => navigate("settings")}
          >
            <Settings2 size={17} />
            <span>偏好设置</span>
          </button>
          <button className="nav-item" onClick={() => setHelp(true)}>
            <CircleHelp size={17} />
            <span>使用指南</span>
            <span className="nav-tiny">?</span>
          </button>
          <div className="profile">
            <button
              className="profile-account"
              aria-label="编辑个人资料"
              title="编辑名称和头像"
              onClick={() => {
                navigate("settings");
                requestAnimationFrame(() => {
                  document
                    .getElementById("profile-heading")
                    ?.scrollIntoView({ block: "center" });
                  document
                    .getElementById("profile-heading")
                    ?.focus({ preventScroll: true });
                });
              }}
            >
              <Avatar source={state.settings.avatar} />
              <span className="profile-details">
                <strong title={workspaceName}>{workspaceName}</strong>
                <span>
                  <i className="status-dot" />
                  本地存储
                </span>
              </span>
            </button>
            <button
              title="收起侧栏"
              className="icon-btn mobile-only"
              onClick={() => setSideOpen(false)}
            >
              <PanelLeftClose size={16} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-btn mobile-only"
              aria-label="打开侧栏"
              onClick={() => setSideOpen(true)}
            >
              <Menu size={18} />
            </button>
            <span className="workspace-name" title={workspaceName}>
              {workspaceName}
            </span>
            <ChevronRight size={13} />
            <strong>{title}</strong>
          </div>
          <div className="topbar-right">
            <button
              className="topbar-streak"
              title="查看连续打卡"
              onClick={() => navigate("calendar")}
            >
              <Flame size={20} fill="currentColor" />
              <strong>{streak(state)}</strong>
              <span>天</span>
            </button>
            <span className="top-divider" />
            <button
              className="icon-btn"
              title="复习提醒"
              onClick={() => navigate("review")}
            >
              <Bell size={17} />
              {due.length > 0 && <i className="notification-dot" />}
            </button>
            <button
              className="icon-btn"
              title="切换明暗主题"
              onClick={() =>
                void mutate({
                  type: "settings",
                  settings: {
                    theme: state.settings.theme === "light" ? "dark" : "light",
                  },
                }).catch(() => {})
              }
            >
              {state.settings.theme === "light" ? (
                <Moon size={17} />
              ) : (
                <Sun size={17} />
              )}
            </button>
          </div>
        </header>
        {selectedKnowledge ? (
          <KnowledgeStudy
            key={selectedKnowledge}
            id={selectedKnowledge}
            state={state}
            mutate={mutate}
            notify={notify}
            onBack={() => navigate("knowledge")}
            onOpen={openKnowledge}
          />
        ) : selected ? (
          <Suspense
            fallback={
              <div className="workspace-loading">
                <LoaderCircle className="spin" />
                <p>正在打开代码编辑器…</p>
              </div>
            }
          >
            <Workspace
              key={selected}
              id={selected}
              state={state}
              capabilities={capabilities}
              problems={problems}
              mutate={mutate}
              notify={notify}
              onBack={() => navigate(view)}
              onOpen={openProblem}
            />
          </Suspense>
        ) : (
          <main className="page-content">
            {view === "today" && (
              <LearningDashboard
                problems={projection.planned}
                state={projection.state}
                onOpen={openStudy}
                navigate={navigate}
              />
            )}
            {view === "knowledge" && (
              <Knowledge
                state={state}
                mutate={mutate}
                notify={notify}
                onOpen={openKnowledge}
              />
            )}
            {(view === "library" || view === "favorites") && (
              <Library
                problems={view === "favorites" ? projection.active : problems}
                state={view === "favorites" ? projection.state : state}
                onOpen={openStudy}
                onFavorite={favorite}
                categories={
                  view === "favorites"
                    ? [
                        ...new Set([
                          ...categories,
                          ...projection.active.map((p) => p.category),
                        ]),
                      ]
                    : categories
                }
                category={category}
                setCategory={setCategory}
                favoritesOnly={view === "favorites"}
              />
            )}
            {view === "review" && (
              <Review
                problems={projection.planned}
                state={projection.state}
                onOpen={openStudy}
              />
            )}
            {view === "calendar" && (
              <Calendar
                problems={projection.all}
                state={projection.state}
                onOpen={openStudy}
              />
            )}
            {view === "path" && (
              <PathView
                problems={problems}
                state={state}
                categories={categories}
                onCategory={(c) => {
                  setCategory(c);
                  navigate("library");
                }}
              />
            )}
            {view === "settings" && (
              <Settings
                state={state}
                capabilities={capabilities}
                mutate={mutate}
                notify={notify}
              />
            )}
          </main>
        )}
        {!selected && !selectedKnowledge && (
          <footer className="page-footer">
            <span>
              <img
                className="mini-brand-image"
                src="/gugugaga-icon.png"
                alt=""
              />{" "}
              GuGuGaGa <span className="footer-dot">·</span> 把练习变成长期记忆
            </span>
            <span>
              专注当下这一小步 <Sprout size={13} />
            </span>
          </footer>
        )}
      </div>
      {toast && (
        <div className="toast" role="status">
          <CircleCheck size={17} />
          <span>{toast}</span>
          <button className="icon-btn" onClick={() => setToast("")}>
            <X size={14} />
          </button>
        </div>
      )}
      {help && (
        <div className="modal-backdrop" onClick={() => setHelp(false)}>
          <section
            className="modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="使用指南"
          >
            <button
              className="icon-btn modal-close"
              onClick={() => setHelp(false)}
            >
              <X size={19} />
            </button>
            <img
              className="guide-brand-image"
              src="/gugugaga-icon.png"
              alt="GuGuGaGa"
            />
            <span className="eyebrow">WELCOME TO GUGUGAGA</span>
            <h2>让每一份知识，成为你的能力。</h2>
            <div className="guide-step">
              <b>01</b>
              <div>
                <h3>从今日计划开始</h3>
                <p>
                  知识库与 Hot100
                  共享每日目标和日历。先复习到期内容，再学习新知识，在设置中调整每天的节奏。
                </p>
              </div>
            </div>
            <div className="guide-step">
              <b>02</b>
              <div>
                <h3>加入自己的知识</h3>
                <p>
                  在「我的知识库」创建问答、填空或实践卡；导入 Markdown
                  笔记，按标题或通过 AI 拆分，预览编辑后导入。Hot100
                  仍支持双语言答题与个人题解。
                </p>
              </div>
            </div>
            <div className="guide-step">
              <b>03</b>
              <div>
                <h3>诚实反馈，按时复习</h3>
                <p>
                  选择「忘记了 / 有点模糊 / 记住了 /
                  很熟练」，系统会安排下一次复习。完成每日目标会自动打卡。
                </p>
              </div>
            </div>
            <div className="info-note">
              <Command size={16} />
              Ctrl / ⌘ + K 搜索知识，Ctrl / ⌘ + Enter 运行代码。
            </div>
            <button className="primary full" onClick={() => setHelp(false)}>
              开始积累 <ArrowRight size={16} />
            </button>
          </section>
        </div>
      )}
    </div>
  );
}

function PageHeading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}
function ProblemRow({
  problem,
  state,
  onOpen,
  number,
}: {
  problem: Problem;
  state: AppState;
  onOpen: (id: number) => void;
  number?: number;
}) {
  const card = state.cards[problem.id];
  return (
    <button className="problem-row" onClick={() => onOpen(problem.id)}>
      <span className="row-number">
        {String(number || problem.order).padStart(2, "0")}
      </span>
      <span className={"row-status " + (card ? "learned" : "")}>
        {card ? <CircleCheck size={18} /> : <Circle size={18} />}
      </span>
      <div className="row-main">
        <strong>
          {problem.title}
          {!problem.knowledgeId && (
            <span className="problem-id">#{problem.id}</span>
          )}
        </strong>
        <span>
          {problem.category}
          <span className="text-dot">·</span>
          {card ? dueLabel(card) : "新知 · 建立第一份记忆"}
        </span>
      </div>
      <Difficulty value={problem.difficulty} />
      <span className={"task-type " + (card ? "review" : "")}>
        {card ? "复习" : "新学"}
      </span>
      <ChevronRight className="row-arrow" size={16} />
    </button>
  );
}

function Library({
  problems,
  state,
  onOpen,
  onFavorite,
  categories,
  category,
  setCategory,
  favoritesOnly,
}: {
  problems: Problem[];
  state: AppState;
  onOpen: (id: number) => void;
  onFavorite: (id: number) => void;
  categories: string[];
  category: string;
  setCategory: (value: string) => void;
  favoritesOnly: boolean;
}) {
  const [search, setSearch] = useState(""),
    [difficulty, setDifficulty] = useState("全部难度"),
    [status, setStatus] = useState("全部状态");
  const filtered = problems.filter(
    (p) =>
      (!favoritesOnly || state.favorites.includes(p.id)) &&
      (category === "全部专题" || p.category === category) &&
      (difficulty === "全部难度" || p.difficulty === difficulty) &&
      (status === "全部状态" ||
        (status === "未学习"
          ? !state.cards[p.id]
          : status === "待复习"
            ? isDue(state.cards[p.id])
            : !!state.cards[p.id])) &&
      `${p.id} ${p.title} ${p.slug} ${p.category}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <PageHeading
        eyebrow={favoritesOnly ? "YOUR COLLECTION" : "THE ESSENTIAL 100"}
        title={
          favoritesOnly ? "值得再看一遍的题。" : "100 道题，一个扎实的起点。"
        }
        description={
          favoritesOnly
            ? "把薄弱点和好思路，留在离自己最近的地方。"
            : "精选高频题目，按专题建立知识之间的联系。"
        }
      >
        <span className="outline-badge">
          <Code2 size={15} />
          Python & C++
        </span>
      </PageHeading>
      <section className="panel library-panel">
        <div className="library-toolbar">
          <label className="search-field">
            <Search size={17} />
            <input
              id="problem-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索题号、名称或知识点…"
            />
            {search && (
              <button className="icon-btn" onClick={() => setSearch("")}>
                <X size={15} />
              </button>
            )}
          </label>
          <select
            aria-label="难度"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
          >
            {["全部难度", "简单", "中等", "困难"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
          <select
            aria-label="学习状态"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            {["全部状态", "未学习", "已学习", "待复习"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </div>
        <div className="category-chips">
          {["全部专题", ...categories].map((c) => (
            <button
              className={category === c ? "selected" : ""}
              key={c}
              onClick={() => setCategory(c)}
            >
              {c}
            </button>
          ))}
        </div>
        <div className="table-header">
          <span>
            题目 <b>{filtered.length}</b>
          </span>
          <span>专题</span>
          <span>难度</span>
          <span>状态</span>
          <span />
        </div>
        <div className="library-list">
          {filtered.map((p) => (
            <div className="library-row" key={p.id}>
              <button
                className="library-problem-name"
                onClick={() => onOpen(p.id)}
              >
                <span
                  className={
                    "row-status " + (state.cards[p.id] ? "learned" : "")
                  }
                >
                  {state.cards[p.id] ? (
                    <CircleCheck size={17} />
                  ) : (
                    <Circle size={17} />
                  )}
                </span>
                <span className="list-id">{p.id}</span>
                <strong>{p.title}</strong>
              </button>
              <span className="table-category">{p.category}</span>
              <Difficulty value={p.difficulty} />
              <span
                className={
                  "table-state " + (isDue(state.cards[p.id]) ? "due" : "")
                }
              >
                {dueLabel(state.cards[p.id])}
              </span>
              <button
                aria-label={
                  state.favorites.includes(p.id) ? "取消收藏" : "收藏题目"
                }
                className={
                  "icon-btn favorite " +
                  (state.favorites.includes(p.id) ? "starred" : "")
                }
                onClick={() => onFavorite(p.id)}
              >
                <Star
                  size={16}
                  fill={
                    state.favorites.includes(p.id) ? "currentColor" : "none"
                  }
                />
              </button>
            </div>
          ))}
          {!filtered.length && (
            <Empty
              icon={favoritesOnly ? Star : Search}
              title={favoritesOnly ? "还没有收藏的题目" : "没有找到匹配的题目"}
            >
              {favoritesOnly
                ? "点击题目旁的星标，把好题收入你的收藏夹。"
                : "试试其他关键词，或调整上方筛选条件。"}
            </Empty>
          )}
        </div>
        <div className="panel-bottom">
          <span>题目与解析支持离线使用 · 原题入口见题目详情</span>
          <span>共 {filtered.length} 题</span>
        </div>
      </section>
    </>
  );
}

function Review({
  problems,
  state,
  onOpen,
}: {
  problems: Problem[];
  state: AppState;
  onOpen: (id: number) => void;
}) {
  const [tab, setTab] = useState("到期复习");
  const now = new Date(),
    learned = problems.filter((p) => state.cards[p.id]);
  const due = learned.filter((p) => isDue(state.cards[p.id]));
  const upcoming = learned.filter(
    (p) =>
      !isDue(state.cards[p.id]) &&
      new Date(state.cards[p.id].due) <= dateShift(now, 7),
  );
  const list = (
    tab === "到期复习" ? due : tab === "未来 7 天" ? upcoming : learned
  ).sort(
    (a, b) =>
      new Date(state.cards[a.id].due).getTime() -
      new Date(state.cards[b.id].due).getTime(),
  );
  const average = learned.length
    ? Math.round(
        (learned.reduce((sum, p) => sum + retention(state.cards[p.id]), 0) /
          learned.length) *
          100,
      )
    : 0;
  return (
    <>
      <PageHeading
        eyebrow="A LITTLE RECALL GOES A LONG WAY"
        title="在遗忘之前，再见一面。"
        description="根据每次记忆反馈，动态调整下一次复习时间。"
      >
        <button
          className="primary"
          disabled={!due.length}
          onClick={() => due[0] && onOpen(due[0].id)}
        >
          <RotateCcw size={16} />
          开始复习{" "}
          {due.length > 0 && (
            <span className="button-shortcut">{due.length}</span>
          )}
        </button>
      </PageHeading>
      <div className="review-summary">
        <div>
          <span>现在需要复习</span>
          <strong>
            {due.length}
            <small>项</small>
          </strong>
        </div>
        <div>
          <span>未来七天安排</span>
          <strong>
            {upcoming.length}
            <small>项</small>
          </strong>
        </div>
        <div>
          <span>预计记忆保留率</span>
          <strong>
            {learned.length ? average : "—"}
            <small>{learned.length ? "%" : ""}</small>
          </strong>
        </div>
        <div>
          <span>累计主动回忆</span>
          <strong>
            {state.events.filter((e) => e.kind === "review").length}
            <small>次</small>
          </strong>
        </div>
      </div>
      <div className="dashboard-columns">
        <section className="panel">
          <div className="tabs-bar large-tabs">
            {["到期复习", "未来 7 天", "全部已学"].map((t) => (
              <button
                className={tab === t ? "selected" : ""}
                key={t}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
          </div>
          {list.map((p, i) => (
            <div className="review-row" key={p.id}>
              <ProblemRow
                problem={p}
                state={state}
                onOpen={onOpen}
                number={i + 1}
              />
              <div className="review-detail">
                <span>回忆 {state.cards[p.id].reviews} 次</span>
                <div className="retention-track">
                  <span
                    style={{ width: `${retention(state.cards[p.id]) * 100}%` }}
                  />
                </div>
                <span>
                  {Math.round(retention(state.cards[p.id]) * 100)}% 预计保留
                </span>
              </div>
            </div>
          ))}
          {!list.length && (
            <Empty
              icon={CheckCheck}
              title={
                tab === "到期复习" ? "目前没有到期内容" : "记忆正在慢慢建立"
              }
            >
              完成学习并提交反馈，即可生成复习计划。
            </Empty>
          )}
        </section>
        <aside>
          <section className="panel memory-panel">
            <div className="mini-section-title">
              <span className="tint-icon">
                <Sprout size={16} />
              </span>
              <h3>你的记忆，值得被照顾</h3>
            </div>
            <MemoryChart />
            <p className="small-copy">曲线展示预计记忆保留率。</p>
            <div className="rating-explain">
              <div>
                <i className="rating-dot again" />
                <b>忘记了</b>
                <span>10 分钟后再试</span>
              </div>
              <div>
                <i className="rating-dot hard" />
                <b>有点模糊</b>
                <span>缩短复习间隔</span>
              </div>
              <div>
                <i className="rating-dot good" />
                <b>记住了</b>
                <span>逐步延长间隔</span>
              </div>
              <div>
                <i className="rating-dot easy" />
                <b>很熟练</b>
                <span>安排更远的复习</span>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}

function Calendar({
  problems,
  state,
  onOpen,
}: {
  problems: Problem[];
  state: AppState;
  onOpen: (id: number) => void;
}) {
  const [month, setMonth] = useState(
      () => new Date(new Date().getFullYear(), new Date().getMonth(), 1),
    ),
    [selected, setSelected] = useState(dayKey());
  const offset = (month.getDay() + 6) % 7,
    days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate(),
    cells = Math.ceil((offset + days) / 7) * 7;
  const selectedEvents = state.events.filter((e) => e.day === selected),
    monthPrefix = dayKey(month).slice(0, 7),
    monthEvents = state.events.filter((e) => e.day.startsWith(monthPrefix));
  return (
    <>
      <PageHeading
        eyebrow="SMALL STEPS, VISIBLE PROGRESS"
        title="每一份坚持，都有迹可循。"
        description="回头看，你已经比昨天多走了一点。"
      >
        <span className="outline-badge">
          <Flame size={15} />
          累计打卡 {state.checkins.length} 天
        </span>
      </PageHeading>
      <div className="calendar-layout">
        <section className="panel calendar-panel">
          <div className="panel-heading">
            <h2>
              {month.getFullYear()} 年 {month.getMonth() + 1} 月
            </h2>
            <div className="calendar-controls">
              <button
                className="icon-btn"
                aria-label="上个月"
                onClick={() =>
                  setMonth(
                    new Date(month.getFullYear(), month.getMonth() - 1, 1),
                  )
                }
              >
                <ChevronLeft size={17} />
              </button>
              <button
                className="text-button"
                onClick={() => {
                  setMonth(
                    new Date(
                      new Date().getFullYear(),
                      new Date().getMonth(),
                      1,
                    ),
                  );
                  setSelected(dayKey());
                }}
              >
                今天
              </button>
              <button
                className="icon-btn"
                aria-label="下个月"
                onClick={() =>
                  setMonth(
                    new Date(month.getFullYear(), month.getMonth() + 1, 1),
                  )
                }
              >
                <ChevronRight size={17} />
              </button>
            </div>
          </div>
          <div className="calendar-grid weekdays">
            {["周一", "周二", "周三", "周四", "周五", "周六", "周日"].map(
              (d) => (
                <span key={d}>{d}</span>
              ),
            )}
          </div>
          <div className="calendar-grid">
            {Array.from({ length: cells }, (_, i) => {
              const date = new Date(
                  month.getFullYear(),
                  month.getMonth(),
                  i - offset + 1,
                ),
                key = dayKey(date),
                outside = date.getMonth() !== month.getMonth(),
                events = state.events.filter((e) => e.day === key),
                count = new Set(events.map((e) => e.problemId)).size,
                check = state.checkins.includes(key);
              return (
                <button
                  key={key}
                  aria-label={`${key}，学习 ${count} 项`}
                  onClick={() => setSelected(key)}
                  className={`calendar-cell ${outside ? "outside" : ""} ${selected === key ? "selected" : ""} ${key === dayKey() ? "today" : ""} ${count ? "has-activity" : ""}`}
                >
                  <span className="calendar-day">
                    {date.getDate()}
                    {check && <CircleCheck size={13} />}
                  </span>
                  {count > 0 ? (
                    <span className="calendar-activity">
                      {count} 项<small>{check ? "已打卡" : "学习中"}</small>
                    </span>
                  ) : key === dayKey() ? (
                    <span className="calendar-today-label">今天</span>
                  ) : null}
                </button>
              );
            })}
          </div>
          <div className="panel-bottom">
            <span>
              <i className="status-dot" />
              绿色表示有学习记录
            </span>
            <span>
              本月学习 {new Set(monthEvents.map((e) => e.problemId)).size} 项 ·
              打卡{" "}
              {state.checkins.filter((d) => d.startsWith(monthPrefix)).length}{" "}
              天
            </span>
          </div>
        </section>
        <aside className="panel calendar-detail">
          <div className="panel-heading">
            <div>
              <h2>
                {Number(selected.slice(5, 7))} 月 {Number(selected.slice(8))} 日
              </h2>
              <p>
                {state.checkins.includes(selected)
                  ? "今日目标已完成"
                  : "记录属于这一天的积累"}
              </p>
            </div>
            <CalendarDays size={20} className="muted" />
          </div>
          {selectedEvents.length ? (
            <>
              <div className="day-stats">
                <div>
                  <b>{new Set(selectedEvents.map((e) => e.problemId)).size}</b>
                  <span>完成内容</span>
                </div>
                <div>
                  <b>
                    {Math.max(
                      1,
                      Math.round(
                        selectedEvents.reduce((s, e) => s + e.seconds, 0) / 60,
                      ),
                    )}
                  </b>
                  <span>专注分钟</span>
                </div>
              </div>
              <div className="timeline">
                {selectedEvents.map((e) => (
                  <button key={e.eventId} onClick={() => onOpen(e.problemId)}>
                    <span className={"timeline-dot " + e.rating} />
                    <div>
                      <strong>
                        {problems.find((p) => p.id === e.problemId)?.title}
                      </strong>
                      <p>
                        {e.kind === "new" ? "新学" : "复习"}
                        <span className="text-dot">·</span>
                        {ratingLabels[e.rating]}
                      </p>
                    </div>
                    <small>
                      {new Date(e.time).toLocaleTimeString("zh-CN", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </small>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <Empty icon={CalendarDays} title="这一天，等待被点亮">
              每一次学习和复习，都会留下一枚足迹。
            </Empty>
          )}
        </aside>
      </div>
    </>
  );
}

function PathView({
  problems,
  state,
  categories,
  onCategory,
}: {
  problems: Problem[];
  state: AppState;
  categories: string[];
  onCategory: (c: string) => void;
}) {
  return (
    <>
      <PageHeading
        eyebrow="CONNECT THE DOTS"
        title="把零散的题，连成知识。"
        description="参考代码随想录的专题脉络，循序渐进地走过 Hot100。"
      />
      <div className="path-intro">
        <Layers size={20} />
        <div>
          <strong>一条清晰的学习路线</strong>
          <p>先打牢数组、链表与哈希表基础，再走向树、回溯、动态规划与图论。</p>
        </div>
        <span>{categories.length} 个专题</span>
      </div>
      <div className="path-grid">
        {categories.map((cat, i) => {
          const items = problems.filter((p) => p.category === cat),
            done = items.filter((p) => state.cards[p.id]).length;
          return (
            <button
              className="panel path-card"
              key={cat}
              onClick={() => onCategory(cat)}
            >
              <div className="path-card-top">
                <span className="path-symbol">{categoryIcons[cat] || "⌘"}</span>
                <span className="path-number">
                  {String(i + 1).padStart(2, "0")}
                </span>
              </div>
              <h2>
                {cat}
                <ArrowRight size={17} />
              </h2>
              <p>
                {items
                  .slice(0, 3)
                  .map((p) => p.title)
                  .join(" · ")}
              </p>
              <div className="progress-track">
                <span style={{ width: `${(done / items.length) * 100}%` }} />
              </div>
              <div className="path-card-bottom">
                <span>
                  {done} / {items.length} 题已学习
                </span>
                <span>{Math.round((done / items.length) * 100)}%</span>
              </div>
            </button>
          );
        })}
      </div>
    </>
  );
}

function Settings({
  state,
  capabilities,
  mutate,
  notify,
}: {
  state: AppState;
  capabilities: Capabilities;
  mutate: (p: unknown) => Promise<AppState>;
  notify: (m: string) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null),
    [importing, setImporting] = useState(false),
    [pendingImport, setPendingImport] = useState<unknown>(null);
  const setting = (settings: Record<string, unknown>) =>
    void mutate({ type: "settings", settings })
      .then(() => notify("偏好已保存"))
      .catch(() => {});
  const readBackup = async (file?: File) => {
    if (!file) return;
    try {
      if (file.size > 64 * 1024 * 1024)
        throw new Error("备份文件不能超过 64 MB");
      const data = JSON.parse((await file.text()).replace(/^\uFEFF/, ""));
      if (!data || ![1, 2].includes(data.version))
        throw new Error("不支持的备份版本；知识库文件请到「我的知识库」导入");
      setPendingImport(data);
    } catch (e) {
      notify((e as Error).message);
    }
    if (fileRef.current) fileRef.current.value = "";
  };
  return (
    <>
      <PageHeading
        eyebrow="MAKE IT YOURS"
        title="找到适合自己的节奏。"
        description="轻一点的目标，长一点的坚持。"
      />
      <div className="settings-grid">
        <AvatarSettings
          avatar={state.settings.avatar}
          workspaceName={state.settings.workspaceName}
          mutate={mutate}
          notify={notify}
        />
        <section className="panel settings-panel">
          <h2>
            <Target size={18} />
            学习偏好
          </h2>
          <div className="setting-row">
            <div>
              <strong>每日打卡目标</strong>
              <p>题目与知识点合计达到每日目标，自动打卡。</p>
            </div>
            <select
              aria-label="每日打卡目标"
              value={state.settings.dailyGoal}
              onChange={(e) => setting({ dailyGoal: Number(e.target.value) })}
            >
              {Array.from({ length: 30 }, (_, i) => (
                <option value={i + 1} key={i}>
                  {i + 1} 项 / 天
                </option>
              ))}
            </select>
          </div>
          <div className="setting-row">
            <div>
              <strong>每日新知推荐</strong>
              <p>先复习，再学习新知识。所有知识库共享新学额度。</p>
            </div>
            <select
              aria-label="每日新知推荐"
              value={state.settings.newPerDay}
              onChange={(e) => setting({ newPerDay: Number(e.target.value) })}
            >
              {Array.from({ length: 10 }, (_, i) => (
                <option key={i} value={i + 1}>
                  {i + 1} 项 / 天
                </option>
              ))}
            </select>
          </div>
          <div className="setting-row">
            <div>
              <strong>每日计划包含 Hot100</strong>
              <p>将 Hot100 练习纳入每日计划。</p>
            </div>
            <input
              aria-label="每日计划包含 Hot100"
              type="checkbox"
              checked={state.settings.includeHot100 !== false}
              onChange={(e) => setting({ includeHot100: e.target.checked })}
            />
          </div>
          <div className="setting-row">
            <div>
              <strong>目标记忆保留率</strong>
              <p>应用于后续复习，数值越高，安排越频繁。</p>
            </div>
            <select
              aria-label="目标记忆保留率"
              value={state.settings.retention}
              onChange={(e) => setting({ retention: Number(e.target.value) })}
            >
              {[0.8, 0.85, 0.9, 0.95].map((n) => (
                <option value={n} key={n}>
                  {n * 100}%{n === 0.9 ? "（推荐）" : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="setting-row">
            <div>
              <strong>默认编程语言</strong>
              <p>两种语言使用相同算法与完整解析。</p>
            </div>
            <select
              aria-label="默认编程语言"
              value={state.settings.language}
              onChange={(e) => setting({ language: e.target.value })}
            >
              <option value="python">Python 3</option>
              <option value="cpp">C++ 17</option>
            </select>
          </div>
          <div className="setting-row">
            <div>
              <strong>默认答题模式</strong>
              <p>函数提交，或自己完成标准输入输出。</p>
            </div>
            <select
              aria-label="默认答题模式"
              value={state.settings.mode}
              onChange={(e) => setting({ mode: e.target.value })}
            >
              <option value="leetcode">LeetCode 模式</option>
              <option value="acm">ACM 模式</option>
            </select>
          </div>
        </section>
        <section className="panel settings-panel">
          <h2>
            <Folder size={18} />
            数据与运行环境
          </h2>
          <div className="setting-block">
            <strong>本地数据与备份</strong>
            <p>学习数据保存在本机，支持导入和导出备份。</p>
            <div className="button-group">
              <button
                className="secondary"
                onClick={() => {
                  download(`GuGuGaGa-${dayKey()}.json`, JSON.stringify(state));
                  notify("备份已导出");
                }}
              >
                <ArrowDownToLine size={15} />
                导出备份
              </button>
              <button
                className="secondary"
                onClick={() => fileRef.current?.click()}
              >
                <Upload size={15} />
                导入备份
              </button>
              <input
                type="file"
                accept="application/json,.json"
                ref={fileRef}
                hidden
                onChange={(e) => void readBackup(e.target.files?.[0])}
              />
            </div>
          </div>
          <div className="runtime-status">
            <div>
              <Code2 size={17} />
              <strong>Python {capabilities.python.version}</strong>
              <span className="runtime-ready">
                <i className="status-dot" />
                可运行
              </span>
            </div>
            <div>
              <Code2 size={17} />
              <strong>C++ 17</strong>
              <span
                className={
                  capabilities.cpp.available ? "runtime-ready" : "muted"
                }
              >
                {capabilities.cpp.available ? "可运行" : "未配置编译器"}
              </span>
            </div>
            {!capabilities.cpp.available && (
              <p>
                安装 g++ / clang++ 并加入 PATH，或设置环境变量{" "}
                <code>CODERECALL_CXX</code> 为编译器路径，然后重启应用。
              </p>
            )}
          </div>
          <div className="info-note">在本机执行样例测试，请运行可信代码。</div>
        </section>
        <section className="panel settings-panel sources-panel">
          <h2>
            <BookOpen size={18} />
            关于这份学习工具
          </h2>
          <p>GuGuGaGa 将知识整理、代码练习与间隔复习结合，帮助你持续学习。</p>
          <div className="source-links">
            <a
              href="https://leetcode.cn/studyplan/top-100-liked/"
              target="_blank"
              rel="noreferrer"
            >
              <Code2 size={16} />
              LeetCode Hot 100 <ArrowRight size={14} />
            </a>
            <a
              href="https://github.com/youngyangyang04/leetcode-master"
              target="_blank"
              rel="noreferrer"
            >
              <Github size={16} />
              代码随想录 · 分类参考 <ArrowRight size={14} />
            </a>
            <a
              href="https://github.com/maimemo/SSP-MMC"
              target="_blank"
              rel="noreferrer"
            >
              <Github size={16} />
              墨墨 · 间隔重复研究 <ArrowRight size={14} />
            </a>
          </div>
        </section>
      </div>
      {pendingImport !== null && (
        <div className="modal-backdrop">
          <section className="modal" role="dialog" aria-modal="true">
            <h2>导入这份学习备份？</h2>
            <p>
              导入将替换当前知识库、个人题解、进度、设置、笔记与草稿。应用会先把现有数据自动备份到数据库所在的数据目录。
            </p>
            <div className="button-group">
              <button
                className="secondary"
                disabled={importing}
                onClick={() => setPendingImport(null)}
              >
                取消
              </button>
              <button
                className="primary"
                disabled={importing}
                onClick={() => {
                  setImporting(true);
                  void mutate({ type: "import", state: pendingImport })
                    .then(() => {
                      Object.keys(localStorage)
                        .filter(
                          (key) =>
                            key.startsWith("coderecall-pending-") ||
                            key.startsWith("coderecall-note-") ||
                            key.startsWith("coderecall-knowledge-note-") ||
                            key.startsWith("coderecall-solution-"),
                        )
                        .forEach((key) => localStorage.removeItem(key));
                      notify("学习备份已恢复");
                      setPendingImport(null);
                    })
                    .catch(() => {})
                    .finally(() => setImporting(false));
                }}
              >
                {importing ? (
                  <LoaderCircle className="spin" size={16} />
                ) : (
                  <Upload size={16} />
                )}
                确认导入
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
