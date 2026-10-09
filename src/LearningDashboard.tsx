import { useState } from "react";
import type { CSSProperties } from "react";
import {
  ArrowRight,
  BookOpen,
  Check,
  ChevronDown,
  Flame,
  Play,
  RotateCcw,
  Settings2,
  Sparkles,
  Target,
} from "lucide-react";
import type { AppState, Problem, View } from "./types";
import { dailyPlan, dateShift, dayKey, isDue, streak } from "./utils";
import CheckInButton from "./CheckInButton";
import JourneyIcon from "./JourneyIcon";
import "./learning-dashboard.css";
import "./journey-icons.css";

export default function LearningDashboard({
  problems,
  state,
  onOpen,
  navigate,
  mutate,
  notify,
}: {
  problems: Problem[];
  state: AppState;
  onOpen: (id: number) => void;
  navigate: (view: View) => void;
  mutate: (payload: unknown) => Promise<AppState>;
  notify: (message: string) => void;
}) {
  const [tab, setTab] = useState("全部任务");
  const [expanded, setExpanded] = useState(false);
  const now = new Date();
  const today = dayKey(now);
  const done = new Set(
    state.events
      .filter((event) => event.day === today)
      .map((event) => event.problemId),
  ).size;
  const plan = dailyPlan(problems, state);
  const due = plan.filter((problem) => isDue(state.cards[problem.id]));
  const filtered = plan.filter(
    (problem) =>
      tab === "全部任务" ||
      (tab === "待复习" ? !!state.cards[problem.id] : !state.cards[problem.id]),
  );
  const visible = expanded ? filtered : filtered.slice(0, 6);
  const goal = state.settings.dailyGoal;
  const achieved = done >= goal;
  const progress = Math.min(100, (done / goal) * 100);
  const learned = problems.filter((problem) => state.cards[problem.id]).length;
  const weekStart = dateShift(now, -((now.getDay() + 6) % 7));
  const nextWeek = dayKey(dateShift(weekStart, 7));
  const weekCount = state.checkins.filter(
    (day) => day >= dayKey(weekStart) && day < nextWeek,
  ).length;
  const start = () => (plan[0] ? onOpen(plan[0].id) : navigate("knowledge"));

  return (
    <div className="learning-dashboard">
      <div className="learning-heading">
        <div>
          <div className="learning-date">
            {now.getMonth() + 1} 月 {now.getDate()} 日 ·{" "}
            {now.toLocaleDateString("zh-CN", { weekday: "long" })}
          </div>
          <h1>
            {achieved ? "今天的努力，闪闪发光。" : "今天，也进步一点点。"}
          </h1>
          <p>和咕嘎一起，把每一次回忆变成更牢的记忆。</p>
        </div>
        <button className="primary start-button" onClick={start}>
          <Play size={18} fill="currentColor" />
          {plan.length ? "开始今日学习" : "添加新的知识"}
        </button>
      </div>

      <div className="learning-layout">
        <section
          className="learning-journey today-panel"
          data-panel-id="journey"
          data-panel-label="学习旅程"
          aria-labelledby="journey-title"
        >
          <div className="journey-banner">
            <div className="journey-banner-icon">
              <JourneyIcon kind="banner" />
            </div>
            <div>
              <span>每日旅程</span>
              <h2 id="journey-title">先巩固，再向前</h2>
              <p>
                {plan.length
                  ? `今天还有 ${plan.length} 项等你探索`
                  : "按自己的节奏，让知识慢慢生根"}
              </p>
            </div>
            <button
              aria-label="调整学习计划"
              title="调整学习计划"
              onClick={() => navigate("settings")}
            >
              <Settings2 size={22} />
            </button>
          </div>
          <div className="journey-filters" aria-label="学习任务分类">
            {["全部任务", "新知", "待复习"].map((label) => (
              <button
                key={label}
                aria-pressed={tab === label}
                className={tab === label ? "selected" : ""}
                onClick={() => {
                  setTab(label);
                  setExpanded(false);
                }}
              >
                {label}
                {label === "待复习" && <span>{due.length}</span>}
              </button>
            ))}
          </div>
          {done > 0 && (
            <div className="journey-completed">
              <Check size={17} strokeWidth={3} />
              <span>
                今天已完成 <strong>{done}</strong> 项。每一步都值得肯定！
              </span>
            </div>
          )}
          <div className="journey-steps">
            {visible.map((problem, index) => {
              const reviewing = !!state.cards[problem.id];
              const first = index === 0;
              return (
                <button
                  key={problem.id}
                  className={`problem-row journey-step ${first ? "current" : ""} ${reviewing ? "is-review" : ""}`}
                  style={
                    {
                      "--step-shift": `${[0, 28, 48, 28][index % 4]}px`,
                    } as CSSProperties
                  }
                  onClick={() => onOpen(problem.id)}
                  aria-label={`${first ? "开始" : "学习"} ${problem.title}`}
                >
                  <span className="step-route">
                    <span className="step-orbit">
                      <JourneyIcon
                        kind={
                          reviewing
                            ? "review"
                            : problem.knowledgeId
                              ? "knowledge"
                              : "code"
                        }
                        current={first}
                      />
                    </span>
                  </span>
                  <span className="step-content">
                    <span className="step-kicker">
                      {first ? "从这里继续" : `第 ${index + 1} 站`}
                      <span
                        className={`step-kind ${reviewing ? "review" : ""}`}
                      >
                        {reviewing ? "巩固记忆" : "探索新知"}
                      </span>
                    </span>
                    <strong>{problem.title}</strong>
                    <span className="step-description">
                      {problem.category}
                      {!problem.knowledgeId && (
                        <span className="problem-id"> · #{problem.id}</span>
                      )}
                    </span>
                  </span>
                  <ArrowRight className="step-arrow" size={19} />
                </button>
              );
            })}
            {!visible.length && (
              <div className="journey-empty">
                <span className="journey-empty-icon">
                  <JourneyIcon kind={done ? "complete" : "empty"} />
                </span>
                <h3>
                  {plan.length
                    ? "这个分类暂时没有任务"
                    : done
                      ? "这一段旅程完成啦！"
                      : "从一张知识卡开始"}
                </h3>
                <p>
                  {plan.length
                    ? "切换分类，找到下一次进步的机会。"
                    : done
                      ? "休息一下，或去发现新的知识。"
                      : "导入你的笔记，开启属于自己的学习旅程。"}
                </p>
                <button
                  className="secondary"
                  onClick={() =>
                    plan.length ? setTab("全部任务") : navigate("knowledge")
                  }
                >
                  {plan.length ? "查看全部任务" : "探索我的知识库"}
                  <ArrowRight size={16} />
                </button>
              </div>
            )}
          </div>
          {filtered.length > 6 && (
            <button
              className="journey-expand"
              onClick={() => setExpanded(!expanded)}
              aria-expanded={expanded}
            >
              {expanded ? "收起任务" : `查看剩余 ${filtered.length - 6} 项`}
              <ChevronDown
                size={16}
                style={{ transform: expanded ? "rotate(180deg)" : undefined }}
              />
            </button>
          )}
          <div className="journey-finish">
            <span />
            <JourneyIcon kind="finish" />
            <span />
            <p>小步前进，日有所获</p>
          </div>
        </section>

        <aside className="learning-side">
          <section
            className={`quest-card ${achieved ? "is-complete" : ""}`}
            data-panel-id="goal"
            data-panel-label="每日目标"
            aria-labelledby="daily-quest-title"
          >
            <div className="quest-title">
              <h2 id="daily-quest-title">每日小目标</h2>
              <Target size={23} />
            </div>
            <div className="coach-scene" aria-hidden="true">
              <span className="coach-spark spark-one">✦</span>
              <img src="/gugugaga-icon.png" alt="" />
              <span className="coach-spark spark-two">✧</span>
              <span className="coach-bubble">
                {achieved ? "好耶，目标达成！" : "咕嘎陪你一起！"}
              </span>
            </div>
            <div className="quest-count">
              <strong>
                {done}
                <small> / {goal} 项</small>
              </strong>
              <span>{achieved ? "学习目标已达成" : "今日学习"}</span>
            </div>
            <div
              className="quest-meter"
              role="progressbar"
              aria-label="每日目标进度"
              aria-valuemin={0}
              aria-valuemax={goal}
              aria-valuenow={Math.min(done, goal)}
              aria-valuetext={`已完成 ${done} 项，目标 ${goal} 项`}
            >
              <span style={{ width: `${progress}%` }} />
            </div>
            <p>
              {achieved
                ? "把这一份坚持，带到明天。"
                : `再完成 ${Math.max(0, goal - done)} 项，达成今日学习目标。`}
            </p>
            <CheckInButton state={state} mutate={mutate} notify={notify} />
          </section>

          <section
            className="streak-card"
            aria-labelledby="streak-title"
            data-panel-id="streak"
            data-panel-label="连续打卡"
          >
            <div className="streak-summary">
              <div className="streak-flame">
                <Flame size={31} fill="currentColor" />
              </div>
              <div>
                <h2 id="streak-title">
                  {streak(state)} <span>天连续打卡</span>
                </h2>
                <p>本周已点亮 {weekCount} 天</p>
              </div>
            </div>
            <div className="learning-week">
              {Array.from({ length: 7 }, (_, index) => {
                const day = dayKey(dateShift(weekStart, index));
                const active = state.checkins.includes(day);
                return (
                  <button
                    key={day}
                    className={`${active ? "checked" : ""} ${day === today ? "is-today" : ""}`}
                    aria-label={`${day}${active ? " 已打卡" : " 未打卡"}，查看日历`}
                    onClick={() => navigate("calendar")}
                  >
                    <small>
                      {["一", "二", "三", "四", "五", "六", "日"][index]}
                    </small>
                    <span>
                      {active ? (
                        <Check size={15} strokeWidth={3} />
                      ) : day === today ? (
                        <span className="week-today-dot" />
                      ) : (
                        "·"
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
            <button
              className="streak-calendar"
              onClick={() => navigate("calendar")}
            >
              查看学习日历
              <ArrowRight size={15} />
            </button>
          </section>

          <section
            className="explore-card"
            data-panel-id="explore"
            data-panel-label="探索知识库"
          >
            <span className="explore-icon">
              <BookOpen size={27} />
            </span>
            <h2>让好奇心，带个路</h2>
            <p>
              代码、语言、创作……
              <br />
              把你的热爱装进知识库。
            </p>
            <button
              className="secondary full"
              onClick={() => navigate("knowledge")}
            >
              管理知识库
              <ArrowRight size={17} />
            </button>
          </section>
        </aside>
      </div>
      <div
        className="learning-summary"
        data-panel-id="summary"
        data-panel-label="学习概览"
      >
        <div>
          <span className="summary-symbol blue">
            <BookOpen size={21} />
          </span>
          <strong>
            {learned}
            <small>已学习的知识</small>
          </strong>
        </div>
        <button onClick={() => navigate("review")}>
          <span className="summary-symbol violet">
            <RotateCcw size={21} />
          </span>
          <strong>
            {due.length}
            <small>等待与你重逢</small>
          </strong>
          <ArrowRight size={16} />
        </button>
        <button
          onClick={() =>
            navigate(state.settings.includeHot100 ? "path" : "knowledge")
          }
        >
          <span className="summary-symbol amber">
            <Sparkles size={21} />
          </span>
          <strong>
            继续探索
            <small>
              {state.settings.includeHot100
                ? "沿着知识路线前进"
                : "发现你的下一项技能"}
            </small>
          </strong>
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
