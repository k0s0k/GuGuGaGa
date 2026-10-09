import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { LayoutPanelLeft, RotateCcw } from "lucide-react";
import "./panel-layout.css";

type PanelSize = { hidden?: boolean; width?: number; height?: number };
type Layout = Record<string, PanelSize>;
const revealEvent = "gugugaga:reveal-panel";
const bounded = (value: unknown, minimum: number, maximum: number) =>
  typeof value === "number" && Number.isFinite(value)
    ? Math.max(minimum, Math.min(maximum, value))
    : undefined;
function readLayout(key: string): Layout {
  try {
    const data = JSON.parse(localStorage.getItem(key) || "{}");
    if (!data || typeof data !== "object" || Array.isArray(data)) return {};
    return Object.fromEntries(
      Object.entries(data)
        .filter(
          ([name, value]) =>
            /^[a-z-]+$/.test(name) && value && typeof value === "object",
        )
        .map(([name, value]) => {
          const item = value as PanelSize;
          return [
            name,
            {
              hidden: item.hidden === true,
              width: bounded(item.width, 180, 2400),
              height: bounded(item.height, 120, 2000),
            },
          ];
        }),
    );
  } catch {
    return {};
  }
}

/** Explicit navigation may open a hidden target without resetting its size. */
export function revealPanel(pageId: string, panelId: string) {
  const key = `gugugaga-panels-${pageId}`;
  const saved = readLayout(key);
  saved[panelId] = { ...saved[panelId], hidden: false };
  try {
    localStorage.setItem(key, JSON.stringify(saved));
  } catch {
    /* The mounted page can still reveal the panel without browser storage. */
  }
  window.dispatchEvent(
    new CustomEvent(revealEvent, { detail: { pageId, panelId } }),
  );
}

/** Keep panels mounted when hidden so in-progress notes and forms survive. */
export default function PanelLayout({
  id,
  children,
}: {
  id: string;
  children: ReactNode;
}) {
  const key = `gugugaga-panels-${id}`;
  const [layout, setLayout] = useState<Layout>(() => readLayout(key));
  const [panels, setPanels] = useState<{ id: string; label: string }[]>([]);
  const root = useRef<HTMLDivElement>(null);
  const controls = useRef<HTMLDetailsElement>(null);
  const layoutRef = useRef(layout);
  layoutRef.current = layout;
  const apply = () => {
    root.current
      ?.querySelectorAll<HTMLElement>("[data-panel-id]")
      .forEach((node) => {
        const size = layoutRef.current[node.dataset.panelId!] || {};
        node.dataset.panelHidden = String(!!size.hidden);
        node.dataset.panelSized = String(!!size.width);
        node.style.width = size.width ? `${size.width}px` : "";
        node.style.height = size.height ? `${size.height}px` : "";
        node.dataset.panelHeight = String(!!size.height);
      });
  };
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(layout));
    } catch {
      /* Storage may be unavailable in private browser windows. */
    }
    apply();
  }, [key, layout]);
  useEffect(() => {
    const container = root.current;
    if (!container) return;
    const discover = () => {
      const next = Array.from(
        container.querySelectorAll<HTMLElement>("[data-panel-id]"),
      ).map((node) => ({
        id: node.dataset.panelId!,
        label: node.dataset.panelLabel || node.dataset.panelId!,
      }));
      setPanels((previous) =>
        JSON.stringify(previous) === JSON.stringify(next) ? previous : next,
      );
      apply();
    };
    discover();
    const observer = new MutationObserver(discover);
    observer.observe(container, { childList: true, subtree: true });
    const rememberSize = () => {
      const next = { ...layoutRef.current };
      let changed = false;
      container
        .querySelectorAll<HTMLElement>("[data-panel-id]")
        .forEach((node) => {
          const current = next[node.dataset.panelId!] || {};
          if (current.hidden) return;
          const width = bounded(parseFloat(node.style.width), 180, 2400);
          const height = bounded(parseFloat(node.style.height), 120, 2000);
          if (width !== current.width || height !== current.height) {
            next[node.dataset.panelId!] = { ...current, width, height };
            changed = true;
          }
        });
      if (changed) setLayout(next);
    };
    window.addEventListener("pointerup", rememberSize);
    window.addEventListener("pointercancel", rememberSize);
    const reveal = (event: Event) => {
      const detail = (event as CustomEvent<{ pageId: string; panelId: string }>)
        .detail;
      if (detail?.pageId !== id || typeof detail.panelId !== "string") return;
      setLayout((previous) => ({
        ...previous,
        [detail.panelId]: { ...previous[detail.panelId], hidden: false },
      }));
    };
    window.addEventListener(revealEvent, reveal);
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && controls.current?.open) {
        controls.current.open = false;
        controls.current.querySelector("summary")?.focus();
      }
    };
    window.addEventListener("keydown", escape);
    return () => {
      observer.disconnect();
      window.removeEventListener("pointerup", rememberSize);
      window.removeEventListener("pointercancel", rememberSize);
      window.removeEventListener(revealEvent, reveal);
      window.removeEventListener("keydown", escape);
    };
  }, []);
  const update = (id: string, value: PanelSize) =>
    setLayout((old) => ({ ...old, [id]: { ...old[id], ...value } }));
  const commitSize = (
    id: string,
    dimension: "width" | "height",
    input: HTMLInputElement,
  ) => {
    const value = bounded(
      input.valueAsNumber,
      dimension === "width" ? 180 : 120,
      dimension === "width" ? 2400 : 2000,
    );
    input.value = value === undefined ? "" : String(value);
    update(id, { [dimension]: value });
  };
  return (
    <div className="customizable-page">
      <div className="panel-layout-toolbar">
        <details className="panel-layout-controls" ref={controls}>
          <summary>
            <LayoutPanelLeft size={16} />
            面板布局
          </summary>
          <div className="panel-layout-menu">
            <strong>显示与大小</strong>
            <p>拖动面板右下角调整大小，或填写尺寸。留空恢复自动大小。</p>
            {panels.map((panel) => (
              <div className="panel-layout-option" key={panel.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={!layout[panel.id]?.hidden}
                    onChange={(event) =>
                      update(panel.id, { hidden: !event.target.checked })
                    }
                  />
                  {panel.label}
                </label>
                <label>
                  宽
                  <input
                    type="number"
                    min={180}
                    max={2400}
                    step={20}
                    placeholder="自动"
                    aria-label={`${panel.label}宽度`}
                    key={`width-${layout[panel.id]?.width}`}
                    defaultValue={layout[panel.id]?.width || ""}
                    onBlur={(event) =>
                      commitSize(panel.id, "width", event.currentTarget)
                    }
                    onKeyDown={(event) => {
                      if (event.key === "Enter") event.currentTarget.blur();
                    }}
                  />
                  <small>px</small>
                </label>
                <label>
                  高
                  <input
                    type="number"
                    min={120}
                    max={2000}
                    step={20}
                    placeholder="自动"
                    aria-label={`${panel.label}高度`}
                    key={`height-${layout[panel.id]?.height}`}
                    defaultValue={layout[panel.id]?.height || ""}
                    onBlur={(event) =>
                      commitSize(panel.id, "height", event.currentTarget)
                    }
                    onKeyDown={(event) => {
                      if (event.key === "Enter") event.currentTarget.blur();
                    }}
                  />
                  <small>px</small>
                </label>
              </div>
            ))}
            <button className="secondary small" onClick={() => setLayout({})}>
              <RotateCcw size={14} />
              恢复本页布局
            </button>
          </div>
        </details>
        {panels.some((panel) => layout[panel.id]?.hidden) && (
          <span className="panel-hidden-notice">
            已隐藏部分面板，可在“面板布局”中恢复
          </span>
        )}
      </div>
      <div className="panel-layout-content" ref={root}>
        {children}
      </div>
    </div>
  );
}

export function SidebarResize({
  width,
  onChange,
}: {
  width: number;
  onChange: (width: number) => void;
}) {
  const drag = useRef<{ x: number; width: number; pointerId: number } | null>(
    null,
  );
  return (
    <div
      className="sidebar-resize"
      role="separator"
      aria-label="调整侧栏宽度"
      title="拖动调整侧栏宽度，双击恢复"
      onDoubleClick={() => onChange(226)}
      aria-orientation="vertical"
      aria-valuenow={width}
      aria-valuemin={180}
      aria-valuemax={340}
      tabIndex={0}
      onPointerDown={(event) => {
        if (event.button !== 0 || drag.current) return;
        event.preventDefault();
        drag.current = { x: event.clientX, width, pointerId: event.pointerId };
        event.currentTarget.setPointerCapture(event.pointerId);
      }}
      onPointerMove={(event) => {
        if (drag.current?.pointerId === event.pointerId)
          onChange(
            Math.round(
              Math.max(
                180,
                Math.min(
                  340,
                  drag.current.width + event.clientX - drag.current.x,
                ),
              ),
            ),
          );
      }}
      onPointerUp={(event) => {
        if (drag.current?.pointerId !== event.pointerId) return;
        drag.current = null;
        if (event.currentTarget.hasPointerCapture(event.pointerId))
          event.currentTarget.releasePointerCapture(event.pointerId);
      }}
      onPointerCancel={(event) => {
        if (drag.current?.pointerId === event.pointerId) drag.current = null;
      }}
      onLostPointerCapture={() => {
        drag.current = null;
      }}
      onKeyDown={(event) => {
        if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
          event.preventDefault();
          onChange(
            event.key === "Home"
              ? 180
              : event.key === "End"
                ? 340
                : Math.max(
                    180,
                    Math.min(
                      340,
                      width + (event.key === "ArrowRight" ? 10 : -10),
                    ),
                  ),
          );
        }
      }}
    />
  );
}
