import { useEffect, useId, useRef, useState } from "react";
import { CalendarCheck, Check, LoaderCircle } from "lucide-react";
import type { AppState } from "./types";
import { dayKey } from "./utils";

interface CheckInButtonProps {
  state: AppState;
  mutate: (payload: unknown) => Promise<AppState>;
  notify: (message: string) => void;
  onSuccess?: (next: AppState) => void;
}

export default function CheckInButton({
  state,
  mutate,
  notify,
  onSuccess,
}: CheckInButtonProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);
  const mounted = useRef(true);
  const errorId = useId();
  const today = dayKey();
  const signed = state.checkins.includes(today);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const checkIn = async () => {
    if (inFlight.current || signed) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      const next = await mutate({ type: "checkin" });
      // The saved response confirms the action; clicking alone never counts.
      // Either date can be valid if midnight passes while the request is in flight.
      if (!next.checkins.includes(today) && !next.checkins.includes(dayKey()))
        throw new Error("签到尚未确认，请重试。");
      notify("签到成功，今天也留下了坚持的足迹。");
      if (mounted.current) onSuccess?.(next);
    } catch (reason) {
      const message =
        reason instanceof Error ? reason.message : "签到失败，请重试。";
      if (mounted.current) setError(message);
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  };

  return (
    <div className="checkin-control">
      <button
        type="button"
        className={`primary full checkin-button ${signed ? "is-checked" : ""}`}
        disabled={signed || busy}
        aria-busy={busy}
        aria-describedby={error ? errorId : undefined}
        onClick={() => void checkIn()}
      >
        {busy ? (
          <LoaderCircle size={18} className="spin" aria-hidden="true" />
        ) : signed ? (
          <Check size={18} aria-hidden="true" />
        ) : (
          <CalendarCheck size={18} aria-hidden="true" />
        )}
        {busy ? "签到中…" : signed ? "今日已签到" : "签到"}
      </button>
      {error && (
        <p id={errorId} className="knowledge-error checkin-error" role="alert">
          {error} 可以再次点击签到。
        </p>
      )}
    </div>
  );
}
