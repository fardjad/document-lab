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
