import { test, expect } from "@playwright/test";

const image = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=", "base64");

test("selects project root in MUI tree", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.route("http://localhost:8000/api/projects", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify(["scan-01", "scan-02"]) }));
  await page.route("http://localhost:8000/api/projects/*/image", (route) => route.fulfill({ contentType: "image/png", body: image }));
  await page.goto("/");
  expect(errors).toEqual([]);
  const root = page.getByRole("treeitem", { name: "scan-01" });
  await expect(root).toHaveAttribute("aria-checked", "true");
  await expect(page.getByRole("heading", { name: "scan-01" })).toBeVisible();
});
