import { test, expect } from "@playwright/test";
import { cp, rm } from "node:fs/promises";

const fixtureRoot = "tests/fixtures/projects";
const projectsRoot = "test-results/projects";

test.beforeEach(async () => {
  await rm(projectsRoot, { recursive: true, force: true });
  await cp(fixtureRoot, projectsRoot, { recursive: true });
});

test("creates a region through the viewer and rotates it via the pipeline contract", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.goto("/");
  await expect(page.getByRole("treeitem", { name: "scan-01" })).toBeVisible();

  await page.getByRole("button", { name: "Create region" }).click();
  const viewport = page.locator("section.viewer");
  const box = await viewport.boundingBox();
  expect(box).not.toBeNull();
  const startX = box!.x + box!.width * 0.3;
  const startY = box!.y + box!.height * 0.3;
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(startX + 120, startY + 90, { steps: 8 });
  await page.mouse.up();
  await page.getByRole("button", { name: "Confirm region" }).click();
  await expect(page.getByRole("treeitem", { name: "Region 2" })).toBeVisible();

  const responsePromise = page.waitForResponse((item) => item.url().includes("/regions/") && item.request().method() === "PUT" && item.status() === 200, { timeout: 5000 });
  await page.getByRole("button", { name: "Rotate region right 90 degrees" }).click();
  const response = await responsePromise.catch(() => null);
  expect(response?.status()).toBe(200);
  await expect(page.getByRole("button", { name: "Rotate region right 90 degrees" })).toBeEnabled();
  expect(errors).toEqual([]);
});
