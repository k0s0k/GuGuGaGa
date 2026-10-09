import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { readFileSync } from "node:fs";

const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/workspace.json", import.meta.url), "utf8"),
);

async function mockApp(page: Page) {
  const data = structuredClone(fixture.bootstrap);
  data.state.settings.avatar = "";
  let failSave = false;
  let writes = 0;
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/bootstrap") return route.fulfill({ json: data });
    if (path === "/api/action") {
      writes++;
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
    const profile = page.getByRole("button", { name: "编辑用户头像" });
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
    await expect(page.getByRole("heading", { name: "个人头像" })).toBeVisible();
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
