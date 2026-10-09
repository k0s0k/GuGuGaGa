import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dayKey } from "../../src/utils";

const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/workspace.json", import.meta.url), "utf8"),
);
const today = dayKey();

async function checkinApp(
  page: Page,
  options: { checked?: boolean; achieved?: boolean } = {},
) {
  const data = structuredClone(fixture.bootstrap);
  const state = data.state;
  Object.assign(state.settings, {
    theme: "dark",
    avatar: "",
    workspaceName: "签到测试空间",
    includeHot100: true,
    dailyGoal: 1,
  });
  state.checkins = options.checked ? [today] : [];
  if (options.achieved)
    state.events = [
      {
        eventId: "studied",
        problemId: 1,
        rating: "good",
        kind: "new",
        seconds: 15,
        day: today,
        time: new Date().toISOString(),
      },
    ];
  let failing = false;
  let held: Promise<void> | undefined;
  const payloads: Record<string, unknown>[] = [];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/bootstrap") return route.fulfill({ json: data });
    if (path === "/api/action") {
      const payload = route.request().postDataJSON();
      payloads.push(payload);
      if (payload.type === "checkin") {
        if (held) await held;
        if (failing)
          return route.fulfill({
            status: 500,
            json: { error: "签到保存失败，请重试" },
          });
        if (!state.checkins.includes(today)) state.checkins.push(today);
      }
      return route.fulfill({ json: state });
    }
    return route.fulfill({
      status: 404,
      json: { error: "Unexpected check-in test request" },
    });
  });
  return {
    state,
    payloads,
    fail: (value: boolean) => {
      failing = value;
    },
    hold: (value: Promise<void>) => {
      held = value;
    },
  };
}

test("calendar check-in returns from a previous month to today without inventing study progress", async ({
  page,
}) => {
  const app = await checkinApp(page);
  await page.goto("/#calendar");
  await page.getByRole("button", { name: "上个月", exact: true }).click();
  const lastMonth = new Date(
    new Date().getFullYear(),
    new Date().getMonth() - 1,
    1,
  );
  await expect(page.locator(".calendar-panel h2")).toHaveText(
    `${lastMonth.getFullYear()} 年 ${lastMonth.getMonth() + 1} 月`,
  );
  await page.locator(".calendar-cell:not(.outside)").first().click();
  await page.getByRole("button", { name: "签到", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "今日已签到", exact: true }),
  ).toBeDisabled();
  const cell = page.getByRole("button", {
    name: `${today}，学习 0 项，已签到`,
    exact: true,
  });
  await expect(cell).toHaveClass(/selected/);
  await expect(page.locator(".calendar-detail")).toContainText("签到已记录");
  await expect(page.locator(".calendar-panel .panel-bottom")).toContainText(
    "本月学习 0 项 · 打卡 1 天",
  );
  expect(app.payloads).toEqual([{ type: "checkin" }]);
  expect(app.state.events).toEqual([]);
  expect(app.state.knowledgeEvents).toEqual([]);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "今日已签到", exact: true }),
  ).toBeDisabled();
  await expect(cell).toHaveClass(/has-activity/);
  await page.goto("/#today");
  await expect(
    page.getByRole("progressbar", { name: "每日目标进度" }),
  ).toHaveAttribute("aria-valuenow", "0");
  await expect(page.locator(".quest-card")).not.toHaveClass(/is-complete/);
  await expect(page.locator(".streak-summary")).toContainText("1 天连续打卡");
});

test("check-in failure is retryable and rapid clicks cannot produce duplicate pending requests", async ({
  page,
}) => {
  const app = await checkinApp(page);
  await page.goto("/#calendar");
  app.fail(true);
  await page.getByRole("button", { name: "签到", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("签到保存失败");
  await expect(
    page.getByRole("button", { name: "签到", exact: true }),
  ).toBeEnabled();
  expect(app.state.checkins).toEqual([]);
  app.fail(false);
  let release!: () => void;
  app.hold(
    new Promise<void>((resolve) => {
      release = resolve;
    }),
  );
  await page
    .getByRole("button", { name: "签到", exact: true })
    .evaluate((button: HTMLButtonElement) => {
      button.click();
      button.click();
    });
  await expect(
    page.getByRole("button", { name: "签到中…", exact: true }),
  ).toBeDisabled();
  await expect.poll(() => app.payloads.length).toBe(2);
  expect(app.state.checkins).toEqual([]);
  release();
  await expect(
    page.getByRole("button", { name: "今日已签到", exact: true }),
  ).toBeDisabled();
  expect(app.state.checkins).toEqual([today]);
  expect(app.payloads).toHaveLength(2);
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("an achieved learning goal still requires explicit check-in and existing check-ins stay disabled", async ({
  page,
}) => {
  const app = await checkinApp(page, { achieved: true });
  await page.goto("/#today");
  await expect(page.locator(".quest-card")).toHaveClass(/is-complete/);
  await expect(page.locator(".quest-card")).toContainText("学习目标已达成");
  await expect(
    page.getByRole("button", { name: "签到", exact: true }),
  ).toBeEnabled();
  expect(app.payloads).toEqual([]);
  expect(app.state.checkins).toEqual([]);
  await page.getByRole("button", { name: "签到", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "今日已签到", exact: true }),
  ).toBeDisabled();
  expect(app.state.events).toHaveLength(1);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "今日已签到", exact: true }),
  ).toBeDisabled();
  expect(app.payloads).toHaveLength(1);
});
