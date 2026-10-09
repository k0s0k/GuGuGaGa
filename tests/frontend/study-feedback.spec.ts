import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dayKey } from "../../src/utils";

const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/workspace.json", import.meta.url), "utf8"),
);

async function studyApp(page: Page) {
  const data = structuredClone(fixture.bootstrap);
  const state = data.state;
  const day = dayKey();
  const event = {
    day,
    kind: "review",
    rating: "good",
    seconds: 10,
    time: new Date().toISOString(),
  };
  state.settings.includeHot100 = true;
  state.settings.workspaceName = "测试学习空间";
  state.events = [
    { ...event, problemId: 77, eventId: "same-problem-1" },
    { ...event, problemId: 77, eventId: "same-problem-2" },
    { ...event, day: "2020-01-01", problemId: 88, eventId: "old-problem" },
  ];
  state.knowledgeEvents = [
    { ...event, itemId: "77", eventId: "different-knowledge-77" },
  ];
  state.decks = {
    demo: { id: "demo", title: "学习反馈测试", description: "" },
  };
  state.knowledge = Object.fromEntries(
    ["card-1", "card-2"].map((id) => [
      id,
      {
        id,
        deckId: "demo",
        title: id === "card-1" ? "记住一个新知识" : "继续练习",
        kind: "qa",
        prompt: "请先回忆一个知识点。",
        answer: "这是复习答案。",
        tags: [],
        source: "",
        archived: false,
      },
    ]),
  );
  let fail = false;
  let held: Promise<void> | undefined;
  const payloads: Record<string, unknown>[] = [];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/bootstrap") return route.fulfill({ json: data });
    if (path === "/api/problems/1")
      return route.fulfill({ json: fixture.problem });
    if (path === "/api/action") {
      const payload = route.request().postDataJSON();
      payloads.push(payload);
      if (held) await held;
      if (fail)
        return route.fulfill({ status: 500, json: { error: "模拟网络中断" } });
      if (payload.type === "knowledge-rate" || payload.type === "rate") {
        const knowledge = payload.type === "knowledge-rate";
        const records = knowledge ? state.knowledgeEvents : state.events;
        records.push({ ...event, ...payload });
        const cards = knowledge ? state.knowledgeCards : state.cards;
        cards[knowledge ? payload.itemId : payload.problemId] = {
          rating: payload.rating,
          reviews: 1,
          stability: 1,
          lapses: 0,
          status: "learning",
          lastReview: new Date().toISOString(),
          due: new Date(Date.now() + 86400000).toISOString(),
        };
        state.checkins = [day];
      }
      return route.fulfill({ json: state });
    }
    return route.fulfill({
      status: 404,
      json: { error: "Unexpected study test request" },
    });
  });
  return {
    state,
    payloads,
    fail: (value: boolean) => {
      fail = value;
    },
    hold: (value: Promise<void> | undefined) => {
      held = value;
    },
  };
}

async function expectDistinctRatingColors(page: Page) {
  const colors = await page
    .locator(".study-rating-buttons > button")
    .evaluateAll((buttons) =>
      buttons.map((button) => {
        const style = getComputedStyle(button);
        return {
          text: style.color,
          fill: style.backgroundColor,
          border: style.borderTopColor,
        };
      }),
    );
  expect(colors).toHaveLength(4);
  for (const property of ["text", "fill", "border"] as const)
    expect(new Set(colors.map((color) => color[property])).size).toBe(4);
}

test("knowledge study counts unique items, confirms saved feedback and celebrates only the goal crossing", async ({
  page,
}) => {
  const app = await studyApp(page);
  await page.goto("/#knowledge/card-1");
  const progress = page.getByRole("progressbar", { name: "今日学习目标" });
  await expect(progress).toHaveAttribute("aria-valuenow", "2");
  await page.getByRole("button", { name: "显示答案", exact: true }).click();
  await expectDistinctRatingColors(page);
  app.fail(true);
  await page.locator(".rating-button.good").click();
  await expect(page.getByRole("alert")).toContainText("还未保存");
  await expect(page.locator(".study-confirmed")).toHaveCount(0);
  await expect(progress).toHaveAttribute("aria-valuenow", "2");
  app.fail(false);
  let release!: () => void;
  app.hold(
    new Promise<void>((resolve) => {
      release = resolve;
    }),
  );
  await page.locator(".rating-button.good").click();
  await expect(page.locator(".rating-button.good")).toBeDisabled();
  await expect(page.locator(".study-confirmed")).toHaveCount(0);
  release();
  await expect(page.locator(".study-confirmed")).toContainText(
    "今日目标达成！",
  );
  await expect(progress).toHaveAttribute("aria-valuenow", "3");
  const rates = app.payloads.filter(
    (payload) => payload.type === "knowledge-rate",
  );
  expect(rates).toHaveLength(2);
  expect(rates[0].eventId).toBe(rates[1].eventId);
  await page.getByRole("button", { name: "下一个知识点" }).click();
  await expect(page).toHaveURL(/#knowledge\/card-2$/);
  await page.getByRole("button", { name: "显示答案", exact: true }).click();
  await page.locator(".rating-button.again").click();
  await expect(page.locator(".study-confirmed")).toContainText(
    "这次学习，记下啦！",
  );
  await expect(page.locator(".study-confirmed.goal-reached")).toHaveCount(0);
  await expect(progress).toHaveAttribute(
    "aria-valuetext",
    "今天已学习 4 项，目标 3 项",
  );
});

test("coding study confirms a saved review and does not award duplicate progress after reload", async ({
  page,
}) => {
  const app = await studyApp(page);
  await page.goto("/#problem/1");
  await expect(
    page.getByRole("progressbar", { name: "今日学习目标" }),
  ).toHaveAttribute("aria-valuenow", "2");
  await expectDistinctRatingColors(page);
  app.fail(true);
  await page.locator(".rate-good").click();
  await expect(page.getByRole("alert")).toContainText("还未保存");
  await expect(page.locator(".study-confirmed")).toHaveCount(0);
  app.fail(false);
  await page.locator(".rate-good").click();
  await expect(page.locator(".study-confirmed.goal-reached")).toContainText(
    "今日目标达成！",
  );
  await expect(
    page.getByRole("button", { name: "返回今日计划", exact: true }),
  ).toBeVisible();
  const rates = app.payloads.filter((payload) => payload.type === "rate");
  expect(rates[0].eventId).toBe(rates[1].eventId);
  await page.reload();
  await page.locator(".rate-easy").click();
  await expect(page.locator(".study-confirmed")).toContainText(
    "这次学习，记下啦！",
  );
  await expect(page.locator(".study-confirmed.goal-reached")).toHaveCount(0);
  await expect(
    page.getByRole("progressbar", { name: "今日学习目标" }),
  ).toHaveAttribute("aria-valuetext", "今天已学习 3 项，目标 3 项");
});

test("Space reveals knowledge only outside notes and dialogs, with reduced motion respected", async ({
  page,
}) => {
  await studyApp(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/#knowledge/card-1");
  const note = page.getByRole("textbox", { name: "知识点学习笔记" });
  await note.fill("my");
  await note.press("Space");
  await expect(note).toHaveValue("my ");
  await expect(page.locator(".knowledge-answer")).toHaveCount(0);
  await page.getByRole("button", { name: "编辑知识点", exact: true }).click();
  await page.getByRole("dialog").getByRole("heading").click();
  await page.keyboard.press("Space");
  await expect(page.locator(".knowledge-answer")).toHaveCount(0);
  await page.getByRole("button", { name: "关闭对话框" }).click();
  await page
    .getByRole("heading", { name: "记住一个新知识", exact: true })
    .click();
  await page.keyboard.press("Space");
  await expect(page.locator(".knowledge-answer")).toBeVisible();
  await expect(page.locator(".knowledge-answer")).toHaveCSS(
    "animation-name",
    "none",
  );
  await expect(page.locator(".knowledge-answer")).toHaveCSS(
    "animation-duration",
    "0s",
  );
  await expect(page.locator(".rating-button.good")).toHaveCSS(
    "transition-duration",
    "0s",
  );
});

test("knowledge feedback and next action fit a narrow screen", async ({
  page,
}) => {
  await studyApp(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/#knowledge/card-1");
  await page.getByRole("button", { name: "显示答案", exact: true }).click();
  await page.locator(".rating-button.good").click();
  await expect(page.locator(".study-confirmed.goal-reached")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "下一个知识点" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
});
