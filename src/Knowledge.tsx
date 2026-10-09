import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  Archive,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  FileText,
  FolderPlus,
  Layers,
  LoaderCircle,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  Sparkles,
  Star,
  Upload,
  X,
} from "lucide-react";
import type {
  AppState,
  KnowledgeDeck,
  KnowledgeDocument,
  KnowledgeItem,
  KnowledgeKind,
  Rating,
} from "./types";
import { splitDocument, validateDocument } from "./api";
import { dayKey, download, dueLabel, isDue, ratingLabels } from "./utils";
import Markdown from "./Markdown";
import { knowledgeSamples } from "./knowledgeSamples";
import {
  confirmedStudy,
  RatingSymbol,
  StudyFeedback,
  StudyProgress,
} from "./StudyFeedback";
import type { ConfirmedStudy } from "./StudyFeedback";
import "./knowledge.css";

interface Shared {
  state: AppState;
  mutate: (payload: unknown) => Promise<AppState>;
  notify: (message: string) => void;
}
const kinds: Record<KnowledgeKind, string> = {
  qa: "问答卡",
  cloze: "填空卡",
  procedure: "实践清单",
};
const blankItem = {
  title: "",
  kind: "qa" as KnowledgeKind,
  prompt: "",
  answer: "",
  tags: [],
  source: "",
};

function Dialog({
  title,
  close,
  children,
  wide = false,
}: {
  title: string;
  close: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef(close);
  closeRef.current = close;
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    const focusable = () =>
      Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled), input:not(:disabled):not([type=hidden]), select:not(:disabled), textarea:not(:disabled), a[href]",
        ) || [],
      ).filter((el) => el.offsetParent !== null);
    const first =
      dialogRef.current?.querySelector<HTMLElement>(
        "input:not([type=hidden]), textarea, select",
      ) || focusable()[0];
    first?.focus();
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        closeRef.current();
      } else if (event.key === "Tab") {
        const elements = focusable();
        const firstElement = elements[0],
          last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === firstElement) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          firstElement?.focus();
        }
      }
    };
    document.addEventListener("keydown", handler);
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = old;
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, []);
  return (
    <div className="modal-backdrop knowledge-backdrop">
      <section
        ref={dialogRef}
        className={`knowledge-dialog ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="knowledge-dialog-heading">
          <div>
            <span className="eyebrow">YOUR PERSONAL KNOWLEDGE</span>
            <h2>{title}</h2>
          </div>
          <button className="icon-btn" aria-label="关闭对话框" onClick={close}>
            <X size={20} />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

export function DeckEditor({
  deck,
  mutate,
  notify,
  close,
}: Shared & { deck?: KnowledgeDeck; close: () => void }) {
  const [title, setTitle] = useState(deck?.title || "");
  const [description, setDescription] = useState(deck?.description || "");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const dismiss = () => {
    if (
      !busy &&
      ((title === (deck?.title || "") &&
        description === (deck?.description || "")) ||
        confirm("放弃未保存的知识库编辑？"))
    )
      close();
  };
  return (
    <Dialog title={deck ? "编辑知识库" : "新建知识库"} close={dismiss}>
      <form
        className="knowledge-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            await mutate({
              type: "deck-save",
              deck: { ...(deck ? { id: deck.id } : {}), title, description },
            });
            notify("知识库已保存");
            close();
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          知识库名称
          <input
            disabled={busy}
            autoFocus
            required
            maxLength={200}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="例如：C++ 学习 / 英语 / Blender / UE5"
          />
        </label>
        <label>
          学习目标
          <textarea
            disabled={busy}
            rows={3}
            maxLength={5000}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="准备在这个知识库里积累什么？"
          />
        </label>
        {error && (
          <p className="knowledge-error" role="alert">
            {error}
          </p>
        )}
        <div className="knowledge-actions">
          <button
            type="button"
            className="secondary"
            onClick={dismiss}
            disabled={busy}
          >
            取消
          </button>
          <button className="primary" disabled={busy}>
            {busy && <LoaderCircle size={15} className="spin" />}保存知识库
          </button>
        </div>
      </form>
    </Dialog>
  );
}

export function ItemEditor({
  item,
  deckId,
  state,
  mutate,
  notify,
  close,
}: Shared & { item?: KnowledgeItem; deckId?: string; close: () => void }) {
  const initial = item || {
    ...blankItem,
    deckId: deckId || Object.keys(state.decks)[0] || "",
  };
  const [draft, setDraft] = useState(initial),
    [tags, setTags] = useState(initial.tags.join(", "));
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const dirty =
    JSON.stringify(initial) !== JSON.stringify(draft) ||
    tags !== initial.tags.join(", ");
  const dismiss = () => {
    if (!busy && (!dirty || confirm("放弃未保存的知识点编辑？"))) close();
  };
  return (
    <Dialog title={item ? "编辑知识点" : "新建知识点"} close={dismiss} wide>
      <form
        className="knowledge-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            await mutate({
              type: "knowledge-save",
              item: {
                ...(item ? { id: item.id } : {}),
                deckId: draft.deckId,
                title: draft.title,
                kind: draft.kind,
                prompt: draft.prompt,
                answer: draft.answer,
                tags: tags
                  .split(/[,，]/)
                  .map((s) => s.trim())
                  .filter(Boolean),
                source: draft.source,
              },
            });
            notify("知识点已保存，学习后会自动安排复习");
            close();
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="knowledge-form-row">
          <label>
            所属知识库
            <select
              disabled={busy}
              required
              value={draft.deckId}
              onChange={(e) => setDraft({ ...draft, deckId: e.target.value })}
            >
              {Object.values(state.decks).map((d) => (
                <option value={d.id} key={d.id}>
                  {d.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            卡片类型
            <select
              disabled={busy}
              value={draft.kind}
              onChange={(e) =>
                setDraft({ ...draft, kind: e.target.value as KnowledgeKind })
              }
            >
              {Object.entries(kinds).map(([key, name]) => (
                <option value={key} key={key}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label>
          知识点标题
          <input
            disabled={busy}
            required
            maxLength={300}
            value={draft.title}
            onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            placeholder="一个知识点，解决一个小问题"
          />
        </label>
        <div className="knowledge-form-row">
          <label>
            问题 / 练习要求
            <textarea
              disabled={busy}
              required
              rows={7}
              maxLength={100000}
              value={draft.prompt}
              onChange={(e) => setDraft({ ...draft, prompt: e.target.value })}
              placeholder={
                draft.kind === "cloze"
                  ? "使用 {{c1::答案}} 标记填空，例如：I {{c1::recall}} it."
                  : "用问题引导回忆，支持 Markdown。"
              }
            />
          </label>
          <label>
            答案 / 验收清单
            <textarea
              disabled={busy}
              required
              rows={7}
              maxLength={100000}
              value={draft.answer}
              onChange={(e) => setDraft({ ...draft, answer: e.target.value })}
              placeholder="写下自己的理解、示例、操作步骤或验收清单。支持 Markdown。"
            />
          </label>
        </div>
        {draft.kind === "cloze" && (
          <p className="knowledge-hint">
            复习时会隐藏问题中所有 {"{{c1::答案}}"}{" "}
            标记；点击显示答案后统一揭晓。
          </p>
        )}
        <div className="knowledge-form-row">
          <label>
            标签
            <input
              disabled={busy}
              maxLength={1800}
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="概念, 易错, 需要实践"
            />
          </label>
          <label>
            来源 / 参考链接
            <input
              disabled={busy}
              maxLength={2000}
              value={draft.source}
              onChange={(e) => setDraft({ ...draft, source: e.target.value })}
              placeholder="文档名称、章节或网址"
            />
          </label>
        </div>
        {error && (
          <p role="alert" className="knowledge-error">
            {error}
          </p>
        )}
        <div className="knowledge-actions">
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={dismiss}
          >
            取消
          </button>
          <button className="primary" disabled={busy}>
            {busy && <LoaderCircle size={15} className="spin" />}保存知识点
          </button>
        </div>
      </form>
    </Dialog>
  );
}

export function ImportKnowledge({
  state,
  mutate,
  notify,
  close,
  sample,
}: Shared & { close: () => void; sample?: KnowledgeDocument }) {
  const [tab, setTab] = useState<"document" | "json">("document");
  const [text, setText] = useState(""),
    [deckTitle, setDeckTitle] = useState("我的学习笔记");
  const [mode, setMode] = useState<"local" | "ai">("local");
  const [endpoint, setEndpoint] = useState(""),
    [model, setModel] = useState(""),
    [apiKey, setApiKey] = useState("");
  const [preview, setPreview] = useState<KnowledgeDocument | null>(
    sample || null,
  );
  const [selected, setSelected] = useState<Set<number>>(
    new Set(sample?.items.map((_, i) => i) || []),
  );
  const [index, setIndex] = useState(0),
    [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const dismiss = () => {
    if (
      !busy &&
      (!(text.trim() || preview) ||
        confirm("关闭导入预览？尚未导入的内容不会保存。"))
    )
      close();
  };
  const acceptPreview = (document: KnowledgeDocument) => {
    setPreview(document);
    setSelected(new Set(document.items.map((_, i) => i)));
    setIndex(0);
    setEditing(false);
  };
  const previewCurrent = preview?.items[index];
  const editItem = (patch: Partial<KnowledgeDocument["items"][number]>) =>
    setPreview(
      (p) =>
        p && {
          ...p,
          items: p.items.map((item, i) =>
            i === index ? { ...item, ...patch } : item,
          ),
        },
    );
  const generate = async () => {
    setBusy(true);
    setError("");
    try {
      const doc =
        tab === "json"
          ? await validateDocument(JSON.parse(text.replace(/^\uFEFF/, "")))
          : await splitDocument({
              text,
              deckTitle,
              mode,
              ...(mode === "ai" ? { endpoint, model, apiKey } : {}),
            });
      acceptPreview(doc);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setApiKey("");
      setBusy(false);
    }
  };
  const importPreview = async () => {
    if (!preview || !selected.size) return;
    setBusy(true);
    setError("");
    try {
      const document = {
        ...preview,
        items: preview.items.filter((_, i) => selected.has(i)),
      };
      const before = Object.keys(state.knowledge).length;
      const next = await mutate({ type: "knowledge-import", document });
      notify(
        `导入完成 · 新增 ${Object.keys(next.knowledge).length - before} 个知识点，已存在的相同内容自动跳过`,
      );
      close();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog title="将笔记变成可复习的知识" close={dismiss} wide>
      <div className="knowledge-import-steps">
        <span className={!preview ? "active" : ""}>1 选择内容</span>
        <ArrowRight size={14} />
        <span className={preview ? "active" : ""}>2 检查与编辑</span>
        <ArrowRight size={14} />
        <span>3 导入知识库</span>
      </div>
      {!preview ? (
        <div className="knowledge-form">
          <div className="segmented">
            <button
              className={tab === "document" ? "selected" : ""}
              onClick={() => setTab("document")}
              disabled={busy}
            >
              笔记文档 .md / .txt
            </button>
            <button
              className={tab === "json" ? "selected" : ""}
              onClick={() => setTab("json")}
              disabled={busy}
            >
              标准知识库 .json
            </button>
          </div>
          {tab === "document" && (
            <>
              <label>
                导入为知识库
                <input
                  maxLength={200}
                  value={deckTitle}
                  onChange={(e) => setDeckTitle(e.target.value)}
                  disabled={busy}
                />
              </label>
              <div className="knowledge-mode-choices">
                <button
                  className={mode === "local" ? "selected" : ""}
                  disabled={busy}
                  onClick={() => setMode("local")}
                >
                  <FileText size={18} />
                  <b>本地按标题拆分</b>
                  <span>离线使用，按 Markdown 章节生成问答卡</span>
                </button>
                <button
                  className={mode === "ai" ? "selected" : ""}
                  disabled={busy}
                  onClick={() => setMode("ai")}
                >
                  <Sparkles size={18} />
                  <b>使用大模型整理</b>
                  <span>提取知识点，生成适合主动回忆的问题</span>
                </button>
              </div>
              {mode === "ai" && (
                <div className="knowledge-ai-settings">
                  <label>
                    API 基础地址
                    <input
                      disabled={busy}
                      type="url"
                      placeholder="https://你的服务商/v1 或 http://localhost:11434/v1"
                      value={endpoint}
                      onChange={(e) => setEndpoint(e.target.value)}
                    />
                  </label>
                  <div className="knowledge-form-row">
                    <label>
                      模型名称
                      <input
                        disabled={busy}
                        value={model}
                        onChange={(e) => setModel(e.target.value)}
                        placeholder="填写服务商提供的模型 ID"
                      />
                    </label>
                    <label>
                      API Key（本次使用）
                      <input
                        disabled={busy}
                        type="password"
                        autoComplete="off"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder="本地服务可留空"
                      />
                    </label>
                  </div>
                  <p className="knowledge-hint">
                    使用 Chat Completions
                    接口发送文档，费用按服务商计费。生成后可预览编辑。
                  </p>
                </div>
              )}
            </>
          )}
          <div className="knowledge-file-bar">
            <button
              className="secondary"
              disabled={busy}
              onClick={() => fileRef.current?.click()}
            >
              <Upload size={15} />
              读取文件
            </button>
            <span>
              {tab === "document"
                ? "UTF-8 文本，最多 20 万字；大文档请分章节处理"
                : "coderecall.knowledge v1，最多 8 MB / 1000 个知识点"}
            </span>
            <input
              ref={fileRef}
              type="file"
              hidden
              accept={
                tab === "document"
                  ? ".md,.txt,text/plain,text/markdown"
                  : ".json,application/json"
              }
              onChange={async (e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (!file) return;
                if (file.size > 8 * 1024 * 1024) {
                  setError("文件最多 8 MB");
                  return;
                }
                try {
                  const contents = (await file.text()).replace(/^\uFEFF/, "");
                  setText(contents);
                  setError("");
                  if (tab === "document")
                    setDeckTitle(file.name.replace(/\.[^.]+$/, ""));
                } catch {
                  setError("无法读取此文件，请使用 UTF-8 编码的文本。");
                }
              }}
            />
          </div>
          <label>
            {tab === "document" ? "笔记内容" : "知识库 JSON"}
            <textarea
              rows={9}
              disabled={busy}
              maxLength={tab === "document" ? 200000 : 8000000}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={
                tab === "document"
                  ? "# 第一章\n## 一个重要概念\n解释、示例与操作步骤…\n\n## 另一个知识点\n…"
                  : '{ "format": "coderecall.knowledge", "version": 1, "deck": { "title": "我的知识库" }, "items": […] }'
              }
            />
          </label>
          <div className="knowledge-file-bar">
            <a
              href="/knowledge-template.json"
              download="knowledge-template.json"
              className="text-button"
            >
              <ArrowDownToLine size={14} />
              下载导入模板
            </a>
            <a
              href="/knowledge-schema.json"
              target="_blank"
              rel="noreferrer"
              className="text-button"
            >
              查看 JSON Schema
            </a>
            <span>也可让外部 AI 按模板生成 JSON，再在这里导入。</span>
          </div>
          <div className="knowledge-actions">
            <button
              className="primary"
              disabled={
                busy ||
                !text.trim() ||
                (tab === "document" &&
                  (!deckTitle.trim() ||
                    (mode === "ai" && (!endpoint.trim() || !model.trim()))))
              }
              onClick={() => void generate()}
            >
              {busy ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <Sparkles size={16} />
              )}{" "}
              {busy
                ? "正在生成预览…"
                : tab === "json"
                  ? "校验并预览"
                  : mode === "ai"
                    ? "调用 API 并预览"
                    : "拆分并预览"}
            </button>
          </div>
        </div>
      ) : (
        <div className="knowledge-preview">
          <div className="knowledge-preview-heading">
            <div>
              <h3>{preview.deck.title}</h3>
              <p>
                {preview.items.length} 个候选知识点 · 已选择 {selected.size} 个
              </p>
            </div>
            <button
              className="secondary"
              disabled={busy}
              onClick={() => {
                if (confirm("返回后会清空当前预览编辑，继续？"))
                  setPreview(null);
              }}
            >
              <ArrowLeft size={14} />
              返回内容
            </button>
          </div>
          <div className="knowledge-preview-grid">
            <div className="knowledge-preview-list">
              <button
                className="text-button"
                onClick={() =>
                  setSelected(
                    selected.size === preview.items.length
                      ? new Set()
                      : new Set(preview.items.map((_, i) => i)),
                  )
                }
                disabled={busy}
              >
                {selected.size === preview.items.length
                  ? "取消全选"
                  : "选择全部"}
              </button>
              {preview.items.map((item, i) => (
                <div className={i === index ? "active" : ""} key={i}>
                  <input
                    type="checkbox"
                    aria-label={`导入 ${item.title}`}
                    checked={selected.has(i)}
                    disabled={busy}
                    onChange={() =>
                      setSelected((s) => {
                        const n = new Set(s);
                        if (n.has(i)) n.delete(i);
                        else n.add(i);
                        return n;
                      })
                    }
                  />
                  <button disabled={busy} onClick={() => setIndex(i)}>
                    <span>{kinds[item.kind]}</span>
                    {item.title}
                  </button>
                </div>
              ))}
            </div>
            {previewCurrent && (
              <div className="knowledge-preview-detail">
                <div className="knowledge-file-bar">
                  <span className="small-tag">
                    {kinds[previewCurrent.kind]}
                  </span>
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() => setEditing(!editing)}
                  >
                    <Pencil size={14} />
                    {editing ? "查看渲染" : "编辑此卡"}
                  </button>
                </div>
                {editing ? (
                  <div className="knowledge-form">
                    <label>
                      预览标题
                      <input
                        maxLength={300}
                        disabled={busy}
                        value={previewCurrent.title}
                        onChange={(e) => editItem({ title: e.target.value })}
                      />
                    </label>
                    <label>
                      预览问题
                      <textarea
                        rows={4}
                        maxLength={100000}
                        disabled={busy}
                        value={previewCurrent.prompt}
                        onChange={(e) => editItem({ prompt: e.target.value })}
                      />
                    </label>
                    <label>
                      预览答案
                      <textarea
                        rows={7}
                        maxLength={100000}
                        disabled={busy}
                        value={previewCurrent.answer}
                        onChange={(e) => editItem({ answer: e.target.value })}
                      />
                    </label>
                  </div>
                ) : (
                  <>
                    <h3>{previewCurrent.title}</h3>
                    <Markdown>{previewCurrent.prompt}</Markdown>
                    <hr />
                    <span className="eyebrow">参考答案</span>
                    <Markdown>{previewCurrent.answer}</Markdown>
                  </>
                )}
              </div>
            )}
          </div>
          <div className="knowledge-actions">
            <button
              className="secondary"
              disabled={busy || !selected.size}
              onClick={() =>
                download(
                  `${preview.deck.title}.json`,
                  JSON.stringify(
                    {
                      ...preview,
                      items: preview.items.filter((_, i) => selected.has(i)),
                    },
                    null,
                    2,
                  ),
                )
              }
            >
              <ArrowDownToLine size={15} />
              导出所选 JSON
            </button>
            <button
              className="primary"
              disabled={busy || !selected.size}
              onClick={() => void importPreview()}
            >
              {busy ? (
                <LoaderCircle size={15} className="spin" />
              ) : (
                <Check size={15} />
              )}
              确认导入 {selected.size} 个知识点
            </button>
          </div>
        </div>
      )}
      {error && (
        <p role="alert" className="knowledge-error">
          {error}
        </p>
      )}
    </Dialog>
  );
}

export default function Knowledge({
  state,
  mutate,
  notify,
  onOpen,
}: Shared & { onOpen: (id: string) => void }) {
  const [deckId, setDeckId] = useState("all"),
    [search, setSearch] = useState(""),
    [filter, setFilter] = useState("all");
  const [modal, setModal] = useState<"deck" | "item" | "import" | null>(null),
    [editingDeck, setEditingDeck] = useState<KnowledgeDeck>();
  const [sample, setSample] = useState<KnowledgeDocument>();
  const decks = Object.values(state.decks || {}),
    items = Object.values(state.knowledge || {});
  const active = items.filter((item) => !item.archived),
    due = active.filter((item) => isDue(state.knowledgeCards[item.id]));
  const filtered = items.filter(
    (item) =>
      (deckId === "all" || item.deckId === deckId) &&
      (filter === "archived" ? item.archived : !item.archived) &&
      (filter !== "due" || isDue(state.knowledgeCards[item.id])) &&
      (filter !== "new" || !state.knowledgeCards[item.id]) &&
      (filter !== "favorites" || state.knowledgeFavorites.includes(item.id)) &&
      `${item.title} ${item.prompt} ${item.tags.join(" ")} ${state.decks[item.deckId]?.title}`
        .toLowerCase()
        .includes(search.trim().toLowerCase()),
  );
  const close = () => {
    setModal(null);
    setEditingDeck(undefined);
    setSample(undefined);
  };
  const exportDeck = (id: string) => {
    const deck = state.decks[id];
    const document: KnowledgeDocument = {
      format: "coderecall.knowledge",
      version: 1,
      deck: { id, title: deck.title, description: deck.description },
      items: items
        .filter((i) => i.deckId === id && !i.archived)
        .map((i) => ({
          id: i.id,
          title: i.title,
          kind: i.kind,
          prompt: i.prompt,
          answer: i.answer,
          tags: i.tags,
          source: i.source,
        })),
    };
    if (!document.items.length) {
      notify("这个知识库还没有可导出的有效知识点");
      return;
    }
    download(`${deck.title}.json`, JSON.stringify(document, null, 2));
  };
  return (
    <div className="knowledge-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            LEARN ANYTHING. REMEMBER WHAT MATTERS.
          </span>
          <h1>你的知识，值得被记住。</h1>
          <p>C++、英语、Blender、UE5… 把笔记变成问题，把回忆变成习惯。</p>
        </div>
        <div className="knowledge-heading-actions">
          <button className="secondary" onClick={() => setModal("import")}>
            <Upload size={16} />
            导入 / 拆分文档
          </button>
          <button className="primary" onClick={() => setModal("deck")}>
            <FolderPlus size={16} />
            新建知识库
          </button>
        </div>
      </div>
      <div className="knowledge-stats">
        <span>
          <Layers size={17} />
          <b>{decks.length}</b> 知识库
        </span>
        <span>
          <BookOpen size={17} />
          <b>{active.length}</b> 知识点
        </span>
        <span>
          <RotateCcw size={17} />
          <b>{due.length}</b> 等待复习
        </span>
        <button
          className="text-button"
          disabled={!due.length}
          onClick={() => due[0] && onOpen(due[0].id)}
        >
          开始到期复习 <ArrowRight size={15} />
        </button>
      </div>
      {!decks.length && (
        <section className="panel knowledge-welcome">
          <span className="tint-icon">
            <BookOpen size={23} />
          </span>
          <h2>从你想掌握的一件事开始</h2>
          <p>
            新建一个知识库，导入已有笔记，或预览一份示例。问答、填空与实践清单都可以复习。
          </p>
          <div className="knowledge-samples">
            {knowledgeSamples.map((s) => (
              <button
                key={s.deck.id}
                onClick={() => {
                  setSample(s);
                  setModal("import");
                }}
              >
                <span>{s.deck.title}</span>
                <small>
                  预览 {s.items.length} 个示例 <ArrowRight size={13} />
                </small>
              </button>
            ))}
          </div>
        </section>
      )}
      {decks.length > 0 && (
        <div className="knowledge-decks">
          <button
            className={`knowledge-deck all ${deckId === "all" ? "selected" : ""}`}
            onClick={() => setDeckId("all")}
          >
            <Layers size={22} />
            <strong>全部知识库</strong>
            <span>{active.length} 个知识点</span>
          </button>
          {decks.map((deck) => {
            const records = active.filter((i) => i.deckId === deck.id),
              learned = records.filter((i) => state.knowledgeCards[i.id]);
            return (
              <section
                className={`knowledge-deck ${deckId === deck.id ? "selected" : ""}`}
                key={deck.id}
              >
                <button
                  className="knowledge-deck-main"
                  onClick={() => setDeckId(deck.id)}
                >
                  <BookOpen size={20} />
                  <strong>{deck.title}</strong>
                  <span>{deck.description || "每次回忆，积累一点理解。"}</span>
                  <small>
                    {learned.length} / {records.length} 已学 ·{" "}
                    {
                      records.filter((i) => isDue(state.knowledgeCards[i.id]))
                        .length
                    }{" "}
                    待复习
                  </small>
                </button>
                <div className="knowledge-deck-tools">
                  <button
                    title={`编辑 ${deck.title}`}
                    onClick={() => {
                      setEditingDeck(deck);
                      setModal("deck");
                    }}
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    title={`导出 ${deck.title}`}
                    onClick={() => exportDeck(deck.id)}
                  >
                    <ArrowDownToLine size={14} />
                  </button>
                </div>
              </section>
            );
          })}
        </div>
      )}
      <section className="panel knowledge-library">
        <div className="knowledge-toolbar">
          <label className="knowledge-search">
            <Search size={16} />
            <input
              id="knowledge-search"
              aria-label="搜索知识点"
              placeholder="搜索标题、内容、标签…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <select
            aria-label="知识点状态"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">全部知识点</option>
            <option value="due">到期复习</option>
            <option value="new">尚未学习</option>
            <option value="favorites">我的收藏</option>
            <option value="archived">已归档</option>
          </select>
          <button
            className="primary"
            disabled={!decks.length}
            onClick={() => setModal("item")}
          >
            <Plus size={15} />
            新建知识点
          </button>
        </div>
        {filtered.map((item) => (
          <div className="knowledge-item-row" key={item.id}>
            <span className={`knowledge-kind ${item.kind}`}>
              {kinds[item.kind]}
            </span>
            <button
              className="knowledge-item-main"
              onClick={() => onOpen(item.id)}
            >
              <strong>{item.title}</strong>
              <span>
                {state.decks[item.deckId]?.title}
                {item.tags.length > 0 && " · " + item.tags.join(" / ")}
              </span>
            </button>
            <span className="knowledge-due">
              {item.archived
                ? "已归档"
                : dueLabel(state.knowledgeCards[item.id])}
            </span>
            <button
              className={`icon-btn ${state.knowledgeFavorites.includes(item.id) ? "is-favorite" : ""}`}
              aria-label={`收藏 ${item.title}`}
              onClick={() =>
                void mutate({
                  type: "knowledge-favorite",
                  itemId: item.id,
                }).catch(() => {})
              }
            >
              <Star
                size={16}
                fill={
                  state.knowledgeFavorites.includes(item.id)
                    ? "currentColor"
                    : "none"
                }
              />
            </button>
            <button
              className="icon-btn"
              aria-label={`打开 ${item.title}`}
              onClick={() => onOpen(item.id)}
            >
              <ArrowRight size={17} />
            </button>
          </div>
        ))}
        {!filtered.length && (
          <div className="empty">
            <BookOpen size={27} />
            <h3>
              {items.length ? "没有找到匹配的知识点" : "下一次回忆，从这里开始"}
            </h3>
            <p>
              {items.length
                ? "调整关键词、知识库或状态筛选。"
                : "创建知识库后，可以手动添加，也可以从笔记文档拆分导入。"}
            </p>
          </div>
        )}
        <div className="panel-bottom">
          <span>Markdown 内容 · 间隔复习 · 本地保存</span>
          <span>{filtered.length} 个知识点</span>
        </div>
      </section>
      {modal === "deck" && (
        <DeckEditor
          state={state}
          mutate={mutate}
          notify={notify}
          deck={editingDeck}
          close={close}
        />
      )}
      {modal === "item" && (
        <ItemEditor
          state={state}
          mutate={mutate}
          notify={notify}
          deckId={deckId === "all" ? undefined : deckId}
          close={close}
        />
      )}
      {modal === "import" && (
        <ImportKnowledge
          state={state}
          mutate={mutate}
          notify={notify}
          sample={sample}
          close={close}
        />
      )}
    </div>
  );
}

export function KnowledgeStudy({
  id,
  state,
  mutate,
  notify,
  onBack,
  onOpen,
}: Shared & { id: string; onBack: () => void; onOpen: (id: string) => void }) {
  const item = state.knowledge[id];
  const [revealed, setRevealed] = useState(false),
    [edit, setEdit] = useState(false),
    [busy, setBusy] = useState(false),
    [rated, setRated] = useState(false);
  const [feedback, setFeedback] = useState<ConfirmedStudy | null>(null),
    [ratingError, setRatingError] = useState("");
  const [note, setNote] = useState(
    () =>
      localStorage.getItem(`coderecall-knowledge-note-${id}`) ??
      state.knowledgeNotes[id] ??
      "",
  );
  const [noteView, setNoteView] = useState(false),
    [noteSaved, setNoteSaved] = useState(
      note === (state.knowledgeNotes[id] || ""),
    );
  const noteRef = useRef(note);
  noteRef.current = note;
  const seconds = useRef(0),
    inFlight = useRef(false),
    pending = useRef<Record<string, unknown> | null>(null);
  useEffect(() => {
    const timer = setInterval(() => {
      if (!document.hidden) seconds.current++;
    }, 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (revealed || edit || !item) return;
    const revealOnSpace = (event: KeyboardEvent) => {
      if (
        event.code !== "Space" ||
        event.repeat ||
        event.defaultPrevented ||
        event.ctrlKey ||
        event.metaKey ||
        event.altKey ||
        event.shiftKey
      )
        return;
      const target = event.target;
      if (
        target instanceof HTMLElement &&
        target.closest(
          'input, textarea, select, button, a, summary, [contenteditable]:not([contenteditable="false"]), [role="textbox"], [role="button"], [role="dialog"]',
        )
      )
        return;
      event.preventDefault();
      setRevealed(true);
    };
    window.addEventListener("keydown", revealOnSpace);
    return () => window.removeEventListener("keydown", revealOnSpace);
  }, [revealed, edit, item]);
  const saveNote = async () => {
    const value = note;
    try {
      await mutate({ type: "knowledge-note", itemId: id, text: value });
      if (localStorage.getItem(`coderecall-knowledge-note-${id}`) === value)
        localStorage.removeItem(`coderecall-knowledge-note-${id}`);
      setNoteSaved(noteRef.current === value);
      notify("学习笔记已保存");
    } catch {
      setNoteSaved(false);
    }
  };
  const rate = async (rating: Rating) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setRatingError("");
    pending.current ??= {
      type: "knowledge-rate",
      itemId: id,
      rating,
      eventId: crypto.randomUUID(),
      day: dayKey(),
      seconds: Math.min(seconds.current, 14400),
    };
    try {
      const next = await mutate(pending.current);
      setFeedback(
        confirmedStudy(
          state,
          next,
          pending.current.rating as Rating,
          dueLabel(next.knowledgeCards[id]),
        ),
      );
      pending.current = null;
      seconds.current = 0;
      setRated(true);
      notify(
        `已记录 · ${dueLabel(next.knowledgeCards[id])}${next.checkins.includes(dayKey()) ? " · 今日已打卡" : ""}`,
      );
    } catch {
      setRatingError("这次反馈还未保存，请点击下方按钮重试。");
      notify("记忆反馈尚未确认，请重试。");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };
  if (!item)
    return (
      <div className="empty">
        <h2>这个知识点不存在</h2>
        <button className="secondary" onClick={onBack}>
          返回知识库
        </button>
      </div>
    );
  const next = Object.values(state.knowledge)
    .filter(
      (i) =>
        i.id !== id &&
        !i.archived &&
        (isDue(state.knowledgeCards[i.id]) || !state.knowledgeCards[i.id]),
    )
    .sort(
      (a, b) =>
        Number(isDue(state.knowledgeCards[b.id])) -
        Number(isDue(state.knowledgeCards[a.id])),
    )[0];
  const prompt = item.prompt.replace(
    /\{\{c[1-9]\d*::([^{}\n]+)\}\}/g,
    (_, value: string) => (revealed ? value : "[ …… ]"),
  );
  return (
    <div className="knowledge-study">
      <div className="knowledge-study-nav">
        <button className="text-button" onClick={onBack}>
          <ArrowLeft size={16} />
          返回知识库
        </button>
        <span>{state.decks[item.deckId]?.title}</span>
        <div>
          <button className="secondary" onClick={() => setEdit(true)}>
            <Pencil size={14} />
            编辑知识点
          </button>
          <button
            className="icon-btn"
            title={item.archived ? "恢复知识点" : "归档知识点"}
            disabled={busy}
            onClick={async () => {
              if (
                !item.archived &&
                !confirm("归档后暂停该知识点的复习，学习记录会保留。继续？")
              )
                return;
              try {
                await mutate({
                  type: "knowledge-archive",
                  itemId: id,
                  archived: !item.archived,
                });
                notify(item.archived ? "知识点已恢复" : "知识点已归档");
              } catch {
                /* mutate reports failure */
              }
            }}
          >
            <Archive size={17} />
          </button>
        </div>
      </div>
      <StudyProgress state={state} />
      <div className="knowledge-study-columns">
        <article className="panel knowledge-recall-card">
          <div className="knowledge-card-meta">
            <span className={`knowledge-kind ${item.kind}`}>
              {kinds[item.kind]}
            </span>
            <span>
              {item.archived
                ? "已归档 · 暂停复习"
                : dueLabel(state.knowledgeCards[id])}
            </span>
          </div>
          <h1>{item.title}</h1>
          <div className="knowledge-tags">
            {item.tags.map((t) => (
              <span key={t}>{t}</span>
            ))}
          </div>
          <div className="knowledge-prompt">
            <Markdown>{prompt}</Markdown>
          </div>
          {!revealed ? (
            <div className="knowledge-reveal">
              <p>
                {item.kind === "procedure"
                  ? "先独立完成操作，再对照验收清单。"
                  : "先尝试回忆，用自己的话说出答案。"}
              </p>
              <button
                className="primary"
                aria-keyshortcuts="Space"
                onClick={() => setRevealed(true)}
              >
                <BookOpen size={16} />
                {item.kind === "procedure" ? "查看验收清单" : "显示答案"}
              </button>
              <small className="study-reveal-hint">
                也可以按 <kbd>Space</kbd> 展开
              </small>
            </div>
          ) : (
            <div className="knowledge-answer study-answer-revealed">
              <span className="eyebrow">
                {item.kind === "procedure" ? "验收清单" : "我的参考答案"}
              </span>
              <Markdown>{item.answer}</Markdown>
              {item.source && (
                <p className="knowledge-source">来源：{item.source}</p>
              )}
              {!item.archived && (
                <div className="knowledge-rate">
                  <p>
                    {rated
                      ? "已记录这次学习。准备好后继续下一个。"
                      : "回忆得怎么样？按真实感受安排下次复习。"}
                  </p>
                  {ratingError && (
                    <p className="knowledge-error" role="alert">
                      {ratingError}
                    </p>
                  )}
                  <div className="study-rating-buttons">
                    {(Object.keys(ratingLabels) as Rating[]).map((r) => (
                      <button
                        className={`rating-button ${r}`}
                        key={r}
                        disabled={busy || rated}
                        onClick={() => void rate(r)}
                      >
                        <RatingSymbol rating={r} />
                        <strong>{ratingLabels[r]}</strong>
                        <small>
                          {r === "again" ? "10 分钟后再学" : "按记忆状态安排"}
                        </small>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {feedback && <StudyFeedback feedback={feedback} />}
              {rated && (
                <div className="knowledge-actions">
                  <button className="secondary" onClick={onBack}>
                    返回知识库
                  </button>
                  {next && (
                    <button className="primary" onClick={() => onOpen(next.id)}>
                      下一个知识点
                      <ArrowRight size={15} />
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </article>
        <aside className="panel knowledge-study-notes">
          <div className="panel-heading">
            <h2>学习笔记</h2>
            <button
              className="text-button"
              onClick={() => setNoteView(!noteView)}
            >
              {noteView ? "继续编辑" : "Markdown 预览"}
            </button>
          </div>
          {noteView ? (
            <Markdown>{note || "记录你的理解、易错点和实践结果。"}</Markdown>
          ) : (
            <textarea
              aria-label="知识点学习笔记"
              maxLength={30000}
              rows={15}
              value={note}
              onChange={(e) => {
                setNote(e.target.value);
                setNoteSaved(false);
                localStorage.setItem(
                  `coderecall-knowledge-note-${id}`,
                  e.target.value,
                );
              }}
              placeholder="支持 Markdown。记录自己的解释、代码片段与实践心得。"
            />
          )}
          <div className="knowledge-note-footer">
            <span>
              {noteSaved ? "已保存到知识库" : "草稿保留在本机，待保存"}
            </span>
            <button
              className="primary"
              disabled={noteSaved}
              onClick={() => void saveNote()}
            >
              保存笔记
            </button>
          </div>
        </aside>
      </div>
      {edit && (
        <ItemEditor
          item={item}
          state={state}
          mutate={mutate}
          notify={notify}
          close={() => setEdit(false)}
        />
      )}
    </div>
  );
}
