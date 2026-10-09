import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/workspace.json", import.meta.url), "utf8"),
);
const layoutKey = "gugugaga-workspace-layout-v1";
const longCode = (language: "python" | "cpp") =>
  Array.from({ length: 240 }, (_, index) =>
    language === "python"
      ? `value_${index + 1} = ${index + 1}`
      : `int value_${index + 1} = ${index + 1};`,
  ).join("\n");

async function mockWorkspace(page: Page, failDrafts = false) {
  const data = structuredClone(fixture.bootstrap);
  data.state.drafts["1:python:leetcode"] = longCode("python");
  data.state.drafts["1:cpp:leetcode"] = longCode("cpp");
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/bootstrap") return route.fulfill({ json: data });
    if (path === "/api/problems/1")
      return route.fulfill({ json: fixture.problem });
    if (path === "/api/action") {
      const input = route.request().postDataJSON();
      if (input.type === "draft") {
        if (failDrafts)
          return route.fulfill({
            status: 500,
            json: { error: "保存暂不可用" },
          });
        data.state.drafts[
          `${input.problemId}:${input.language}:${input.mode}`
        ] = input.code;
      }
      return route.fulfill({ json: data.state });
    }
    return route.fulfill({
      status: 404,
      json: { error: "Unexpected request" },
    });
  });
  await page.goto("/#problem/1");
  await expect(page.locator(".code-editor .cm-scroller")).toBeVisible();
}

for (const language of ["python", "cpp"] as const) {
  test(`${language}: mouse wheel scrolls bounded editor to the last of 240 lines`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await mockWorkspace(page);
    await page.getByLabel("编程语言").selectOption(language);
    const scroll = page.locator(".code-editor .cm-scroller");
    const bounds = await scroll.evaluate((node) => ({
      height: node.clientHeight,
      full: node.scrollHeight,
    }));
    expect(bounds.height).toBeGreaterThan(80);
    expect(bounds.height).toBeLessThan(650);
    expect(bounds.full).toBeGreaterThan(bounds.height * 4);
    await scroll.hover();
    await page.mouse.wheel(0, 620);
    await expect
      .poll(() => scroll.evaluate((node) => node.scrollTop))
      .toBeGreaterThan(150);
    await page.mouse.wheel(0, 30000);
    await expect
      .poll(() =>
        scroll.evaluate(
          (node) => node.scrollHeight - node.clientHeight - node.scrollTop,
        ),
      )
      .toBeLessThan(3);
    await expect(page.locator(".code-editor .cm-content")).toContainText(
      "value_240",
    );
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollTop))
      .toBe(0);
  });
}

test("drag and keyboard resize both panes, persist dimensions, and restore defaults", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockWorkspace(page);
  const columns = page.getByRole("separator", {
    name: "调整题目区与代码区宽度",
  });
  const rows = page.getByRole("separator", { name: "调整代码区与运行区高度" });
  const question = page.locator(".question-pane");
  const before = (await question.boundingBox())!.width;
  const handle = (await columns.boundingBox())!;
  await page.mouse.move(handle.x + handle.width / 2, handle.y + 30);
  await page.mouse.down();
  await page.mouse.move(handle.x + 105, handle.y + 30, { steps: 8 });
  await page.mouse.up();
  expect((await question.boundingBox())!.width).toBeGreaterThan(before + 70);
  const changedWidth = await columns.getAttribute("aria-valuenow");
  await rows.focus();
  const codeBefore = (await page.locator(".code-editor").boundingBox())!.height;
  await page.keyboard.press("ArrowDown");
  await expect(rows).toHaveAttribute("aria-valuenow", "64");
  expect(
    (await page.locator(".code-editor").boundingBox())!.height,
  ).toBeGreaterThan(codeBefore);
  await page.reload();
  await expect(columns).toHaveAttribute("aria-valuenow", changedWidth!);
  await expect(rows).toHaveAttribute("aria-valuenow", "64");
  await columns.focus();
  await page.keyboard.press("Home");
  await expect(columns).toHaveAttribute("aria-valuenow", "30");
  await page.keyboard.press("End");
  await expect(columns).toHaveAttribute("aria-valuenow", "65");
  await page.getByRole("button", { name: "恢复布局", exact: true }).click();
  await expect(columns).toHaveAttribute("aria-valuenow", "44");
  await expect(rows).toHaveAttribute("aria-valuenow", "62");
});

test("hidden panels retain unsaved code, recovery remains reachable, and one main pane stays visible", async ({
  page,
}) => {
  await mockWorkspace(page, true);
  const editor = page.locator(".code-editor .cm-content");
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.insertText("# unsaved panel draft\nanswer = 42");
  const controls = page.getByLabel("工作区布局", { exact: true });
  await controls.getByRole("button", { name: "代码区", exact: true }).click();
  await expect(page.locator(".editor-pane")).toBeHidden();
  await expect(
    controls.getByRole("button", { name: "题目区", exact: true }),
  ).toBeDisabled();
  await controls.getByRole("button", { name: "代码区", exact: true }).click();
  await expect(editor).toContainText("unsaved panel draft");
  await controls.getByRole("button", { name: "运行区", exact: true }).click();
  await expect(page.locator(".console-pane")).toBeHidden();
  await controls.getByRole("button", { name: "学习进度", exact: true }).click();
  await expect(page.locator(".workspace-progress-panel")).toBeHidden();
  await controls.getByRole("button", { name: "题目区", exact: true }).click();
  await expect(page.locator(".question-pane")).toBeHidden();
  await expect(
    controls.getByRole("button", { name: "代码区", exact: true }),
  ).toBeDisabled();
  await page.reload();
  await expect(editor).toContainText("unsaved panel draft");
  await expect(page.locator(".question-pane")).toBeHidden();
  await expect(page.locator(".console-pane")).toBeHidden();
  await controls.getByRole("button", { name: "恢复布局", exact: true }).click();
  await expect(page.locator(".question-pane")).toBeVisible();
  await expect(page.locator(".console-pane")).toBeVisible();
  await expect(editor).toContainText("unsaved panel draft");
});

test("mobile stacks panels without horizontal overflow and code still scrolls independently", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 700 });
  await mockWorkspace(page);
  await expect(
    page.getByRole("separator", { name: "调整题目区与代码区宽度" }),
  ).toBeHidden();
  expect((await page.locator(".editor-pane").boundingBox())!.y).toBeGreaterThan(
    (await page.locator(".question-pane").boundingBox())!.y,
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth - innerWidth,
    ),
  ).toBeLessThanOrEqual(1);
  const scroll = page.locator(".code-editor .cm-scroller");
  await scroll.scrollIntoViewIfNeeded();
  await scroll.hover();
  await page.mouse.wheel(0, 650);
  await expect
    .poll(() => scroll.evaluate((node) => node.scrollTop))
    .toBeGreaterThan(100);
  const controls = page.getByLabel("工作区布局", { exact: true });
  await expect(controls).toBeInViewport();
  await controls.getByRole("button", { name: "题目区", exact: true }).click();
  await expect(page.locator(".question-pane")).toBeHidden();
  await controls.getByRole("button", { name: "恢复布局", exact: true }).click();
  await expect(page.locator(".question-pane")).toBeVisible();
});

test("invalid saved layouts are bounded and cannot hide both main panes", async ({
  page,
}) => {
  await page.addInitScript(
    ({ key }) =>
      localStorage.setItem(
        key,
        JSON.stringify({
          question: false,
          editor: false,
          questionShare: 999,
          codeShare: -100,
          console: "invalid",
        }),
      ),
    { key: layoutKey },
  );
  await mockWorkspace(page);
  await expect(page.locator(".editor-pane")).toBeVisible();
  await expect(page.locator(".console-pane")).toBeVisible();
  await expect(
    page.getByRole("separator", { name: "调整代码区与运行区高度" }),
  ).toHaveAttribute("aria-valuenow", "35");
  await page
    .getByLabel("工作区布局", { exact: true })
    .getByRole("button", { name: "题目区", exact: true })
    .click();
  await expect(
    page.getByRole("separator", { name: "调整题目区与代码区宽度" }),
  ).toHaveAttribute("aria-valuenow", "65");
});

for (const size of [
  { width: 1280, height: 600, sidebar: 226 },
  { width: 1024, height: 700, sidebar: 340 },
  { width: 900, height: 700, sidebar: 340 },
  { width: 760, height: 700, sidebar: 340 },
]) {
  test(`workspace remains usable at ${size.width}x${size.height} with ${size.sidebar}px sidebar`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: size.width, height: size.height });
    await page.addInitScript(
      (width) => localStorage.setItem("gugugaga-sidebar-width", String(width)),
      size.sidebar,
    );
    await mockWorkspace(page);
    const scroll = page.locator(".code-editor .cm-scroller");
    expect(await scroll.evaluate((node) => node.clientHeight)).toBeGreaterThan(
      65,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth - innerWidth,
      ),
    ).toBeLessThanOrEqual(1);
    await scroll.hover();
    await page.mouse.wheel(0, 30000);
    await expect
      .poll(() =>
        scroll.evaluate(
          (node) => node.scrollHeight - node.clientHeight - node.scrollTop,
        ),
      )
      .toBeLessThan(3);
    const run = page.getByRole("button", { name: "运行代码" });
    await run.scrollIntoViewIfNeeded();
    await expect(run).toBeInViewport();
    const runBox = (await run.boundingBox())!;
    expect(
      await run.evaluate((node) => {
        const rect = node.getBoundingClientRect();
        return node.contains(
          document.elementFromPoint(
            rect.x + rect.width / 2,
            rect.y + rect.height / 2,
          ),
        );
      }),
    ).toBe(true);
    expect(runBox.x + runBox.width).toBeLessThanOrEqual(size.width);
    await page.screenshot({
      path: `.local/workspace-layout-${size.width}x${size.height}.png`,
    });
  });
}
