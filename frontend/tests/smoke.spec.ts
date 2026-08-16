import { test, expect } from "@playwright/test";
import { cp, rm } from "node:fs/promises";

const fixtureRoot = "tests/fixtures/projects";
const projectsRoot = "test-results/projects";

test.beforeEach(async () => {
  await rm(projectsRoot, { recursive: true, force: true });
  await cp(fixtureRoot, projectsRoot, { recursive: true });
});

test("loads the app and adds a crop operation to the fixture", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto("/");

  await expect(page).toHaveTitle("Document Cropper");
  await expect(page.getByText("DOCUMENTLAB", { exact: true })).toBeVisible();
  await expect(page.getByText("Projects", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Pipeline", exact: true })).toBeVisible();
  await expect(page.getByRole("treeitem", { name: "scan-01" })).toBeVisible();

  const addOperation = page.getByRole("button", { name: "Add operation" });
  await expect(addOperation).toBeVisible();
  await expect(addOperation).toBeEnabled();
  await addOperation.click();

  const cropOption = page.getByRole("button", { name: "Crop", exact: true });
  await expect(cropOption).toBeVisible();
  await cropOption.click();

  await expect(page.locator(".operation").filter({ hasText: "Crop" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Crop parameters", exact: true })).toBeVisible();
  expect(pageErrors).toEqual([]);
});

test("imports an image without crashing when the create response has no views", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto("/");

  await page.locator('input[type="file"]').setInputFiles("tests/fixtures/projects/scan-01/image.png");

  await expect(page.getByRole("treeitem", { name: "image" })).toBeVisible();
  expect(pageErrors).toEqual([]);
});

test("keeps the parameters expand control visible after folding", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Add operation" }).click();
  await page.getByRole("button", { name: "Crop", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Crop parameters", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Collapse parameters" }).click();
  const expandParameters = page.getByRole("button", { name: "Expand parameters" });
  await expect(expandParameters).toBeVisible();

  await expandParameters.click();
  await expect(page.getByRole("button", { name: "Collapse parameters" })).toBeVisible();
});

test("resizes parameters continuously without automatic folding", async ({ page }) => {
  await page.goto("/");
  const splitter = page.locator(".resize-handle.vertical");
  const box = await splitter.boundingBox();
  if (!box) throw new Error("Parameter splitter is unavailable");

  await page.mouse.move(box.x + 1, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + 1, box.y + 1000);
  await page.mouse.up();
  await expect(page.getByRole("button", { name: "Expand parameters" })).toBeVisible();
  await expect(page.locator(".center > .center-pane").last()).toHaveJSProperty("offsetHeight", 0);
  await page.getByRole("button", { name: "Expand parameters" }).click();
  const parameterHeight = await page.locator(".center > .center-pane").last().evaluate((pane) => pane.clientHeight);
  const workspaceHeight = await page.locator(".center").evaluate((workspace) => workspace.clientHeight);
  expect(Math.abs(parameterHeight - (workspaceHeight - 4) * 0.32)).toBeLessThanOrEqual(1);
});

test("side splitter controls fold and restore their panes", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Collapse project sidebar" }).click();
  await expect(page.getByRole("button", { name: "Expand project sidebar" })).toBeVisible();
  await page.getByRole("button", { name: "Expand project sidebar" }).click();
  await expect(page.getByRole("button", { name: "Collapse project sidebar" })).toBeVisible();

  await page.getByRole("button", { name: "Collapse pipeline sidebar" }).click();
  await expect(page.getByRole("button", { name: "Expand pipeline sidebar" })).toBeVisible();
  await page.getByRole("button", { name: "Expand pipeline sidebar" }).click();
  await expect(page.getByRole("button", { name: "Collapse pipeline sidebar" })).toBeVisible();
});

test("side splitters resize continuously to zero", async ({ page }) => {
  await page.goto("/");

  const leftSplitter = page.locator(".resize-handle.horizontal").first();
  const leftBox = await leftSplitter.boundingBox();
  if (!leftBox) throw new Error("Left splitter is unavailable");
  await page.mouse.move(leftBox.x + leftBox.width / 2, leftBox.y + 100);
  await page.mouse.down();
  await page.mouse.move(leftBox.x - 1000, leftBox.y + 100);
  await page.mouse.up();
  await expect(page.locator("aside.left")).toHaveJSProperty("offsetWidth", 0);
  await expect(page.getByRole("button", { name: "Expand project sidebar" })).toBeVisible();
  await page.getByRole("button", { name: "Expand project sidebar" }).click();
  await expect(page.locator("aside.left")).toHaveJSProperty("offsetWidth", 250);

  const rightSplitter = page.locator(".resize-handle.horizontal").last();
  const rightBox = await rightSplitter.boundingBox();
  if (!rightBox) throw new Error("Right splitter is unavailable");
  await page.mouse.move(rightBox.x + rightBox.width / 2, rightBox.y + 100);
  await page.mouse.down();
  await page.mouse.move(rightBox.x + 1000, rightBox.y + 100);
  await page.mouse.up();
  await expect(page.locator("aside.right")).toHaveJSProperty("offsetWidth", 0);
  await expect(page.getByRole("button", { name: "Expand pipeline sidebar" })).toBeVisible();
  await page.getByRole("button", { name: "Expand pipeline sidebar" }).click();
  await expect(page.locator("aside.right")).toHaveJSProperty("offsetWidth", 340);
});

test("renames a project and updates the tree without reloading", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("treeitem", { name: "scan-01" })).toBeVisible();
  await page.getByRole("button", { name: "Rename project scan-01" }).click();
  await expect(page.getByRole("dialog")).toContainText("Rename project");
  await page.getByLabel("Project name").fill("Receipts");
  await page.getByRole("button", { name: "Rename", exact: true }).click();
  await expect(page.getByRole("treeitem", { name: "Receipts" })).toBeVisible();
  await expect(page.getByRole("treeitem", { name: "scan-01" })).not.toBeVisible();
});
