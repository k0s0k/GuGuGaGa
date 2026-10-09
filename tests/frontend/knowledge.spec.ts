import { test, expect } from "@playwright/test";
import type { APIRequestContext, Page } from "@playwright/test";
import { spawn } from "node:child_process";
import type { ChildProcess } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type { AppState, KnowledgeDocument } from "../../src/types";

// This suite exercises the built application against a real, isolated SQLite
// database. It never contacts an AI provider or reads/writes the user's database.
const baseURL = "http://127.0.0.1:8896";
const root = fileURLToPath(new URL("../../", import.meta.url));
const screenshots = join(root, ".local", "v2-screenshots");
let backend: ChildProcess | undefined;
let token = "";
let initialState: AppState;

test.use({ baseURL });

test.beforeAll(async () => {
  try {
    const occupied = await fetch(`${baseURL}/api/bootstrap`, {
      signal: AbortSignal.timeout(500),
    });
    if (occupied)
      throw new Error(
        "Test port 8896 is occupied; refusing to use another process's data.",
      );
  } catch (error) {
    if ((error as Error).message.startsWith("Test port")) throw error;
  }
  const directory = join(
    root,
    ".local",
    `knowledge-e2e-${process.pid}-${Date.now()}`,
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
      "8896",
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
      throw new Error(`Isolated backend exited with ${backend.exitCode}`);
    try {
      const response = await fetch(`${baseURL}/api/bootstrap`, {
        signal: AbortSignal.timeout(1000),
      });
      if (response.ok) {
        const bootstrap = await response.json();
        token = bootstrap.token;
        initialState = bootstrap.state;
        expect(initialState.version).toBe(2);
        return;
      }
    } catch {
      /* Starting the isolated process can take a moment. */
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error(
    "The isolated knowledge backend did not start within 20 seconds.",
  );
});

test.afterAll(async () => {
  if (!backend || backend.exitCode !== null) return;
  const stopped = new Promise<void>((resolve) =>
    backend!.once("exit", () => resolve()),
  );
  backend.kill(); // Only the ChildProcess created by this file is terminated.
  await Promise.race([
    stopped,
    new Promise((resolve) => setTimeout(resolve, 3000)),
  ]);
});

async function action(
  request: APIRequestContext,
  payload: unknown,
): Promise<AppState> {
  const response = await request.post(`${baseURL}/api/action`, {
    headers: { "X-CodeRecall-Token": token },
    data: payload,
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}

async function state(request: APIRequestContext): Promise<AppState> {
  const response = await request.get(`${baseURL}/api/state`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}

function knowledgeDocument(
  id = "qa-card",
  kind: "qa" | "cloze" = "qa",
): KnowledgeDocument {
  return {
    format: "coderecall.knowledge",
    version: 1,
    deck: {
      id: "test-deck",
      title: "测试知识库",
      description: "仅用于自动化测试",
    },
    items: [
      {
        id,
        title: kind === "cloze" ? "填空练习" : "主动回忆练习",
        kind,
        prompt:
          kind === "cloze"
            ? "C++ 的 {{c1::RAII}} 依赖 {{c2::对象生命周期}}。"
            : "主动回忆为什么有效？",
        answer: "## 核心答案\n\n通过提取记忆来巩固理解。",
        tags: ["测试"],
        source: "本地测试笔记",
      },
    ],
  };
}

async function openKnowledge(page: Page) {
  await page.goto("/#knowledge");
  await expect(
    page.getByRole("heading", { name: "你的知识，值得被记住。" }),
  ).toBeVisible();
}

test.beforeEach(async ({ request }) => {
  await action(request, {
    type: "import",
    state: structuredClone(initialState),
  });
});

test("manual deck and card creation/editing persist through reload", async ({
  page,
  request,
}) => {
  await openKnowledge(page);
  await page.getByRole("button", { name: "新建知识库", exact: true }).click();
  let dialog = page.getByRole("dialog", { name: "新建知识库" });
  await dialog
    .getByLabel("知识库名称", { exact: true })
    .fill("我的 Blender 学习");
  await dialog.getByLabel("学习目标").fill("每周完成一个动画练习");
  await dialog.getByRole("button", { name: "保存知识库", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await page.getByRole("button", { name: "新建知识点", exact: true }).click();
  dialog = page.getByRole("dialog", { name: "新建知识点" });
  await dialog.getByLabel("知识点标题", { exact: true }).fill("关键帧的作用");
  await dialog.getByLabel("问题 / 练习要求").fill("关键帧记录什么？");
  await dialog.getByLabel("答案 / 验收清单").fill("关键帧记录特定帧的属性值。");
  await dialog.getByLabel("标签", { exact: true }).fill("动画, 关键帧");
  await dialog.getByRole("button", { name: "保存知识点", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await page
    .getByRole("button", { name: "编辑 我的 Blender 学习", exact: true })
    .click();
  dialog = page.getByRole("dialog", { name: "编辑知识库" });
  await dialog
    .getByLabel("知识库名称", { exact: true })
    .fill("Blender 动画基础");
  await dialog.getByRole("button", { name: "保存知识库", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await page.screenshot({
    path: join(screenshots, "knowledge-list.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "打开 关键帧的作用", exact: true })
    .click();
  await page.getByRole("button", { name: "编辑知识点", exact: true }).click();
  dialog = page.getByRole("dialog", { name: "编辑知识点" });
  await dialog
    .getByLabel("答案 / 验收清单")
    .fill("## 我的理解\n\n关键帧保存某一时刻的位置、旋转等属性。");
  await dialog.getByRole("button", { name: "保存知识点", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "关键帧的作用", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "显示答案", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "我的理解", exact: true }),
  ).toBeVisible();
  const saved = await state(request);
  expect(Object.values(saved.decks)[0].title).toBe("Blender 动画基础");
  expect(Object.values(saved.knowledge)[0].tags).toEqual(["动画", "关键帧"]);
  expect(Object.values(saved.knowledge)[0].answer).toContain("某一时刻的位置");
});

test("revealing and rating a real card joins LeetCode in calendar check-ins", async ({
  page,
  request,
}) => {
  await action(request, {
    type: "knowledge-import",
    document: knowledgeDocument(),
  });
  await action(request, { type: "settings", settings: { dailyGoal: 2 } });
  await page.goto("/#knowledge/qa-card");
  await expect(
    page.getByRole("heading", { name: "主动回忆练习", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "核心答案", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "显示答案", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "核心答案", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: join(screenshots, "knowledge-study.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: /^记住了/ }).click();
  await expect
    .poll(async () => (await state(request)).knowledgeCards["qa-card"]?.reviews)
    .toBe(1);
  expect((await state(request)).checkins).toEqual([]);
  const combined = await action(request, {
    type: "rate",
    problemId: 1,
    rating: "good",
    eventId: "calendar-lc",
  });
  const day = combined.knowledgeEvents[0].day;
  expect(combined.checkins).toContain(day);
  await page.goto("/#calendar");
  await page.reload(); // The preceding LeetCode event was seeded outside the UI.
  await page
    .getByRole("button", { name: `${day}，学习 2 项`, exact: true })
    .click();
  await expect(page.getByText("今日目标已完成", { exact: true })).toBeVisible();
  await expect(
    page.locator(".timeline").getByText("主动回忆练习", { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".timeline").getByText("两数之和", { exact: true }),
  ).toBeVisible();
  await page
    .locator(".timeline")
    .getByRole("button", { name: /主动回忆练习/ })
    .click();
  await expect(page).toHaveURL(/#knowledge\/qa-card$/);
  await expect(
    page.getByRole("button", { name: "显示答案", exact: true }),
  ).toBeVisible();
});

test("local Markdown split stays a preview until edited cards are imported", async ({
  page,
  request,
}) => {
  await openKnowledge(page);
  await page
    .getByRole("button", { name: "导入 / 拆分文档", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "将笔记变成可复习的知识" });
  await dialog.getByLabel("导入为知识库", { exact: true }).fill("C++ 笔记拆分");
  await dialog
    .getByLabel("笔记内容", { exact: true })
    .fill(
      "# C++ 笔记\n## 栈\n后进先出。\n```python\n# this is code, not a section\nprint(1)\n```\n## 引用\n引用是已有对象的别名。",
    );
  await dialog.getByRole("button", { name: "拆分并预览", exact: true }).click();
  await expect(
    dialog.getByText("2 个候选知识点 · 已选择 2 个", { exact: true }),
  ).toBeVisible();
  expect(Object.keys((await state(request)).knowledge)).toHaveLength(0);
  await dialog.getByRole("button", { name: "编辑此卡", exact: true }).click();
  await dialog.getByLabel("预览标题", { exact: true }).fill("我自己的栈问题");
  await dialog.getByLabel("预览问题").fill("如何用自己的话说明栈？");
  await dialog
    .getByLabel("预览答案")
    .fill("**后进先出**，最后放入的元素最先取出。");
  await dialog.getByRole("button", { name: "查看渲染", exact: true }).click();
  await page.screenshot({
    path: join(screenshots, "knowledge-import-preview.png"),
    fullPage: true,
  });
  await dialog
    .getByRole("button", { name: "确认导入 2 个知识点", exact: true })
    .click();
  await expect(dialog).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "打开 我自己的栈问题", exact: true }),
  ).toBeVisible();
  const saved = await state(request);
  expect(Object.keys(saved.knowledge)).toHaveLength(2);
  expect(
    Object.values(saved.knowledge).find(
      (item) => item.title === "我自己的栈问题",
    )?.answer,
  ).toContain("最后放入");
  await page.reload();
  await expect(
    page.getByRole("button", { name: "打开 引用", exact: true }),
  ).toBeVisible();
});

test("JSON cloze import, Markdown notes and reversible archive survive reopening", async ({
  page,
  request,
}) => {
  await openKnowledge(page);
  await page
    .getByRole("button", { name: "导入 / 拆分文档", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "将笔记变成可复习的知识" });
  await dialog
    .getByRole("button", { name: "标准知识库 .json", exact: true })
    .click();
  await dialog
    .getByLabel("知识库 JSON", { exact: true })
    .fill(JSON.stringify(knowledgeDocument("cloze-card", "cloze")));
  await dialog.getByRole("button", { name: "校验并预览", exact: true }).click();
  await expect(
    dialog.getByRole("button", { name: "确认导入 1 个知识点", exact: true }),
  ).toBeVisible();
  expect(Object.keys((await state(request)).knowledge)).toHaveLength(0);
  await dialog
    .getByRole("button", { name: "确认导入 1 个知识点", exact: true })
    .click();
  await expect(dialog).toHaveCount(0);
  await page
    .getByRole("button", { name: "打开 填空练习", exact: true })
    .click();
  await expect(page.locator(".knowledge-prompt")).not.toContainText("RAII");
  await expect(page.locator(".knowledge-prompt")).toContainText("[ …… ]");
  await page.getByRole("button", { name: "显示答案", exact: true }).click();
  await expect(page.locator(".knowledge-prompt")).toContainText("RAII");
  await expect(page.locator(".knowledge-prompt")).toContainText("对象生命周期");
  await page
    .getByLabel("知识点学习笔记", { exact: true })
    .fill(
      "## 易错点\n\n- 资源绑定对象。\n\n```cpp\nstd::unique_ptr<int> p;\n```",
    );
  await page.getByRole("button", { name: "保存笔记", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "保存笔记", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Markdown 预览", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "易错点", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".knowledge-study-notes pre code")).toContainText(
    "unique_ptr",
  );
  page.once("dialog", (confirmation) => confirmation.accept());
  await page.getByRole("button", { name: "归档知识点", exact: true }).click();
  await expect
    .poll(async () => (await state(request)).knowledge["cloze-card"].archived)
    .toBe(true);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "恢复知识点", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("知识点学习笔记", { exact: true })).toHaveValue(
    /## 易错点/,
  );
  await page.getByRole("button", { name: "返回知识库", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "打开 填空练习", exact: true }),
  ).toHaveCount(0);
  await page.getByLabel("知识点状态", { exact: true }).selectOption("archived");
  await page
    .getByRole("button", { name: "打开 填空练习", exact: true })
    .click();
  await page.getByRole("button", { name: "恢复知识点", exact: true }).click();
  await expect
    .poll(async () => (await state(request)).knowledge["cloze-card"].archived)
    .toBe(false);
  await page.reload();
  expect((await state(request)).knowledgeNotes["cloze-card"]).toContain(
    "unique_ptr",
  );
});

test("disabling Hot100 recommendations leaves a knowledge-only plan and keeps the library", async ({
  page,
  request,
}) => {
  await action(request, {
    type: "knowledge-import",
    document: knowledgeDocument(),
  });
  await page.goto("/#today");
  await expect(page.locator(".today-panel .problem-row")).toHaveCount(3);
  await expect(page.locator(".today-panel .problem-id")).toHaveCount(2);
  await page.screenshot({
    path: join(screenshots, "dashboard.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "偏好设置", exact: true }).click();
  // This preference is controlled by the persisted response, so await that response.
  await page.getByLabel("每日计划包含 Hot100", { exact: true }).click();
  await expect
    .poll(async () => (await state(request)).settings.includeHot100)
    .toBe(false);
  await expect(
    page.getByLabel("每日计划包含 Hot100", { exact: true }),
  ).not.toBeChecked();
  await page.getByRole("button", { name: "今日学习", exact: true }).click();
  await expect(page.locator(".today-panel .problem-row")).toHaveCount(1);
  await page.getByRole("button", { name: "切换明暗主题", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.screenshot({
    path: join(screenshots, "dashboard-dark.png"),
    fullPage: true,
  });
  await expect(page.locator(".today-panel .problem-id")).toHaveCount(0);
  await expect(
    page.locator(".today-panel").getByText("主动回忆练习", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(page.locator(".today-panel .problem-row")).toHaveCount(1);
  await page.getByRole("button", { name: /Hot 100 题库/ }).click();
  await expect(page.getByText("两数之和", { exact: true })).toBeVisible();
  expect((await state(request)).settings.includeHot100).toBe(false);
});

test("v2 backup download and confirmed restore retain knowledge, notes, solutions and avatar", async ({
  page,
  request,
}) => {
  await action(request, {
    type: "knowledge-import",
    document: knowledgeDocument(),
  });
  await action(request, {
    type: "knowledge-note",
    itemId: "qa-card",
    text: "备份中的个人笔记",
  });
  await action(request, {
    type: "solution",
    problemId: 1,
    language: "python",
    mode: "leetcode",
    solution: {
      brief: "# mine",
      annotated: "# my annotated solution",
      explanation: "## 自己的解析",
    },
  });
  await page.goto("/#settings");
  await page.getByLabel("上传用户头像", { exact: true }).setInputFiles({
    name: "profile.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC",
      "base64",
    ),
  });
  await page.getByRole("button", { name: "保存头像", exact: true }).click();
  await expect(page.locator(".profile .avatar img")).toBeVisible();
  const saved = await state(request);
  expect(saved.settings.avatar).toMatch(/^data:image\/png;base64,/);
  const downloading = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出备份", exact: true }).click();
  const downloaded = await downloading;
  const downloadedPath = await downloaded.path();
  expect(downloadedPath).not.toBeNull();
  const backup = JSON.parse(readFileSync(downloadedPath!, "utf8"));
  expect(backup).toEqual(saved);
  expect(backup.settings.avatar).toBe(saved.settings.avatar);
  expect(backup.version).toBe(2);
  await action(request, {
    type: "import",
    state: structuredClone(initialState),
  });
  await page.reload();
  await expect(page.locator(".profile .avatar img")).toHaveCount(0);
  await page
    .locator('input[type="file"][accept="application/json,.json"]')
    .setInputFiles({
      name: "test-v2-backup.json",
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify(backup)),
    });
  await expect(
    page.getByRole("heading", { name: "导入这份学习备份？", exact: true }),
  ).toBeVisible();
  expect(Object.keys((await state(request)).knowledge)).toHaveLength(0);
  await page.getByRole("button", { name: "确认导入", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "导入这份学习备份？", exact: true }),
  ).toHaveCount(0);
  expect(await state(request)).toEqual(saved);
  await expect(page.locator(".profile .avatar img")).toHaveAttribute(
    "src",
    saved.settings.avatar,
  );
  await page.goto("/#knowledge/qa-card");
  await expect(page.getByLabel("知识点学习笔记", { exact: true })).toHaveValue(
    "备份中的个人笔记",
  );
});

test("typing during a delayed note save keeps the newer draft unsaved and recoverable", async ({
  page,
  request,
}) => {
  await action(request, {
    type: "knowledge-import",
    document: knowledgeDocument(),
  });
  await page.goto("/#knowledge/qa-card");
  const note = page.getByLabel("知识点学习笔记", { exact: true });
  await note.fill("第一版");
  let release!: () => void;
  const paused = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/action", async (route) => {
    const payload = route.request().postDataJSON();
    if (payload.type !== "knowledge-note" || payload.text !== "第一版")
      return route.continue();
    const response = await route.fetch(); // Real backend write; only delivery is delayed.
    await paused;
    return route.fulfill({ response });
  });
  await page.getByRole("button", { name: "保存笔记", exact: true }).click();
  await expect
    .poll(async () => (await state(request)).knowledgeNotes["qa-card"])
    .toBe("第一版");
  await note.fill("第二版：保存请求期间继续输入");
  release();
  await expect(
    page.getByRole("button", { name: "保存笔记", exact: true }),
  ).toBeEnabled();
  await page.reload();
  await expect(note).toHaveValue("第二版：保存请求期间继续输入");
  await page.getByRole("button", { name: "保存笔记", exact: true }).click();
  await expect
    .poll(async () => (await state(request)).knowledgeNotes["qa-card"])
    .toBe("第二版：保存请求期间继续输入");
});

test("modal guards retain focus on Ctrl-K and disable fields during a pending save", async ({
  page,
  request,
}) => {
  await openKnowledge(page);
  await page.getByRole("button", { name: "新建知识库", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "新建知识库" });
  const title = dialog.getByLabel("知识库名称", { exact: true });
  const description = dialog.getByLabel("学习目标");
  await title.fill("快捷键与保存保护");
  await page.clock.install();
  await page.keyboard.press("ControlOrMeta+k");
  // Advancing the clock also exercises the search shortcut's deferred focus.
  await page.clock.runFor(150);
  await expect(dialog).toBeVisible();
  await expect(title).toBeFocused();
  await expect(title).toHaveValue("快捷键与保存保护");

  let release!: () => void;
  const paused = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/action", async (route) => {
    if (route.request().postDataJSON().type !== "deck-save")
      return route.continue();
    const response = await route.fetch();
    await paused;
    return route.fulfill({ response });
  });
  try {
    await dialog
      .getByRole("button", { name: "保存知识库", exact: true })
      .click();
    await expect
      .poll(async () => Object.values((await state(request)).decks)[0]?.title)
      .toBe("快捷键与保存保护");
    await expect(title).toBeDisabled();
    await expect(description).toBeDisabled();
    await expect(
      dialog.getByRole("button", { name: "保存知识库", exact: true }),
    ).toBeDisabled();
  } finally {
    release();
  }
  await expect(dialog).toHaveCount(0);
  expect(Object.values((await state(request)).decks)[0].title).toBe(
    "快捷键与保存保护",
  );
  await page.reload();
  await expect(
    page.getByRole("button", { name: "编辑 快捷键与保存保护", exact: true }),
  ).toBeVisible();
});
