import { useEffect, useId, useRef, useState } from "react";
import {
  ArrowRight,
  CalendarCheck,
  LoaderCircle,
  Sparkles,
} from "lucide-react";
import type { AppState, StoneWalletState } from "./types";
import { dateShift, dayKey } from "./utils";
import StoneIcon from "./StoneIcon";
import "./stone-wallet.css";

export function stoneWallet(state: AppState): StoneWalletState {
  return (
    state.stones ?? {
      balance: 0,
      totalEarned: 0,
      totalSpent: 0,
      rules: {
        learn: 10,
        review: 5,
        checkin: 2,
        makeup: 20,
        makeupWindowDays: 30,
      },
      startedOn: dayKey(),
      makeups: [],
    }
  );
}

export function stoneGain(before: AppState, after: AppState) {
  if (!before.stones || !after.stones) return undefined;
  return Math.max(0, after.stones.totalEarned - before.stones.totalEarned);
}

export function StoneBalance({
  state,
  onClick,
}: {
  state: AppState;
  onClick: () => void;
}) {
  const { balance } = stoneWallet(state);
  return (
    <button
      className="stone-balance"
      data-stone-wallet
      aria-label={`小石头余额 ${balance}，查看收藏`}
      title={`可用 ${balance.toLocaleString()} 颗小石头 · 查看收藏`}
      onClick={onClick}
    >
      <StoneIcon size={24} />
      <strong>
        {balance >= 100000
          ? `${(balance / 10000).toFixed(1)}万`
          : balance.toLocaleString()}
      </strong>
    </button>
  );
}

export function StoneCollection({
  state,
  compact = false,
  onCalendar,
}: {
  state: AppState;
  compact?: boolean;
  onCalendar?: () => void;
}) {
  const wallet = stoneWallet(state);
  const titleId = useId();
  const count = Math.min(18, Math.ceil(wallet.totalEarned / 10));
  return (
    <section
      className={`stone-collection ${compact ? "is-compact" : ""}`}
      data-panel-id="stones"
      data-panel-label="小石头收藏"
      aria-labelledby={titleId}
    >
      <div className="stone-collection-heading">
        <div>
          <span className="stone-eyebrow">PIECE BY PIECE</span>
          <h2 id={titleId}>我的小石头收藏</h2>
        </div>
        <Sparkles size={21} aria-hidden="true" />
      </div>
      <div className="stone-collection-body">
        <div className="stone-shelf" aria-hidden="true">
          <span className="stone-shelf-spark">✦</span>
          {Array.from({ length: Math.max(1, count) }, (_, index) => (
            <span
              key={index}
              className={`collected-stone ${count ? "" : "is-empty"}`}
              style={{
                left: `${5 + (index % 6) * 13}%`,
                bottom: `${14 + Math.floor(index / 6) * 21}px`,
                transform: `rotate(${[-14, 10, -6, 18, -20, 4][index % 6]}deg)`,
                zIndex: 20 - index,
              }}
            >
              <StoneIcon size={index % 3 === 0 ? 43 : 35} />
            </span>
          ))}
          <span className="stone-shelf-line" />
        </div>
        <div className="stone-stats">
          <div className="stone-available">
            <span>可用小石头</span>
            <strong data-testid="stone-balance">
              {wallet.balance.toLocaleString()}
              <small>颗</small>
            </strong>
          </div>
          <div className="stone-lifetime">
            <span>
              累计收集{" "}
              <b data-testid="stone-total">
                {wallet.totalEarned.toLocaleString()}
              </b>
            </span>
            <span>
              补签已用{" "}
              <b data-testid="stone-spent">
                {wallet.totalSpent.toLocaleString()}
              </b>
            </span>
          </div>
        </div>
      </div>
      <p className="stone-collection-caption">
        {wallet.totalEarned
          ? "一颗颗收藏，一点点记住。"
          : "从今天的学习，收集第一颗小石头。"}
      </p>
      <div className="stone-rules" aria-label="小石头奖励规则">
        <span>
          新学 <b>+{wallet.rules.learn}</b>
        </span>
        <span>
          复习 <b>+{wallet.rules.review}</b>
        </span>
        <span>
          签到 <b>+{wallet.rules.checkin}</b>
        </span>
      </div>
      <p className="stone-rule-note">
        同一知识点每天收集一次。补签消耗 {wallet.rules.makeup}{" "}
        颗，累计收集一直保留。
      </p>
      {onCalendar ? (
        <button className="stone-calendar-link" onClick={onCalendar}>
          去日历补签 <ArrowRight size={15} />
        </button>
      ) : (
        <p className="stone-rule-note">
          可补签最近 {wallet.rules.makeupWindowDays}{" "}
          天内、开始使用以来的漏签日期。点击日历中的日期即可补签。
        </p>
      )}
    </section>
  );
}

export function MakeupCheckin({
  state,
  day,
  mutate,
  notify,
}: {
  state: AppState;
  day: string;
  mutate: (payload: unknown) => Promise<AppState>;
  notify: (message: string) => void;
}) {
  const wallet = stoneWallet(state);
  const today = dayKey();
  const earliest = [
    wallet.startedOn,
    dayKey(dateShift(new Date(), -wallet.rules.makeupWindowDays)),
  ]
    .sort()
    .at(-1)!;
  const madeUp = wallet.makeups.find((entry) => entry.day === day);
  const checked = state.checkins.includes(day);
  const eligible = day < today && day >= earliest && !checked;
  const affordable = wallet.balance >= wallet.rules.makeup;
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const inFlight = useRef(false);
  const mounted = useRef(true);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    const element = dialog.current;
    if (open && element && !element.open) element.showModal();
    return () => {
      if (element?.open) element.close();
    };
  }, [open]);

  const confirm = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      const next = await mutate({ type: "checkin-makeup", day });
      if (!next.checkins.includes(day))
        throw new Error("补签尚未确认，请重试。");
      const spent = stoneWallet(next).totalSpent - wallet.totalSpent;
      notify(
        spent > 0
          ? `${day} 补签成功，消耗 ${spent} 颗小石头。`
          : `${day} 已有签到记录。`,
      );
      if (mounted.current) setOpen(false);
    } catch (reason) {
      if (mounted.current)
        setError(
          reason instanceof Error ? reason.message : "补签失败，请重试。",
        );
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  };

  return (
    <div className="makeup-control">
      {madeUp ? (
        <p className="makeup-record">
          <StoneIcon size={19} />
          已补签 · 消耗 {madeUp.cost} 颗小石头
        </p>
      ) : eligible ? (
        <>
          <button
            className="secondary full makeup-button"
            disabled={!affordable}
            onClick={() => {
              setError("");
              setOpen(true);
            }}
          >
            <StoneIcon size={21} />
            补签 · {wallet.rules.makeup} 小石头
          </button>
          <p>
            {affordable
              ? "让漏掉的一天，重新亮起来。"
              : `还差 ${wallet.rules.makeup - wallet.balance} 颗小石头，完成学习即可收集。`}
          </p>
        </>
      ) : (
        !checked && (
          <p>
            {day === today
              ? "点击上方「签到」，点亮今天。"
              : day > today
                ? "这一天还没到，先收集今天的进步吧。"
                : `可补签 ${earliest} 起的漏签日期。`}
          </p>
        )
      )}
      {open && (
        <dialog
          ref={dialog}
          className="makeup-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={descriptionId}
          onCancel={(event) => {
            event.preventDefault();
            if (!inFlight.current) setOpen(false);
          }}
        >
          <div className="makeup-dialog-art" aria-hidden="true">
            <StoneIcon size={64} />
            <CalendarCheck size={28} />
          </div>
          <h2 id={titleId}>用小石头补签</h2>
          <p id={descriptionId}>
            为 <strong>{day}</strong> 点亮一次签到。
            <br />
            累计收集的小石头会继续保留。
          </p>
          <dl className="makeup-cost">
            <div>
              <dt>本次消耗</dt>
              <dd>
                <StoneIcon />
                {wallet.rules.makeup} 颗
              </dd>
            </div>
            <div>
              <dt>补签后可用</dt>
              <dd>
                {Math.max(
                  0,
                  wallet.balance - wallet.rules.makeup,
                ).toLocaleString()}{" "}
                颗
              </dd>
            </div>
          </dl>
          {error && (
            <p className="knowledge-error" role="alert">
              {error}
            </p>
          )}
          <div className="makeup-dialog-actions">
            <button
              className="secondary"
              disabled={busy}
              onClick={() => setOpen(false)}
            >
              取消
            </button>
            <button
              className="primary"
              disabled={busy}
              aria-busy={busy}
              onClick={() => void confirm()}
            >
              {busy && (
                <LoaderCircle size={16} className="spin" aria-hidden="true" />
              )}
              {busy ? "补签中…" : "确认补签"}
            </button>
          </div>
        </dialog>
      )}
    </div>
  );
}
