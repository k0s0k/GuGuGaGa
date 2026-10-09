import { expect, test } from "@playwright/test";
import type { APIRequestContext, Page } from "@playwright/test";
import { spawn } from "node:child_process";
import type { ChildProcess } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type { AppState, KnowledgeDocument } from "../../src/types";
import { dateShift, dayKey } from "../../src/utils";

// Real production UI + real SQLite, isolated from the user's data and other suites.
const baseURL = "http://127.0.0.1:8898";
const root = fileURLToPath(new URL("../../", import.meta.url));
const screenshots = join(root, ".local", "stones-screenshots");
type StoneState = AppState & {
  stones: {
    balance: number;
    totalEarned: number;
    totalSpent: number;
    startedOn: string;
    makeups: { day: string; spentAt: string; cost: number }[];
    rules: {
      learn: number;
      review: number;
      checkin: number;
      makeup: number;
      makeupWindowDays: number;
    };
  };
};
let backend: ChildProcess | undefined;
let token = "";
let initialState: StoneState;
let problemIds: number[];

test.use({ baseURL });

test.beforeAll(async () => {
  try {
    await fetch(`${baseURL}/api/bootstrap`, {
      signal: AbortSignal.timeout(500),
    });
    throw new Error(
      "Test port 8898 is occupied; refusing to use another process's data.",
    );
  } catch (error) {
    if ((error as Error).message.startsWith("Test port")) throw error;
  }
  const directory = join(
    root,
    ".local",
    `stones-e2e-${process.pid}-${Date.now()}`,
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
      "8898",
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
      throw new Error(`Isolated stone backend exited with ${backend.exitCode}`);
    try {
      const response = await fetch(`${baseURL}/api/bootstrap`, {
        signal: AbortSignal.timeout(1000),
      });
      if (response.ok) {
        const payload = await response.json();
        token = payload.token;
        initialState = payload.state;
        problemIds = payload.problems
          .slice(0, 3)
          .map((problem: { id: number }) => problem.id);
        expect(initialState.stones.balance).toBe(0);
        return;
      }
    } catch {
      /* The isolated server is still starting. */
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error(
    "The isolated stone backend did not start within 20 seconds.",
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
): Promise<StoneState> {
  const response = await request.post(`${baseURL}/api/action`, {
    headers: { "X-CodeRecall-Token": token },
    data: payload,
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}
async function savedState(request: APIRequestContext): Promise<StoneState> {
  const response = await request.get(`${baseURL}/api/state`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}
const card: KnowledgeDocument = {
  format: "coderecall.knowledge",
  version: 1,
  deck: { id: "stone-deck", title: "小石头测试知识库" },
  items: [
    {
      id: "stone-card",
      title: "主动回忆练习",
      kind: "qa",
      prompt: "为什么先回忆再查看答案？",
      answer: "主动提取记忆可以帮助巩固理解。",
    },
  ],
};

test.beforeEach(async ({ request }) => {
  await action(request, {
    type: "import",
    state: structuredClone(initialState),
  });
});

async function seedHistory(
  request: APIRequestContext,
  count = 3,
  theme: "light" | "dark" = "light",
) {
  const old = structuredClone(initialState) as Partial<StoneState>;
  delete old.stones; // Exercise migration of a backup made before stone rewards existed.
  old.settings!.theme = theme;
  const firstDay = dayKey(dateShift(new Date(), -3));
  const targetDay = dayKey(dateShift(new Date(), -2));
  old.events = problemIds.slice(0, count).map((problemId, index) => ({
    eventId: `stone-history-${problemId}`,
    problemId,
    day: index === 0 ? firstDay : targetDay,
    time: `${index === 0 ? firstDay : targetDay}T10:00:00+08:00`,
    kind: "new",
    rating: "good",
    seconds: 90,
  }));
  old.checkins = [firstDay];
  const state = await action(request, { type: "import", state: old });
  return { state, firstDay, targetDay };
}
async function openPastDay(page: Page, targetDay: string) {
  await page.goto("/#calendar");
  if (targetDay.slice(0, 7) !== dayKey().slice(0, 7))
    await page.getByRole("button", { name: "上个月", exact: true }).click();
  await page
    .getByRole("button", {
      name: new RegExp(`^${targetDay}，学习 \\d+ 项，未签到$`),
    })
    .click();
}
const makeupButton = (page: Page) =>
  page.getByRole("button", { name: "补签 · 20 小石头", exact: true });
const makeupDialog = (page: Page) =>
  page.getByRole("dialog", { name: "用小石头补签", exact: true });

for (const kind of ["knowledge", "code"] as const) {
  test(`${kind}: first learning earns stones, repeated same-day feedback does not, and manual check-in earns once`, async ({
    page,
    request,
  }) => {
    if (kind === "knowledge")
      await action(request, { type: "knowledge-import", document: card });
    const route =
      kind === "knowledge"
        ? "/#knowledge/stone-card"
        : `/#problem/${problemIds[0]}`;
    await page.goto(route);
    if (kind === "knowledge")
      await page.getByRole("button", { name: "显示答案", exact: true }).click();
    await page.getByRole("button", { name: /^记住了/ }).click();
    await expect(page.locator(".stone-reward")).toContainText(/\+10\s*小石头/);
    await expect
      .poll(async () => (await savedState(request)).stones.balance)
      .toBe(10);
    expect((await savedState(request)).checkins).toEqual([]);
    await page.reload();
    if (kind === "knowledge")
      await page.getByRole("button", { name: "显示答案", exact: true }).click();
    await page.getByRole("button", { name: /^记住了/ }).click();
    await expect(page.locator(".study-confirmed")).toBeVisible();
    expect((await savedState(request)).stones.balance).toBe(10);
    await page.locator("[data-stone-wallet]").click();
    await expect(page).toHaveURL(/#calendar$/);
    await expect(page.locator(".stone-collection")).toBeVisible();
    await page.getByRole("button", { name: "签到", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "今日已签到", exact: true }),
    ).toBeDisabled();
    await expect
      .poll(async () => (await savedState(request)).stones.balance)
      .toBe(12);
    await page.reload();
    await expect(page.locator("[data-stone-wallet]")).toContainText("12");
    expect((await savedState(request)).stones.totalEarned).toBe(12);
    expect((await savedState(request)).checkins).toEqual([dayKey()]);
  });
}

test("reviewing a previously learned item on a later day earns five stones", async ({
  page,
  request,
}) => {
  const learned = await action(request, {
    type: "rate",
    problemId: problemIds[0],
    rating: "good",
    eventId: "stone-review-history",
  });
  const old = structuredClone(learned) as Partial<StoneState>;
  delete old.stones;
  const yesterday = dayKey(dateShift(new Date(), -1));
  old.events![0].day = yesterday;
  old.events![0].time = `${yesterday}T10:00:00+08:00`;
  const migrated = await action(request, { type: "import", state: old });
  expect(migrated.stones.balance).toBe(10);
  await page.goto(`/#problem/${problemIds[0]}`);
  await page.getByRole("button", { name: /^记住了/ }).click();
  await expect(page.locator(".stone-reward")).toContainText(/\+5\s*小石头/);
  await expect
    .poll(async () => (await savedState(request)).stones.balance)
    .toBe(15);
  expect((await savedState(request)).stones.totalEarned).toBe(15);
});

test("old history earns stones; confirmed makeup spends once and survives a full backup round trip", async ({
  page,
  request,
}) => {
  const { state: seeded, firstDay, targetDay } = await seedHistory(request);
  expect(seeded.stones.balance).toBe(32);
  expect(seeded.stones.startedOn).toBe(firstDay);
  await openPastDay(page, targetDay);
  await expect(page.getByTestId("stone-balance")).toHaveText(/32\s*颗/);
  await expect(page.getByTestId("stone-total")).toHaveText("32");
  await makeupButton(page).click();
  let dialog = makeupDialog(page);
  await expect(dialog).toContainText("20");
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  expect((await savedState(request)).stones.balance).toBe(32);
  await makeupButton(page).click();
  dialog = makeupDialog(page);
  await dialog.getByRole("button", { name: "确认补签", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(page.getByTestId("stone-balance")).toHaveText(/12\s*颗/);
  await expect(page.getByTestId("stone-total")).toHaveText("32");
  await expect(page.getByTestId("stone-spent")).toHaveText("20");
  await expect(
    page.getByRole("button", { name: new RegExp(`^${targetDay}，.*已补签`) }),
  ).toBeVisible();
  const confirmed = await savedState(request);
  expect(confirmed.stones.balance).toBe(12);
  expect(confirmed.stones.totalEarned).toBe(32);
  expect(confirmed.stones.totalSpent).toBe(20);
  expect(confirmed.stones.makeups).toEqual([
    expect.objectContaining({ day: targetDay, cost: 20 }),
  ]);
  expect(confirmed.checkins).toContain(targetDay);
  await page.reload();
  expect((await savedState(request)).stones).toEqual(confirmed.stones);
  await page.goto("/#settings");
  const downloading = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出备份", exact: true }).click();
  const download = await downloading;
  const backup = JSON.parse(readFileSync((await download.path())!, "utf8"));
  expect(backup.stones).toEqual(confirmed.stones);
  await action(request, {
    type: "import",
    state: structuredClone(initialState),
  });
  await page.reload();
  await page
    .locator('input[type="file"][accept="application/json,.json"]')
    .setInputFiles({
      name: "stones-backup.json",
      mimeType: "application/json",
      buffer: Buffer.from(JSON.stringify(backup)),
    });
  await page.getByRole("button", { name: "确认导入", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "导入这份学习备份？", exact: true }),
  ).not.toBeVisible();
  expect((await savedState(request)).stones).toEqual(confirmed.stones);
  await page.goto("/#calendar");
  if (targetDay.slice(0, 7) !== dayKey().slice(0, 7))
    await page.getByRole("button", { name: "上个月", exact: true }).click();
  await expect(
    page.getByRole("button", { name: new RegExp(`^${targetDay}，.*已补签`) }),
  ).toBeVisible();
});

test("insufficient stone balance disables makeup without spending anything", async ({
  page,
  request,
}) => {
  const { state: seeded, targetDay } = await seedHistory(request, 1);
  expect(seeded.stones.balance).toBe(12);
  await openPastDay(page, targetDay);
  await expect(makeupButton(page)).toBeDisabled();
  expect((await savedState(request)).stones.makeups).toEqual([]);
  expect((await savedState(request)).stones.balance).toBe(12);
});

test("failed makeup remains retryable and double clicks cannot charge twice", async ({
  page,
  request,
}) => {
  const { targetDay } = await seedHistory(request);
  let attempts = 0;
  let release!: () => void;
  const paused = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/action", async (route) => {
    if (route.request().postDataJSON().type !== "checkin-makeup")
      return route.continue();
    attempts++;
    if (attempts === 1)
      return route.fulfill({
        status: 500,
        json: { error: "测试补签失败，请重试" },
      });
    const response = await route.fetch(); // Persist for real, but delay confirmation to exercise busy protection.
    await paused;
    await route.fulfill({ response });
  });
  await openPastDay(page, targetDay);
  await makeupButton(page).click();
  const dialog = makeupDialog(page);
  const confirm = dialog.getByRole("button", { name: /确认补签|补签中/ });
  await confirm.click();
  await expect(dialog.getByRole("alert")).toContainText("测试补签失败");
  expect((await savedState(request)).stones.balance).toBe(32);
  try {
    await confirm.evaluate((node: HTMLButtonElement) => {
      node.click();
      node.click();
    });
    await expect(confirm).toBeDisabled();
    await expect
      .poll(async () => (await savedState(request)).stones.balance)
      .toBe(12);
    expect(attempts).toBe(2);
  } finally {
    release();
  }
  await expect(dialog).not.toBeVisible();
  const state = await savedState(request);
  expect(state.stones.totalSpent).toBe(20);
  expect(state.stones.makeups).toHaveLength(1);
});

for (const theme of ["light", "dark"] as const) {
  test(`${theme}: wallet and makeup dialog fit at 390px and retain keyboard dismissal`, async ({
    page,
    request,
  }) => {
    await page.setViewportSize({ width: 390, height: 700 });
    const { targetDay } = await seedHistory(request, 3, theme);
    await page.goto("/#today");
    const wallet = page.locator("[data-stone-wallet]");
    await expect(wallet).toBeInViewport({ ratio: 1 });
    await wallet.click();
    await expect(page).toHaveURL(/#calendar$/);
    await expect(page.locator(".stone-collection")).toBeVisible();
    await page.screenshot({
      path: join(screenshots, `calendar-${theme}-390.png`),
      fullPage: true,
    });
    if (targetDay.slice(0, 7) !== dayKey().slice(0, 7))
      await page.getByRole("button", { name: "上个月", exact: true }).click();
    await page
      .getByRole("button", { name: new RegExp(`^${targetDay}，.*未签到$`) })
      .click();
    await makeupButton(page).click();
    const dialog = makeupDialog(page);
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "取消", exact: true }).focus();
    await page.clock.install();
    await page.keyboard.press("ControlOrMeta+k");
    // Let the app's delayed search-focus shortcut run if the modal guard fails.
    await page.clock.runFor(200);
    await expect(page).toHaveURL(/#calendar$/);
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
    await expect(
      dialog.getByRole("button", { name: "确认补签", exact: true }),
    ).toBeInViewport();
    await page.screenshot({
      path: join(screenshots, `makeup-${theme}-390.png`),
    });
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    expect((await savedState(request)).stones.balance).toBe(32);
  });
}
