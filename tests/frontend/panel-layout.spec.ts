import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/workspace.json", import.meta.url), "utf8"),
);

async function panelApp(page: Page) {
  const data = structuredClone(fixture.bootstrap);
  const state = data.state;
  Object.assign(state.settings, {
    theme: "dark",
    avatar: "",
    workspaceName: "面板测试空间",
    includeHot100: true,
  });
  state.decks = { demo: { id: "demo", title: "学习布局", description: "" } };
  state.knowledge = {
    card: {
      id: "card",
      deckId: "demo",
      title: "布局测试知识卡",
      kind: "qa",
      prompt: "先尝试回忆。",
      answer: "这是答案。",
      tags: [],
      source: "",
      archived: false,
    },
  };
  const payloads: Record<string, unknown>[] = [];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/bootstrap") return route.fulfill({ json: data });
    if (path === "/api/action") {
      const payload = route.request().postDataJSON();
      payloads.push(payload);
      if (payload.type === "knowledge-note")
        state.knowledgeNotes[payload.itemId] = payload.text;
      return route.fulfill({ json: state });
    }
    return route.fulfill({
      status: 404,
      json: { error: "Unexpected panel test request" },
    });
  });
  return { state, payloads };
}

async function layoutMenu(page: Page) {
  await page.locator(".panel-layout-controls > summary").click();
  await expect(page.locator(".panel-layout-menu")).toBeVisible();
}

test("hiding and restoring knowledge notes preserves an unsaved draft and later saves it", async ({
  page,
}) => {
  const app = await panelApp(page);
  await page.goto("/#knowledge/card");
  const note = page.getByRole("textbox", { name: "知识点学习笔记" });
  const draft = "## 尚未保存的笔记\n\n保留我的输入和 **Markdown**。";
  await note.fill(draft);
  await layoutMenu(page);
  await page.getByRole("checkbox", { name: "学习笔记", exact: true }).uncheck();
  await expect(page.locator('[data-panel-id="notes"]')).toBeHidden();
  expect(app.payloads).toEqual([]);
  await page.getByRole("checkbox", { name: "学习笔记", exact: true }).check();
  await page.keyboard.press("Escape");
  await expect(note).toHaveValue(draft);
  await page.getByRole("button", { name: "保存笔记", exact: true }).click();
  await expect(page.locator(".knowledge-note-footer")).toContainText(
    "已保存到知识库",
  );
  expect(app.state.knowledgeNotes.card).toBe(draft);
  await page.reload();
  await expect(note).toHaveValue(draft);
});

test("panel dimensions commit on Enter and blur, survive reload, and reset restores hidden panels", async ({
  page,
}) => {
  await panelApp(page);
  await page.goto("/#today");
  await layoutMenu(page);
  await page
    .getByRole("spinbutton", { name: "学习旅程宽度", exact: true })
    .fill("520");
  await page
    .getByRole("spinbutton", { name: "学习旅程宽度", exact: true })
    .press("Enter");
  await page
    .getByRole("spinbutton", { name: "学习旅程高度", exact: true })
    .fill("420");
  await page
    .getByRole("spinbutton", { name: "学习旅程高度", exact: true })
    .press("Tab");
  await page
    .getByRole("checkbox", { name: "探索知识库", exact: true })
    .uncheck();
  await page.keyboard.press("Escape");
  const journey = page.locator('[data-panel-id="journey"]');
  await expect(journey).toHaveCSS("width", "520px");
  await expect(journey).toHaveCSS("height", "420px");
  await expect(page.locator('[data-panel-id="explore"]')).toBeHidden();
  await page.reload();
  await expect(journey).toHaveCSS("width", "520px");
  await expect(journey).toHaveCSS("height", "420px");
  await layoutMenu(page);
  await expect(
    page.getByRole("spinbutton", { name: "学习旅程宽度", exact: true }),
  ).toHaveValue("520");
  await expect(
    page.getByRole("spinbutton", { name: "学习旅程高度", exact: true }),
  ).toHaveValue("420");
  await page.getByRole("button", { name: "恢复本页布局", exact: true }).click();
  await page.keyboard.press("Escape");
  await expect(page.locator('[data-panel-id="explore"]')).toBeVisible();
  await expect(journey).toHaveAttribute("data-panel-sized", "false");
  await expect(journey).toHaveAttribute("data-panel-height", "false");
  expect(
    await page.evaluate(() =>
      JSON.parse(localStorage.getItem("gugugaga-panels-today") || "{}"),
    ),
  ).toEqual({});
});

test("native bottom-right panel resizing persists dimensions after reload", async ({
  page,
}) => {
  await panelApp(page);
  await page.goto("/#today");
  await layoutMenu(page);
  await page
    .getByRole("spinbutton", { name: "学习旅程宽度", exact: true })
    .fill("520");
  await page
    .getByRole("spinbutton", { name: "学习旅程宽度", exact: true })
    .press("Enter");
  await page
    .getByRole("spinbutton", { name: "学习旅程高度", exact: true })
    .fill("400");
  await page
    .getByRole("spinbutton", { name: "学习旅程高度", exact: true })
    .press("Enter");
  await page.keyboard.press("Escape");
  const journey = page.locator('[data-panel-id="journey"]');
  await journey.scrollIntoViewIfNeeded();
  const box = (await journey.boundingBox())!;
  await page.mouse.move(box.x + box.width - 4, box.y + box.height - 4);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width - 74, box.y + box.height - 54, {
    steps: 10,
  });
  await page.mouse.up();
  await expect
    .poll(async () => (await journey.boundingBox())!.width)
    .toBeLessThan(500);
  const changed = await journey.boundingBox();
  expect(changed!.height).toBeLessThan(380);
  const persisted = await page.evaluate(
    () =>
      JSON.parse(localStorage.getItem("gugugaga-panels-today") || "{}").journey,
  );
  expect(persisted.width).toBeCloseTo(changed!.width, 0);
  expect(persisted.height).toBeCloseTo(changed!.height, 0);
  await page.reload();
  await expect(journey).toHaveCSS("width", `${persisted.width}px`);
  await expect(journey).toHaveCSS("height", `${persisted.height}px`);
});

test("sidebar drag and keyboard resizing persist and its reset restores default width", async ({
  page,
}) => {
  await panelApp(page);
  await page.goto("/#today");
  const handle = page.getByRole("separator", { name: "调整侧栏宽度" });
  await handle.focus();
  await handle.press("End");
  await expect(page.locator(".sidebar")).toHaveCSS("width", "340px");
  await handle.press("ArrowLeft");
  await expect(handle).toHaveAttribute("aria-valuenow", "330");
  const box = (await handle.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, 100);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 - 50, 100, { steps: 5 });
  await page.mouse.up();
  await expect(handle).toHaveAttribute("aria-valuenow", "280");
  await page.reload();
  await expect(page.locator(".sidebar")).toHaveCSS("width", "280px");
  await handle.dblclick({ position: { x: 3, y: 100 } });
  await expect(page.locator(".sidebar")).toHaveCSS("width", "226px");
});

for (const mobileWidth of [760, 390]) {
  test(`hidden sidebar recovers at ${mobileWidth}px while panel controls stay accessible`, async ({
    page,
  }) => {
    await panelApp(page);
    await page.setViewportSize({ width: 1280, height: 600 });
    await page.goto("/#today");
    await page.getByRole("button", { name: "隐藏侧栏", exact: true }).click();
    await expect(page.locator(".sidebar")).toBeHidden();
    await page.reload();
    await expect(
      page.getByRole("button", { name: "显示侧栏", exact: true }),
    ).toBeVisible();
    await layoutMenu(page);
    await page
      .getByRole("checkbox", { name: "学习旅程", exact: true })
      .uncheck();
    await page
      .getByRole("button", { name: "恢复本页布局", exact: true })
      .click();
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-panel-id="journey"]')).toBeVisible();
    await page.setViewportSize({ width: mobileWidth, height: 600 });
    await page.getByRole("button", { name: "打开侧栏", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "编辑个人资料", exact: true }),
    ).toBeInViewport({ ratio: 1 });
    await page.locator(".nav-item").filter({ hasText: "学习日历" }).click();
    await expect(page.locator(".sidebar")).not.toHaveClass(/open/);
    await expect(
      page.locator(".panel-layout-controls > summary"),
    ).toBeVisible();
    await layoutMenu(page);
    await expect(
      page.getByRole("button", { name: "恢复本页布局", exact: true }),
    ).toBeInViewport({ ratio: 1 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBeTruthy();
    await page.keyboard.press("Escape");
    await page.setViewportSize({ width: 1280, height: 600 });
    await page.getByRole("button", { name: "显示侧栏", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "编辑个人资料", exact: true }),
    ).toBeInViewport({ ratio: 1 });
  });
}

test("out-of-range panel sizes normalize visibly and empty sizes restore automatic layout", async ({
  page,
}) => {
  await panelApp(page);
  await page.goto("/#today");
  await layoutMenu(page);
  const width = page.getByRole("spinbutton", {
    name: "学习旅程宽度",
    exact: true,
  });
  await width.fill("10");
  await width.press("Enter");
  await expect(width).toHaveValue("180");
  await width.fill("-50");
  await width.press("Tab");
  await expect(width).toHaveValue("180");
  await width.fill("9000");
  await width.press("Enter");
  await expect(width).toHaveValue("2400");
  await width.fill("");
  await width.press("Enter");
  await expect(width).toHaveValue("");
  await expect(page.locator('[data-panel-id="journey"]')).toHaveAttribute(
    "data-panel-sized",
    "false",
  );
  await page.getByRole("button", { name: "恢复本页布局", exact: true }).click();
  await expect(width).toHaveValue("");
});

test("opening hidden personal details reveals the existing panel without clearing its draft or size", async ({
  page,
}) => {
  const app = await panelApp(page);
  await page.goto("/#settings");
  const name = page.getByRole("textbox", { name: "工作空间名称", exact: true });
  await name.fill("尚未保存的工作空间名称");
  await layoutMenu(page);
  await page
    .getByRole("spinbutton", { name: "个人资料宽度", exact: true })
    .fill("660");
  await page
    .getByRole("spinbutton", { name: "个人资料宽度", exact: true })
    .press("Enter");
  await page
    .getByRole("spinbutton", { name: "个人资料高度", exact: true })
    .fill("420");
  await page
    .getByRole("spinbutton", { name: "个人资料高度", exact: true })
    .press("Enter");
  await page.getByRole("checkbox", { name: "个人资料", exact: true }).uncheck();
  await page.keyboard.press("Escape");
  const profile = page.locator('[data-panel-id="profile"]');
  await expect(profile).toBeHidden();
  await page.getByRole("button", { name: "编辑个人资料", exact: true }).click();
  await expect(profile).toBeVisible();
  await expect(page.locator("#profile-heading")).toBeFocused();
  await expect(name).toHaveValue("尚未保存的工作空间名称");
  await expect(profile).toHaveCSS("width", "660px");
  await expect(profile).toHaveCSS("height", "420px");
  expect(app.payloads).toEqual([]);
  await page.reload();
  await expect(profile).toBeVisible();
  await expect(profile).toHaveCSS("width", "660px");
  await expect(profile).toHaveCSS("height", "420px");
});

test("Ctrl+K and sidebar search reveal a hidden knowledge list while preserving its dimensions", async ({
  page,
}) => {
  await panelApp(page);
  await page.goto("/#knowledge");
  const search = page.getByRole("textbox", { name: "搜索知识点", exact: true });
  await search.fill("布局");
  await layoutMenu(page);
  await page
    .getByRole("spinbutton", { name: "知识点列表宽度", exact: true })
    .fill("700");
  await page
    .getByRole("spinbutton", { name: "知识点列表宽度", exact: true })
    .press("Enter");
  await page
    .getByRole("spinbutton", { name: "知识点列表高度", exact: true })
    .fill("300");
  await page
    .getByRole("spinbutton", { name: "知识点列表高度", exact: true })
    .press("Enter");
  await page
    .getByRole("checkbox", { name: "知识点列表", exact: true })
    .uncheck();
  await page.keyboard.press("Escape");
  const list = page.locator('[data-panel-id="knowledge-list"]');
  await expect(list).toBeHidden();
  await page.keyboard.press("ControlOrMeta+k");
  await expect(search).toBeFocused();
  await expect(search).toHaveValue("布局");
  await expect(list).toHaveCSS("width", "700px");
  await expect(list).toHaveCSS("height", "300px");
  await layoutMenu(page);
  await page
    .getByRole("checkbox", { name: "知识点列表", exact: true })
    .uncheck();
  await page.keyboard.press("Escape");
  await page.locator(".nav-item").filter({ hasText: "今日学习" }).click();
  await page.locator(".quick-search").click();
  await expect(search).toBeFocused();
  await expect(list).toHaveCSS("width", "700px");
  await expect(list).toHaveCSS("height", "300px");
  await page.reload();
  await expect(list).toBeVisible();
  await expect(list).toHaveCSS("width", "700px");
  await expect(list).toHaveCSS("height", "300px");
});
