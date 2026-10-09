import { useEffect, useRef, useState } from "react";
import { ImagePlus, LoaderCircle, UserRound } from "lucide-react";
import type { AppState } from "./types";
import WorkspaceNameSettings from "./WorkspaceNameSettings";

const MAX_UPLOAD = 5 * 1024 * 1024;

export function Avatar({
  source,
  className = "",
}: {
  source?: string;
  className?: string;
}) {
  return (
    <span className={`avatar ${className}`}>
      {source ? (
        <img src={source} alt="用户头像" />
      ) : (
        <UserRound size={19} aria-hidden="true" />
      )}
    </span>
  );
}

async function prepareAvatar(file: File): Promise<string> {
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type))
    throw new Error("请选择 PNG、JPEG 或 WebP 图片");
  if (file.size > MAX_UPLOAD) throw new Error("头像图片不能超过 5 MB");
  if (!file.size) throw new Error("这张图片是空文件，请重新选择");
  const url = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = url;
    try {
      await image.decode();
    } catch {
      throw new Error("无法读取这张图片，请重新选择有效的图片文件");
    }
    if (!image.naturalWidth || !image.naturalHeight)
      throw new Error("无法读取图片尺寸，请重新选择");
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 256;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("当前环境无法处理图片，请重新打开应用后重试");
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = "high";
    const side = Math.min(image.naturalWidth, image.naturalHeight);
    context.drawImage(
      image,
      (image.naturalWidth - side) / 2,
      (image.naturalHeight - side) / 2,
      side,
      side,
      0,
      0,
      256,
      256,
    );
    const result = canvas.toDataURL("image/png");
    if (
      !result.startsWith("data:image/png;base64,") ||
      (result.length - result.indexOf(",") - 1) * 0.75 > 256 * 1024
    )
      throw new Error("图片压缩失败，请选择一张更小的图片");
    return result;
  } finally {
    URL.revokeObjectURL(url);
  }
}

export default function AvatarSettings({
  avatar,
  workspaceName,
  mutate,
  notify,
}: {
  avatar?: string;
  workspaceName?: string;
  mutate: (payload: unknown) => Promise<AppState>;
  notify: (message: string) => void;
}) {
  const saved = avatar || "";
  const [draft, setDraft] = useState(saved);
  const [reading, setReading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  useEffect(() => {
    setDraft(saved);
  }, [saved]);
  const busy = reading || saving;
  const dirty = draft !== saved;
  const choose = async (file?: File) => {
    if (!file) return;
    setReading(true);
    setError("");
    try {
      const next = await prepareAvatar(file);
      if (active.current) setDraft(next);
    } catch (reason) {
      if (active.current) setError((reason as Error).message);
    } finally {
      if (active.current) setReading(false);
      if (input.current) input.current.value = "";
    }
  };
  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await mutate({ type: "settings", settings: { avatar: draft } });
      notify(draft ? "头像已保存" : "已恢复默认头像");
    } catch (reason) {
      if (active.current) setError((reason as Error).message);
    } finally {
      if (active.current) setSaving(false);
    }
  };
  return (
    <section
      className="panel settings-panel avatar-settings"
      data-panel-id="profile"
      data-panel-label="个人资料"
      aria-labelledby="profile-heading"
    >
      <h2 id="profile-heading" tabIndex={-1}>
        <UserRound size={18} />
        个人资料
      </h2>
      <WorkspaceNameSettings
        workspaceName={workspaceName}
        mutate={mutate}
        notify={notify}
      />
      <h3 className="profile-avatar-heading">个人头像</h3>
      <div className="avatar-settings-content">
        <Avatar source={draft} className="avatar-settings-preview" />
        <div className="avatar-settings-options">
          <strong>让工作空间更像你</strong>
          <p>支持 PNG、JPEG、WebP，最大 5 MB。自动居中裁剪，随学习备份保存。</p>
          <div className="button-group">
            <button
              className="secondary"
              disabled={busy}
              onClick={() => input.current?.click()}
            >
              {reading ? (
                <LoaderCircle size={15} className="spin" />
              ) : (
                <ImagePlus size={15} />
              )}
              {reading ? "正在处理…" : "上传头像"}
            </button>
            <button
              className="secondary"
              disabled={busy || !draft}
              onClick={() => {
                setDraft("");
                setError("");
              }}
            >
              移除头像
            </button>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              aria-label="上传用户头像"
              hidden
              ref={input}
              disabled={busy}
              onChange={(event) => void choose(event.target.files?.[0])}
            />
          </div>
          {dirty && (
            <div className="button-group avatar-save-actions">
              <button
                className="primary"
                disabled={busy}
                onClick={() => void save()}
              >
                {saving ? "正在保存…" : "保存头像"}
              </button>
              <button
                className="text-button"
                disabled={busy}
                onClick={() => {
                  setDraft(saved);
                  setError("");
                }}
              >
                撤销修改
              </button>
              <span className="muted">预览中，尚未保存</span>
            </div>
          )}
          {error && (
            <p className="avatar-error" role="alert">
              {error}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
