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
