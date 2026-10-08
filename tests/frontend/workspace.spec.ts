import { test, expect } from "@playwright/test";
import type { Page, Locator } from "@playwright/test";
import { readFileSync } from "node:fs";
const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/workspace.json", import.meta.url), "utf8"),
);

// The API is mocked per test, so keyboard and Markdown tests never touch a
// real user's progress, notes, or saved solutions.
test.beforeEach(async ({ page }) => {
  const data = structuredClone(fixture.bootstrap);
  const state = data.state as any;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/bootstrap") return route.fulfill({ json: data });
    if (path === "/api/problems/1")
      return route.fulfill({ json: fixture.problem });
    if (path === "/api/action") {
      const input = route.request().postDataJSON();
      const key = `${input.problemId}:${input.language}:${input.mode}`;
      if (input.type === "draft") state.drafts[key] = input.code;
      if (input.type === "note") state.notes[input.problemId] = input.text;
      if (input.type === "solution")
        state.solutions[key] = {
          ...input.solution,
          updatedAt: new Date().toISOString(),
        };
      if (input.type === "solution-reset") delete state.solutions[key];
      return route.fulfill({ json: state });
    }
    return route.fulfill({
      status: 404,
      json: { error: "Unexpected test request" },
    });
  });
  await page.goto("/#problem/1");
  await expect(page.locator(".code-editor .cm-content")).toBeVisible();
});

async function replaceCode(page: Page, editor: Locator, value: string) {
  await editor.click();
  await page.keyboard.press("ControlOrMeta+a");
  await page.keyboard.insertText(value);
}
async function editorText(editor: Locator) {
  return editor.evaluate((element) =>
    Array.from(
      element.querySelectorAll(".cm-line"),
      (line) => line.textContent,
    ).join("\n"),
  );
}

for (const language of ["python", "cpp"] as const) {
  test(`${language}: Enter indents four spaces, Tab indents, Shift-Tab outdents`, async ({
    page,
  }) => {
    await page.getByLabel("编程语言").selectOption(language);
    const editor = page.locator(".code-editor .cm-content");
    const opening = language === "python" ? "def solve():" : "int main() {";
    await replaceCode(page, editor, opening);
    await page.keyboard.press("Enter");
    await expect.poll(() => editorText(editor)).toBe(opening + "\n    ");
    await page.keyboard.press("Tab");
    await expect.poll(() => editorText(editor)).toBe(opening + "\n        ");
    await page.keyboard.press("Shift+Tab");
    await expect.poll(() => editorText(editor)).toBe(opening + "\n    ");
  });

  test(`${language}: Tab accepts variable completion without changing indentation`, async ({
    page,
  }) => {
    await page.getByLabel("编程语言").selectOption(language);
    const editor = page.locator(".code-editor .cm-content");
    const declaration =
      language === "python" ? "total_count = 1" : "int total_count = 1;";
    await replaceCode(page, editor, declaration + "\ntotal_c");
    await page.keyboard.press("Control+Space");
    await expect(page.locator(".cm-tooltip-autocomplete")).toBeVisible();
    await page.keyboard.press("Tab");
    await expect
      .poll(() => editorText(editor))
      .toBe(declaration + "\ntotal_count");
  });
}

test("Enter always makes a newline when a completion menu is open", async ({
  page,
}) => {
  const editor = page.locator(".code-editor .cm-content");
  await replaceCode(page, editor, "total_count = 1\ntotal_c");
  await page.keyboard.press("Control+Space");
  await expect(page.locator(".cm-tooltip-autocomplete")).toBeVisible();
  await page.keyboard.press("Enter");
  await expect
    .poll(() => editorText(editor))
    .toBe("total_count = 1\ntotal_c\n");
});

test("personal solutions preserve all sections across language changes and reloads", async ({
  page,
}) => {
  await page.getByRole("button", { name: "题解", exact: true }).click();
  await page.getByRole("button", { name: "创建我的题解", exact: true }).click();
  await replaceCode(
    page,
    page.locator(".solution-code .cm-content"),
    "# my concise solution\nanswer = 42",
  );
  await page.getByRole("button", { name: "注释版", exact: true }).click();
  await replaceCode(
    page,
    page.locator(".solution-code .cm-content"),
    "# my annotated solution\nanswer = 42 # meaning",
  );
  await page.getByRole("button", { name: "完整解析", exact: true }).click();
  await page
    .getByLabel("我的完整解析 Markdown")
    .fill("## 我的理解\n\n保持哈希表不变量。");
  await page.getByLabel("编程语言").selectOption("cpp");
  await page.getByLabel("编程语言").selectOption("python");
  await expect
    .poll(() => editorText(page.locator(".solution-code .cm-content")))
    .toBe("# my concise solution\nanswer = 42");
  await page.getByLabel("答题模式").selectOption("acm");
  await page.getByRole("button", { name: "创建我的题解", exact: true }).click();
  await replaceCode(
    page,
    page.locator(".solution-code .cm-content"),
    "print('my ACM solution')",
  );
  await page.getByLabel("答题模式").selectOption("leetcode");
  await expect
    .poll(() => editorText(page.locator(".solution-code .cm-content")))
    .toBe("# my concise solution\nanswer = 42");
  await page.reload();
  await page.getByRole("button", { name: "题解", exact: true }).click();
  await expect
    .poll(() => editorText(page.locator(".solution-code .cm-content")))
    .toBe("# my concise solution\nanswer = 42");
  await page.getByRole("button", { name: "保存题解", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "我的题解 · 已保存", exact: true }),
  ).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "题解", exact: true }).click();
  await expect
    .poll(() => editorText(page.locator(".solution-code .cm-content")))
    .toBe("# my concise solution\nanswer = 42");
  await page.getByRole("button", { name: "注释版", exact: true }).click();
  await expect
    .poll(() => editorText(page.locator(".solution-code .cm-content")))
    .toBe("# my annotated solution\nanswer = 42 # meaning");
  await page.getByRole("button", { name: "完整解析", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "我的理解", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "内置题解", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "解题思路", exact: true }),
  ).toBeVisible();
  await page.getByLabel("答题模式").selectOption("acm");
  await expect
    .poll(() => editorText(page.locator(".solution-code .cm-content")))
    .toBe("print('my ACM solution')");
});

test("a failed save keeps the custom solution draft recoverable", async ({
  page,
}) => {
  await page.route("**/api/action", async (route) => {
    if (route.request().postDataJSON().type === "solution")
      return route.fulfill({
        status: 503,
        json: { error: "Test server temporarily unavailable" },
      });
    return route.fallback();
  });
  await page.getByRole("button", { name: "题解", exact: true }).click();
  await page.getByRole("button", { name: "创建我的题解", exact: true }).click();
  await replaceCode(
    page,
    page.locator(".solution-code .cm-content"),
    "# retain this answer after a failed save",
  );
  await page.getByRole("button", { name: "保存题解", exact: true }).click();
  await expect(
    page.getByText("保存失败，题解草稿已保留，请重试。", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "题解", exact: true }).click();
  await expect
    .poll(() => editorText(page.locator(".solution-code .cm-content")))
    .toBe("# retain this answer after a failed save");
});

test("discard and restore require confirmation and keep built-in answers intact", async ({
  page,
}) => {
  await page.getByRole("button", { name: "题解", exact: true }).click();
  const original = await editorText(page.locator(".solution-code .cm-content"));
  await page.getByRole("button", { name: "创建我的题解", exact: true }).click();
  await replaceCode(
    page,
    page.locator(".solution-code .cm-content"),
    "# saved version",
  );
  await page.getByRole("button", { name: "保存题解", exact: true }).click();
  await page.getByRole("button", { name: "编辑我的题解", exact: true }).click();
  await replaceCode(
    page,
    page.locator(".solution-code .cm-content"),
    "# unsaved change",
  );
  await page.getByRole("button", { name: "取消编辑", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "放弃题解草稿" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "放弃草稿", exact: true }).click();
  await expect
    .poll(() => editorText(page.locator(".solution-code .cm-content")))
    .toBe("# saved version");
  await page.getByRole("button", { name: "恢复内置题解", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "恢复内置题解" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "继续保留", exact: true }).click();
  await expect
    .poll(() => editorText(page.locator(".solution-code .cm-content")))
    .toBe("# saved version");
  await page.getByRole("button", { name: "恢复内置题解", exact: true }).click();
  await page.getByRole("button", { name: "确认恢复", exact: true }).click();
  await expect
    .poll(() => editorText(page.locator(".solution-code .cm-content")))
    .toBe(original);
});

test("Markdown notes render tables and code safely without fetching images", async ({
  page,
}) => {
  const outgoingImages: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("tracker.invalid"))
      outgoingImages.push(request.url());
  });
  await page.getByRole("button", { name: "笔记", exact: true }).click();
  await page
    .getByLabel("我的题目笔记")
    .fill(
      "## 复习重点\n\n- 主动回忆\n\n| 操作 | 作用 |\n| --- | --- |\n| Tab | 补全 |\n\n```python\nprint('hello')\n```\n\n[参考](https://example.com)\n\n[危险](javascript:alert(1))\n\n<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n\n![示意](https://tracker.invalid/pixel.png)",
    );
  const preview = page.getByLabel("笔记预览");
  await expect(
    preview.getByRole("heading", { name: "复习重点" }),
  ).toBeVisible();
  await expect(preview.locator("table")).toBeVisible();
  await expect(preview.locator("pre code")).toHaveText("print('hello')\n");
  await expect(preview.getByRole("link", { name: "参考" })).toHaveAttribute(
    "rel",
    "noopener noreferrer",
  );
  await expect(preview.locator('a[href^="javascript:"]')).toHaveCount(0);
  await expect(preview.locator("img, script")).toHaveCount(0);
  expect(outgoingImages).toEqual([]);
  await page.getByRole("button", { name: "预览", exact: true }).click();
  await expect(page.getByLabel("我的题目笔记")).toHaveCount(0);
  await page.getByRole("button", { name: "编辑", exact: true }).click();
  await expect(page.getByLabel("我的题目笔记")).toHaveValue(/## 复习重点/);
});
