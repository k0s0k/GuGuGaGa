import { useEffect, useState } from "react";
import type { AppState } from "./types";

export default function WorkspaceNameSettings({
  workspaceName,
  mutate,
  notify,
}: {
  workspaceName?: string;
  mutate: (payload: unknown) => Promise<AppState>;
  notify: (message: string) => void;
}) {
  const saved = workspaceName || "我的工作空间";
  const [draft, setDraft] = useState(saved);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    setDraft(saved);
  }, [saved]);
  const trimmed = draft.trim();
  const length = Array.from(trimmed).length;
  const invalid = /[\p{Cc}\p{Cs}\u2028\u2029]/u.test(draft)
    ? "名称不能包含换行或控制字符"
    : length < 1 || length > 40
      ? "请输入 1–40 个字符"
      : "";
  const dirty = trimmed !== saved;
  const save = async () => {
    if (saving || invalid || !dirty) return;
    setSaving(true);
    setError("");
    try {
      await mutate({ type: "settings", settings: { workspaceName: trimmed } });
      setDraft(trimmed);
      notify("工作空间名称已保存");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <form
      className="workspace-name-settings"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <label htmlFor="workspace-name">工作空间名称</label>
      <div className="workspace-name-controls">
        <input
          id="workspace-name"
          value={draft}
          disabled={saving}
          autoComplete="off"
          aria-describedby="workspace-name-hint"
          aria-invalid={!!invalid}
          onChange={(event) => {
            setDraft(event.target.value);
            setError("");
          }}
        />
        <button
          className="primary"
          type="submit"
          disabled={saving || !dirty || !!invalid}
        >
          {saving ? "正在保存名称…" : "保存名称"}
        </button>
        {dirty && (
          <button
            className="text-button"
            type="button"
            disabled={saving}
            onClick={() => {
              setDraft(saved);
              setError("");
            }}
          >
            撤销名称修改
          </button>
        )}
      </div>
      <p
        id="workspace-name-hint"
        className={invalid ? "profile-error" : "muted"}
      >
        {invalid || "显示在侧栏和顶部导航，最多 40 个字符。"}
      </p>
      {error && (
        <p className="profile-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
