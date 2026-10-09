import { expect, test } from "@playwright/test";
import type { APIRequestContext, Page } from "@playwright/test";
import { spawn } from "node:child_process";
import type { ChildProcess } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type { AppState, KnowledgeDocument } from "../../src/types";
import { dateShift, dayKey } from "../../src/utils";

// Exercise the built app against an isolated database; never change real plans.
const baseURL = "http://127.0.0.1:8899";
const root = fileURLToPath(new URL("../../", import.meta.url));
const screenshots = join(root, ".local", "study-plan-screenshots");
type PlanState = AppState & {
  settings: AppState["settings"] & { studyDeckIds: string[] };
};
let backend: ChildProcess | undefined;
let initialState: PlanState;
let token = "";

const cpp: KnowledgeDocument = {
  format: "coderecall.knowledge",
  version: 1,
  deck: { id: "plan-cpp", title: "C++ 概念复习" },
  items: [
    {
      id: "cpp-new",
      title: "理解 C++ 引用",
      kind: "qa",
      prompt: "引用是什么？",
      answer: "已有对象的别名。",
    },
    {
      id: "cpp-review",
      title: "复习 C++ 生命周期",
      kind: "qa",
      prompt: "局部对象何时析构？",
      answer: "离开其作用域时。",
    },
  ],
};
const english: KnowledgeDocument = {
  format: "coderecall.knowledge",
  version: 1,
  deck: { id: "plan-english", title: "英语短句" },
  items: [
    {
      id: "english-new",
      title: "用英语描述今天",
      kind: "qa",
      prompt: "说出今天发生的一件事。",
      answer: "I learned something new today.",
    },
    {
      id: "english-review",
      title: "复习英语过去时",
      kind: "qa",
      prompt: "learn 的过去式？",
      answer: "learned / learnt",
    },
  ],
};
test.use({ baseURL });

test.beforeAll(async () => {
  try {
    await fetch(`${baseURL}/api/bootstrap`, {
      signal: AbortSignal.timeout(500),
    });
    throw new Error(
      "Test port 8899 is occupied; refusing to use another process's data.",
    );
  } catch (error) {
    if ((error as Error).message.startsWith("Test port")) throw error;
  }
  const directory = join(
    root,
    ".local",
    `study-plans-e2e-${process.pid}-${Date.now()}`,
  );
  const temporary = join(directory, "tmp");
  mkdirSync(temporary, { recursive: true });
  mkdirSync(screenshots, { recursive: true });
  backend = spawn(
    process.env.CODERECALL_TEST_PYTHON || "python",
    [
      "-m",
      "server.app",
      "--port",
      "8899",
      "--data",
      join(directory, "test.db"),
    ],
    {
      cwd: root,
      windowsHide: true,
      stdio: "ignore",
      env: { ...process.env, TEMP: temporary, TMP: temporary },
    },
  );
  let launchError: Error | undefined;
  backend.on("error", (error) => {
    launchError = error;
  });
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    if (launchError) throw launchError;
    if (backend.exitCode !== null)
      throw new Error(
        `Isolated study-plan backend exited with ${backend.exitCode}`,
      );
    try {
      const response = await fetch(`${baseURL}/api/bootstrap`, {
        signal: AbortSignal.timeout(1000),
      });
      if (response.ok) {
        const payload = await response.json();
        token = payload.token;
        initialState = payload.state;
        expect(initialState.settings.studyDeckIds).toEqual([]);
        return;
      }
    } catch {
      /* The isolated server may still be starting. */
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error(
    "The isolated study-plan backend did not start within 20 seconds.",
  );
});

test.afterAll(async () => {
  if (!backend || backend.exitCode !== null) return;
  const stopped = new Promise<void>((resolve) =>
    backend!.once("exit", () => resolve()),
  );
  backend.kill();
  await Promise.race([
    stopped,
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
});
async function action(
  request: APIRequestContext,
  payload: unknown,
): Promise<PlanState> {
  const response = await request.post(`${baseURL}/api/action`, {
    headers: { "X-CodeRecall-Token": token },
    data: payload,
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}
async function savedState(request: APIRequestContext): Promise<PlanState> {
  const response = await request.get(`${baseURL}/api/state`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}
test.beforeEach(async ({ request }) => {
  await action(request, {
    type: "import",
    state: structuredClone(initialState),
  });
  await action(request, { type: "knowledge-import", document: cpp });
  await action(request, { type: "knowledge-import", document: english });
});

async function openPlans(page: Page) {
  if (
    (page.viewportSize()?.width ?? 1440) <= 760 &&
    !(await page
      .locator(".sidebar")
      .evaluate((node) => node.classList.contains("open")))
  )
    await page.getByRole("button", { name: "打开侧栏", exact: true }).click();
  await page.getByRole("button", { name: "管理学习计划", exact: true }).click();
  const dialog = page.getByRole("dialog", {
    name: "我的学习计划",
    exact: true,
  });
  await expect(dialog).toBeVisible();
  return dialog;
}

test("newly imported decks join only after saving; selected plans persist and open the filtered knowledge library", async ({
  page,
  request,
}) => {
  const allDeck: KnowledgeDocument = {
    format: "coderecall.knowledge",
    version: 1,
    deck: { id: "all", title: "名为 all 的独立知识库" },
    items: [
      {
        id: "all-card",
        title: "all 知识库专属卡片",
        kind: "qa",
        prompt: "这个知识点属于哪个库？",
        answer: "标识为 all 的独立知识库。",
      },
    ],
  };
  await action(request, { type: "knowledge-import", document: allDeck });
  expect((await savedState(request)).settings.studyDeckIds).toEqual([]);
  await page.goto("/#today");
  const plans = page.locator(".sidebar-study-plans");
  await expect(
    plans.getByRole("button", {
      name: `打开学习计划：${cpp.deck.title}`,
      exact: true,
    }),
  ).toHaveCount(0);
  const dialog = await openPlans(page);
  await expect(
    dialog.getByRole("checkbox", { name: cpp.deck.title, exact: true }),
  ).not.toBeChecked();
  await dialog
    .getByRole("checkbox", { name: "LeetCode Hot 100", exact: true })
    .check();
  await dialog
    .getByRole("checkbox", { name: cpp.deck.title, exact: true })
    .check();
  await dialog
    .getByRole("checkbox", { name: english.deck.title, exact: true })
    .check();
  await dialog
    .getByRole("checkbox", { name: allDeck.deck.title, exact: true })
    .check();
  expect((await savedState(request)).settings.studyDeckIds).toEqual([]);
  await dialog
    .getByRole("button", { name: "保存学习计划", exact: true })
    .click();
  await expect(dialog).not.toBeVisible();
  expect((await savedState(request)).settings.studyDeckIds.sort()).toEqual([
    "all",
    "plan-cpp",
    "plan-english",
  ]);
  await page.reload();
  await expect(
    plans.getByRole("button", {
      name: `打开学习计划：${english.deck.title}`,
      exact: true,
    }),
  ).toBeVisible();
  await plans
    .getByRole("button", {
      name: `打开学习计划：${cpp.deck.title}`,
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(/#knowledge\?deck=plan-cpp$/);
  await expect(
    page.getByRole("button", { name: "打开 理解 C++ 引用", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "打开 用英语描述今天", exact: true }),
  ).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "打开 复习 C++ 生命周期", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "打开 复习英语过去时", exact: true }),
  ).toHaveCount(0);
  await plans
    .getByRole("button", {
      name: `打开学习计划：${allDeck.deck.title}`,
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(/#knowledge\?deck=all$/);
  await expect(
    page.getByRole("button", { name: "打开 all 知识库专属卡片", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "打开 理解 C++ 引用", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "打开 用英语描述今天", exact: true }),
  ).toHaveCount(0);
  await page.reload();
  await expect(page).toHaveURL(/#knowledge\?deck=all$/);
  await expect(
    page.getByRole("button", { name: "打开 all 知识库专属卡片", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "打开 理解 C++ 引用", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: /^全部知识库/ }).click();
  await expect(page).toHaveURL(/#knowledge$/);
  await expect(
    page.getByRole("button", { name: "打开 all 知识库专属卡片", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "打开 理解 C++ 引用", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "打开 用英语描述今天", exact: true }),
  ).toBeVisible();
});

test("today and due reviews use selected decks; deselecting retains knowledge, notes, history and stones", async ({
  page,
  request,
}) => {
  await action(request, {
    type: "knowledge-rate",
    itemId: "cpp-review",
    rating: "good",
    eventId: "plan-cpp-past",
  });
  await action(request, {
    type: "knowledge-rate",
    itemId: "english-review",
    rating: "good",
    eventId: "plan-english-past",
  });
  let prior = await action(request, {
    type: "knowledge-note",
    itemId: "cpp-review",
    text: "自己的复习笔记",
  });
  const old = structuredClone(prior);
  const yesterday = dayKey(dateShift(new Date(), -1));
  for (const card of Object.values(old.knowledgeCards)) {
    card.lastReview = `${yesterday}T09:00:00+08:00`;
    card.due = `${yesterday}T10:00:00+08:00`;
  }
  for (const event of old.knowledgeEvents) {
    event.day = yesterday;
    event.time = `${yesterday}T09:00:00+08:00`;
  }
  delete old.stones;
  old.settings.includeHot100 = false;
  old.settings.studyDeckIds = ["plan-cpp"];
  prior = await action(request, { type: "import", state: old });
  await page.goto("/#today");
  const steps = page.locator(".journey-step");
  await expect(steps).toHaveCount(2);
  await expect(steps.filter({ hasText: "理解 C++ 引用" })).toBeVisible();
  await expect(steps.filter({ hasText: "复习 C++ 生命周期" })).toBeVisible();
  await page.goto("/#review");
  await expect(page.locator(".review-row")).toHaveCount(1);
  await expect(page.locator(".review-row")).toContainText("复习 C++ 生命周期");
  const dialog = await openPlans(page);
  await dialog
    .getByRole("checkbox", { name: cpp.deck.title, exact: true })
    .uncheck();
  await dialog
    .getByRole("button", { name: "保存学习计划", exact: true })
    .click();
  await expect(dialog).not.toBeVisible();
  await expect(page.locator(".review-row")).toHaveCount(0);
  await page.goto("/#today");
  await expect(steps).toHaveCount(0);
  const after = await savedState(request);
  expect(after.settings.studyDeckIds).toEqual([]);
  for (const field of [
    "decks",
    "knowledge",
    "knowledgeNotes",
    "knowledgeCards",
    "knowledgeEvents",
    "stones",
  ] as const)
    expect(after[field]).toEqual(prior[field]);
  await page.goto("/#knowledge");
  await expect(
    page.getByRole("button", { name: "打开 理解 C++ 引用", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "打开 用英语描述今天", exact: true }),
  ).toBeVisible();
});

test("failed plan saves retain selected checkboxes and retry once with busy protection", async ({
  page,
  request,
}) => {
  let attempts = 0;
  let release!: () => void;
  const paused = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/action", async (route) => {
    const input = route.request().postDataJSON();
    if (input.type !== "settings" || !("studyDeckIds" in input.settings))
      return route.continue();
    attempts++;
    if (attempts === 1)
      return route.fulfill({
        status: 500,
        json: { error: "学习计划暂时保存失败" },
      });
    const response = await route.fetch();
    await paused;
    await route.fulfill({ response });
  });
  await page.goto("/#today");
  const dialog = await openPlans(page);
  const cppOption = dialog.getByRole("checkbox", {
    name: cpp.deck.title,
    exact: true,
  });
  await cppOption.check();
  const save = dialog.getByRole("button", { name: /保存学习计划|保存中/ });
  await save.click();
  await expect(dialog.getByRole("alert")).toContainText("学习计划暂时保存失败");
  await expect(cppOption).toBeChecked();
  expect((await savedState(request)).settings.studyDeckIds).toEqual([]);
  try {
    await save.evaluate((node: HTMLButtonElement) => {
      node.click();
      node.click();
    });
    await expect(save).toBeDisabled();
    await expect(cppOption).toBeDisabled();
    await expect
      .poll(async () => (await savedState(request)).settings.studyDeckIds)
      .toEqual(["plan-cpp"]);
    expect(attempts).toBe(2);
  } finally {
    release();
  }
  await expect(dialog).not.toBeVisible();
  await expect(
    page.locator(".sidebar-study-plans").getByRole("button", {
      name: `打开学习计划：${cpp.deck.title}`,
      exact: true,
    }),
  ).toBeVisible();
});

test("full backup export and restore includes selected plans and their knowledge libraries", async ({
  page,
  request,
}) => {
  await action(request, {
    type: "settings",
    settings: { studyDeckIds: ["plan-english"], includeHot100: false },
  });
  await page.goto("/#settings");
  const downloading = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出备份", exact: true }).click();
  const download = await downloading;
  const backup = JSON.parse(readFileSync((await download.path())!, "utf8"));
  expect(backup.settings.studyDeckIds).toEqual(["plan-english"]);
  await action(request, {
    type: "import",
    state: structuredClone(initialState),
  });
  await page.reload();
  await page
    .locator('input[type="file"][accept="application/json,.json"]')
    .setInputFiles({
      name: "study-plans-backup.json",
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify(backup)),
    });
  await page.getByRole("button", { name: "确认导入", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "导入这份学习备份？", exact: true }),
  ).not.toBeVisible();
  const saved = await savedState(request);
  expect(saved.settings.studyDeckIds).toEqual(["plan-english"]);
  expect(saved.settings.includeHot100).toBe(false);
  expect(saved.knowledge).toEqual(backup.knowledge);
  await page
    .locator(".sidebar-study-plans")
    .getByRole("button", {
      name: `打开学习计划：${english.deck.title}`,
      exact: true,
    })
    .click();
  await expect(page).toHaveURL(/#knowledge\?deck=plan-english$/);
  await expect(
    page.getByRole("button", { name: "打开 用英语描述今天", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "打开 理解 C++ 引用", exact: true }),
  ).toHaveCount(0);
});

test("390px long titles fit; keyboard toggling, modal shortcut protection and Escape do not save drafts", async ({
  page,
  request,
}) => {
  const longTitle = "我的石头收藏与 Blender 动画制作学习".repeat(4);
  await action(request, {
    type: "deck-save",
    deck: { id: "long-plan", title: longTitle, description: "长标题布局测试" },
  });
  await page.setViewportSize({ width: 390, height: 700 });
  await page.goto("/#today");
  let dialog = await openPlans(page);
  const option = dialog.getByRole("checkbox", { name: longTitle, exact: true });
  await option.focus();
  await page.keyboard.press("Space");
  await expect(option).toBeChecked();
  await page.clock.install();
  await page.keyboard.press("ControlOrMeta+k");
  await page.clock.runFor(200);
  await expect(page).toHaveURL(/#today$/);
  await expect(dialog).toBeVisible();
  expect(
    await dialog.evaluate((node) => node.contains(document.activeElement)),
  ).toBe(true);
  const box = (await dialog.boundingBox())!;
  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(390);
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(700);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth - innerWidth,
    ),
  ).toBeLessThanOrEqual(1);
  await page.screenshot({
    path: join(screenshots, "study-plan-dialog-390.png"),
  });
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  expect((await savedState(request)).settings.studyDeckIds).toEqual([]);
  dialog = await openPlans(page);
  await expect(option).not.toBeChecked();
  await option.check();
  await dialog
    .getByRole("button", { name: "保存学习计划", exact: true })
    .click();
  await expect(dialog).not.toBeVisible();
  const planLink = page
    .locator(".sidebar-study-plans")
    .getByRole("button", { name: `打开学习计划：${longTitle}`, exact: true });
  await planLink.scrollIntoViewIfNeeded();
  await expect(planLink).toBeInViewport({ ratio: 1 });
  const linkBox = (await planLink.boundingBox())!;
  const sideBox = (await page.locator(".sidebar").boundingBox())!;
  expect(linkBox.x + linkBox.width).toBeLessThanOrEqual(
    sideBox.x + sideBox.width,
  );
  await page.screenshot({
    path: join(screenshots, "study-plan-sidebar-390.png"),
  });
  await planLink.click();
  await expect(page).toHaveURL(/#knowledge\?deck=long-plan$/);
  await expect(page.locator(".sidebar")).not.toHaveClass(/open/);
});

test("backups made before plan selection migrate all existing decks while explicit empty plans stay empty", async ({
  page,
  request,
}) => {
  const old = structuredClone(await savedState(request));
  delete (old.settings as Partial<PlanState["settings"]>).studyDeckIds;
  const migrated = await action(request, { type: "import", state: old });
  expect(migrated.settings.studyDeckIds.sort()).toEqual([
    "plan-cpp",
    "plan-english",
  ]);
  await page.goto("/#today");
  let dialog = await openPlans(page);
  await expect(
    dialog.getByRole("checkbox", { name: cpp.deck.title, exact: true }),
  ).toBeChecked();
  await expect(
    dialog.getByRole("checkbox", { name: english.deck.title, exact: true }),
  ).toBeChecked();
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  await action(request, {
    type: "import",
    state: {
      ...migrated,
      settings: { ...migrated.settings, studyDeckIds: [] },
    },
  });
  await page.reload();
  dialog = await openPlans(page);
  await expect(
    dialog.getByRole("checkbox", { name: cpp.deck.title, exact: true }),
  ).not.toBeChecked();
  await expect(
    dialog.getByRole("checkbox", { name: english.deck.title, exact: true }),
  ).not.toBeChecked();
});
