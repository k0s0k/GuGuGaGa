import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/workspace.json", import.meta.url), "utf8"),
);

async function mockApp(page: Page) {
  const data = structuredClone(fixture.bootstrap);
  data.state.settings.avatar = "";
  data.state.settings.workspaceName = "我的工作空间";
  let failSave = false;
  let writes = 0;
  let holdSave: Promise<void> | undefined;
  const payloads: unknown[] = [];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/bootstrap") return route.fulfill({ json: data });
    if (path === "/api/action") {
      writes++;
      payloads.push(route.request().postDataJSON());
      if (holdSave) await holdSave;
      if (failSave)
        return route.fulfill({
          status: 500,
          json: { error: "测试保存失败，请重试" },
        });
      const input = route.request().postDataJSON();
      if (input.type === "settings")
        Object.assign(data.state.settings, input.settings);
      return route.fulfill({ json: data.state });
    }
    return route.fulfill({
      status: 404,
      json: { error: "Unexpected test request" },
    });
  });
  return {
    data,
    fail: (value: boolean) => {
      failSave = value;
    },
    writes: () => writes,
    payloads,
    hold: (paused: Promise<void>) => {
      holdSave = paused;
    },
  };
}

async function imageFile(page: Page) {
  const data = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 400;
    const context = canvas.getContext("2d")!;
    context.fillStyle = "#654392";
    context.fillRect(0, 0, 800, 400);
    context.fillStyle = "#a9ff99";
    context.fillRect(300, 80, 200, 240);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  return {
    name: "my-avatar.png",
    mimeType: "image/png",
    buffer: Buffer.from(data, "base64"),
  };
}

for (const viewport of [
  { width: 1366, height: 768 },
  { width: 1280, height: 600 },
  { width: 1093, height: 614 },
  { width: 980, height: 660 },
  { width: 390, height: 600 },
]) {
  test(`workspace profile stays clickable without clipping at ${viewport.width}x${viewport.height}`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await mockApp(page);
    await page.goto("/#today");
    if (viewport.width < 760)
      await page.getByRole("button", { name: "打开侧栏" }).click();
    const profile = page.getByRole("button", { name: "编辑个人资料" });
    await expect(profile).toBeInViewport({ ratio: 1 });
    const profileBox = await profile.boundingBox();
    expect(profileBox!.y + profileBox!.height).toBeLessThanOrEqual(
      viewport.height,
    );
    await expect(
      page.locator(".sidebar-bottom").getByRole("button", { name: "偏好设置" }),
    ).toBeInViewport({ ratio: 1 });
    const clip = await page.locator(".sidebar-scroll").evaluate((node) => {
      const scroller = node as HTMLElement;
      scroller.scrollTop = scroller.scrollHeight;
      return {
        y: scroller.getBoundingClientRect().bottom,
        top: document.querySelector(".sidebar-bottom")!.getBoundingClientRect()
          .top,
      };
    });
    expect(clip.y).toBeLessThanOrEqual(clip.top + 1);
    await page.locator(".sidebar-scroll").evaluate((node) => {
      node.scrollTop = 0;
    });
    await page.screenshot({
      path: `.local/gugugaga-sidebar-${viewport.width}x${viewport.height}.png`,
    });
    await profile.click();
    await expect(page.getByRole("heading", { name: "个人资料" })).toBeVisible();
    if (viewport.width < 760)
      await expect(page.locator(".sidebar")).not.toHaveClass(/open/);
    await expect(page.locator(".brand")).toContainText("GuGuGaGa");
  });
}

test("avatar is cropped locally, explicitly saved, restored after reload and removable", async ({
  page,
}) => {
  const mock = await mockApp(page);
  await page.goto("/#settings");
  await page.getByLabel("上传用户头像").setInputFiles(await imageFile(page));
  const preview = page.locator(".avatar-settings-preview img");
  await expect(preview).toBeVisible();
  expect(
    await preview.evaluate((image: HTMLImageElement) => [
      image.naturalWidth,
      image.naturalHeight,
    ]),
  ).toEqual([256, 256]);
  expect(mock.writes()).toBe(0);
  await expect(page.locator(".profile .avatar img")).toHaveCount(0);
  await page.getByRole("button", { name: "保存头像", exact: true }).click();
  await expect(page.locator(".profile .avatar img")).toBeVisible();
  await page.screenshot({ path: ".local/gugugaga-avatar-settings.png" });
  const saved = mock.data.state.settings.avatar;
  expect(saved).toMatch(/^data:image\/png;base64,/);
  expect(saved.length).toBeLessThan(350000);
  await page.reload();
  await expect(page.locator(".profile .avatar img")).toHaveAttribute(
    "src",
    saved,
  );
  await expect(preview).toHaveAttribute("src", saved);
  await page.getByRole("button", { name: "移除头像", exact: true }).click();
  await expect(preview).toHaveCount(0);
  await expect(page.locator(".profile .avatar img")).toBeVisible();
  await page.getByRole("button", { name: "保存头像", exact: true }).click();
  await expect(page.locator(".profile .avatar img")).toHaveCount(0);
  await page.reload();
  await expect(preview).toHaveCount(0);
  expect(mock.data.state.settings.avatar).toBe("");
});

test("invalid files do not save; failed saves keep avatar preview for retry", async ({
  page,
}) => {
  const mock = await mockApp(page);
  await page.goto("/#settings");
  const input = page.getByLabel("上传用户头像");
  await input.setInputFiles({
    name: "unsafe.svg",
    mimeType: "image/svg+xml",
    buffer: Buffer.from("<svg/>"),
  });
  await expect(page.getByRole("alert")).toContainText("PNG、JPEG 或 WebP");
  await input.setInputFiles({
    name: "huge.png",
    mimeType: "image/png",
    buffer: Buffer.alloc(5 * 1024 * 1024 + 1),
  });
  await expect(page.getByRole("alert")).toContainText("不能超过 5 MB");
  await input.setInputFiles({
    name: "broken.png",
    mimeType: "image/png",
    buffer: Buffer.from("not a real image"),
  });
  await expect(page.getByRole("alert")).toContainText("无法读取这张图片");
  expect(mock.writes()).toBe(0);
  await input.setInputFiles(await imageFile(page));
  await expect(page.locator(".avatar-settings-preview img")).toBeVisible();
  mock.fail(true);
  await page.getByRole("button", { name: "保存头像", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("测试保存失败");
  await expect(page.locator(".avatar-settings-preview img")).toBeVisible();
  await expect(page.locator(".profile .avatar img")).toHaveCount(0);
  mock.fail(false);
  await page.getByRole("button", { name: "保存头像", exact: true }).click();
  await expect(page.locator(".profile .avatar img")).toBeVisible();
});

test("workspace name explicitly saves with Enter, trims and persists beside the avatar", async ({
  page,
}) => {
  const mock = await mockApp(page);
  const avatar =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC";
  mock.data.state.settings.avatar = avatar;
  await page.goto("/#today");
  await page.getByRole("button", { name: "编辑个人资料" }).click();
  const input = page.getByLabel("工作空间名称", { exact: true });
  await expect(input).toHaveValue("我的工作空间");
  await input.fill("  咕咕的学习空间 🐧  ");
  await expect(page.locator(".profile-details strong")).toHaveText(
    "我的工作空间",
  );
  expect(mock.writes()).toBe(0);
  await input.press("Enter");
  await expect(page.locator(".profile-details strong")).toHaveText(
    "咕咕的学习空间 🐧",
  );
  await expect(page.locator(".breadcrumb .workspace-name")).toHaveText(
    "咕咕的学习空间 🐧",
  );
  await expect(input).toHaveValue("咕咕的学习空间 🐧");
  expect(mock.payloads).toEqual([
    { type: "settings", settings: { workspaceName: "咕咕的学习空间 🐧" } },
  ]);
  expect(mock.data.state.settings.avatar).toBe(avatar);
  await page.reload();
  await expect(input).toHaveValue("咕咕的学习空间 🐧");
  await expect(page.locator(".profile .avatar img")).toHaveAttribute(
    "src",
    avatar,
  );
  await expect(page.locator(".breadcrumb .workspace-name")).toHaveAttribute(
    "title",
    "咕咕的学习空间 🐧",
  );
  await input.fill("不会保存的修改");
  await page.getByRole("button", { name: "撤销名称修改" }).click();
  await expect(input).toHaveValue("咕咕的学习空间 🐧");
  expect(mock.writes()).toBe(1);
});

test("workspace name validates empty and long values and retains failed saves for retry", async ({
  page,
}) => {
  const mock = await mockApp(page);
  await page.goto("/#settings");
  const input = page.getByLabel("工作空间名称", { exact: true });
  const save = page.getByRole("button", { name: "保存名称", exact: true });
  await input.fill("  ");
  await expect(save).toBeDisabled();
  await expect(page.locator("#workspace-name-hint")).toHaveText(
    "请输入 1–40 个字符",
  );
  await input.press("Enter");
  await input.fill("🐧".repeat(41));
  await expect(save).toBeDisabled();
  expect(mock.writes()).toBe(0);
  await input.fill("企鹅的知识小屋");
  mock.fail(true);
  await save.click();
  await expect(page.getByRole("alert")).toContainText("测试保存失败");
  await expect(input).toHaveValue("企鹅的知识小屋");
  await expect(page.locator(".profile-details strong")).toHaveText(
    "我的工作空间",
  );
  mock.fail(false);
  let release!: () => void;
  mock.hold(
    new Promise<void>((resolve) => {
      release = resolve;
    }),
  );
  try {
    await save.click();
    await expect(input).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "正在保存名称…" }),
    ).toBeDisabled();
  } finally {
    release();
  }
  await expect(page.locator(".profile-details strong")).toHaveText(
    "企鹅的知识小屋",
  );
  await expect(input).toBeEnabled();
});

test("40-codepoint names truncate without clipping the profile or mobile header; markup stays text", async ({
  page,
}) => {
  await mockApp(page);
  await page.goto("/#settings");
  const input = page.getByLabel("工作空间名称", { exact: true });
  const longName = "🐧".repeat(40);
  await input.fill(longName);
  await page.getByRole("button", { name: "保存名称", exact: true }).click();
  await expect(page.locator(".breadcrumb .workspace-name")).toHaveAttribute(
    "title",
    longName,
  );
  for (const width of [1366, 390]) {
    await page.setViewportSize({ width, height: 768 });
    if (width < 760)
      await page.getByRole("button", { name: "打开侧栏" }).click();
    await expect(
      page.getByRole("button", { name: "编辑个人资料" }),
    ).toBeInViewport({ ratio: 1 });
    const metrics = await page.evaluate(() => {
      const name = document.querySelector(
        ".profile-details strong",
      ) as HTMLElement;
      const crumb = document.querySelector(
        ".breadcrumb .workspace-name",
      ) as HTMLElement;
      const right = document
        .querySelector(".topbar-right")!
        .getBoundingClientRect();
      return {
        profileTruncated: name.scrollWidth > name.clientWidth,
        crumbTruncated: crumb.scrollWidth > crumb.clientWidth,
        headerRight: right.right,
        contentFits: document.documentElement.scrollWidth <= window.innerWidth,
      };
    });
    expect(metrics.profileTruncated).toBe(true);
    expect(metrics.crumbTruncated).toBe(true);
    expect(metrics.headerRight).toBeLessThanOrEqual(width);
    expect(metrics.contentFits).toBe(true);
    if (width < 760)
      await page.getByRole("button", { name: "编辑个人资料" }).click();
  }
  const markup = "<img src=x onerror=alert(1)>";
  await input.fill(markup);
  await input.press("Enter");
  await expect(page.locator(".breadcrumb .workspace-name")).toHaveText(markup);
  await expect(page.locator(".breadcrumb .workspace-name img")).toHaveCount(0);
  await page.reload();
  await expect(page.locator(".profile-details strong")).toHaveText(markup);
});
