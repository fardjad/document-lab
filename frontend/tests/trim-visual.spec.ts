import { test, expect } from "@playwright/test";
import { cp, rm } from "node:fs/promises";

const fixtureRoot = "tests/fixtures/projects";
const projectsRoot = "test-results/projects";

test.beforeEach(async () => {
  await rm(projectsRoot, { recursive: true, force: true });
  await cp(fixtureRoot, projectsRoot, { recursive: true });
});

test("trim controls overlay the viewer center while actions stay in the header", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.goto("/");
  await expect(page.getByRole("treeitem", { name: "scan-01" })).toBeVisible();
  await page.getByText("Receipt", { exact: true }).click();
  await expect(page.locator(".image-window.crop-window")).toBeVisible();
  await page.getByRole("button", { name: "Trim region" }).click();

  const overlay = page.locator(".trim-overlay");
  const header = page.locator("header");
  const viewer = page.locator(".viewer");
  const toolbar = page.locator(".viewer-toolbar");
  await expect(overlay).toBeVisible();

  const viewerBox = await viewer.boundingBox();
  const overlayBox = await overlay.boundingBox();
  const headerBox = await header.boundingBox();
  const toolbarBox = await toolbar.boundingBox();
  if (!viewerBox || !overlayBox || !headerBox || !toolbarBox) throw new Error("missing boxes");

  const inside = (box: { x: number; y: number; width: number; height: number }, outer: { x: number; y: number; width: number; height: number }) =>
    box.x >= outer.x - 1 && box.y >= outer.y - 1 &&
    box.x + box.width <= outer.x + outer.width + 1 &&
    box.y + box.height <= outer.y + outer.height + 1;
  expect(inside(overlayBox, viewerBox), `overlay outside viewer: ${JSON.stringify({ viewerBox, overlayBox })}`).toBeTruthy();

  // Overlay must be centered in the viewer.
  const centerX = (b: { x: number; width: number }) => b.x + b.width / 2;
  const centerY = (b: { y: number; height: number }) => b.y + b.height / 2;
  expect(Math.abs(centerX(overlayBox) - centerX(viewerBox))).toBeLessThan(4);
  expect(Math.abs(centerY(overlayBox) - centerY(viewerBox))).toBeLessThan(4);

  // Overlay must not cover the bottom zoom toolbar.
  const overlaps = (a: { x: number; y: number; width: number; height: number }, b: { x: number; y: number; width: number; height: number }) =>
    a.x < b.x + b.width - 1 && b.x < a.x + a.width - 1 && a.y < b.y + b.height - 1 && b.y < a.y + a.height - 1;
  expect(overlaps(overlayBox, toolbarBox), "overlay covers viewer toolbar").toBeFalsy();

  // Directional controls keep their canvas orientation.
  const topBox = await overlay.locator(".trim-top").boundingBox();
  const bottomBox = await overlay.locator(".trim-bottom").boundingBox();
  const leftBox = await overlay.locator(".trim-left").boundingBox();
  const rightBox = await overlay.locator(".trim-right").boundingBox();
  if (!topBox || !bottomBox || !leftBox || !rightBox) throw new Error("missing trim boxes");
  expect(topBox.y).toBeLessThan(leftBox.y);
  expect(bottomBox.y).toBeGreaterThan(leftBox.y);
  expect(leftBox.x).toBeLessThan(topBox.x);
  expect(rightBox.x).toBeGreaterThan(topBox.x);

  // Auto, Cancel, and Confirm stay in the header.
  for (const name of ["Automatically detect trim", "Cancel trim", "Confirm trim"]) {
    const box = await page.getByRole("button", { name }).boundingBox();
    if (!box) throw new Error(`missing ${name}`);
    expect(inside(box, headerBox), `${name} outside header`).toBeTruthy();
  }

  expect(errors).toEqual([]);
});
