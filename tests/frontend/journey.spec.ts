import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dayKey } from "../../src/utils";

const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/workspace.json", import.meta.url), "utf8"),
);

async function setup(page: Page) {
  const data = structuredClone(fixture.bootstrap);
  data.problems = Array.from({ length: 9 }, (_, index) => ({
    ...data.problems[0],
    id: index + 1,
    title: index ? `学习任务 ${index + 1}` : "两数之和",
  }));
  Object.assign(data.state.settings, {
    newPerDay: 2,
    dailyGoal: 3,
    workspaceName: "咕咕的学习空间",
    avatar: "",
    includeHot100: true,
  });
  for (let id = 1; id <= 7; id++)
    data.state.cards[id] = {
      stability: 1,
      due: "2020-01-01T00:00:00Z",
      lastReview: "2020-01-01T00:00:00Z",
      reviews: 1,
      lapses: 0,
      rating: "good",
      status: "review",
    };
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/bootstrap") return route.fulfill({ json: data });
    if (path === "/api/problems/1")
      return route.fulfill({ json: fixture.problem });
    if (path === "/api/action") {
      const input = route.request().postDataJSON();
      if (input.type === "settings")
        Object.assign(data.state.settings, input.settings);
      return route.fulfill({ json: data.state });
    }
    return route.fulfill({
      status: 404,
      json: { error: "Unexpected request" },
    });
  });
  return data;
}

test("journey expands the full queue, filters reviews and opens a real study route", async ({
  page,
}) => {
  await setup(page);
  await page.goto("/#today");
  await expect(page.locator(".journey-step")).toHaveCount(6);
  await page.getByRole("button", { name: "查看剩余 3 项" }).click();
  await expect(page.locator(".journey-step")).toHaveCount(9);
  await page.getByRole("button", { name: "新知", exact: true }).click();
  await expect(page.locator(".journey-step")).toHaveCount(2);
  await expect(page.locator(".journey-step").first()).toContainText(
    "学习任务 8",
  );
  await page
    .locator(".journey-filters")
    .getByRole("button", { name: "待复习" })
    .click();
  await expect(page.locator(".journey-step")).toHaveCount(6);
  await page.getByRole("button", { name: "查看剩余 1 项" }).click();
  await expect(page.locator(".journey-step")).toHaveCount(7);
  await page
    .getByRole("button", { name: "开始 两数之和", exact: true })
    .click();
  await expect(page).toHaveURL(/#problem\/1$/);
  await expect(page.locator(".code-editor .cm-content")).toBeVisible();
});

test("daily goal is based on unique items and check-in links to the calendar", async ({
  page,
}) => {
  const data = await setup(page);
  data.state.events = [1, 1, 2].map((problemId, index) => ({
    problemId,
    eventId: `event-${index}`,
    day: dayKey(),
    time: new Date().toISOString(),
    rating: "good",
    kind: "review",
    seconds: 20,
  }));
  await page.goto("/#today");
  await expect(
    page.getByRole("progressbar", { name: "每日目标进度" }),
  ).toHaveAttribute("aria-valuenow", "2");
  await expect(page.locator(".quest-card")).toContainText("再完成 1 项");
  await page.getByRole("button", { name: "查看学习日历", exact: true }).click();
  await expect(page).toHaveURL(/#calendar$/);
});

test("journey and navigation fit mobile and desktop in both themes", async ({
  page,
}) => {
  await setup(page);
  await page.goto("/#today");
  for (const theme of ["light", "dark"]) {
    if (theme === "dark")
      await page.getByRole("button", { name: "切换明暗主题" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
    for (const width of [1440, 980, 390]) {
      await page.setViewportSize({ width, height: 900 });
      if (width < 760) await expect(page.locator(".sidebar")).not.toBeInViewport();
      await expect(page.locator(".journey-banner")).toBeVisible();
      const fits = await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      );
      expect(fits, `${theme} at ${width}px`).toBe(true);
      await page.screenshot({
        path: `.local/journey-${theme}-${width}.png`,
        fullPage: true,
      });
    }
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.locator(".quest-meter > span")).toHaveCSS(
    "transition-duration",
    "0s",
  );
});
