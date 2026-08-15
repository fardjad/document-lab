import { test, expect } from "@playwright/test";
import { cp, rm } from "node:fs/promises";

const fixtureRoot = "tests/fixtures/projects";
const projectsRoot = "test-results/projects";

test.beforeEach(async () => {
  await rm(projectsRoot, { recursive: true, force: true });
  await cp(fixtureRoot, projectsRoot, { recursive: true });
});

test("loads projects and displays selected view", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.goto("/");
  await expect(page.getByRole("treeitem", { name: "scan-01" })).toBeVisible();
  await expect(page.locator("img.document")).toBeVisible();
  await page.getByText("Receipt", { exact: true }).click();
  await expect(page.locator(".image-window.crop-window")).toBeVisible();
  expect(errors).toEqual([]);
});
