import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  use: { baseURL: "http://localhost:3000", browserName: "chromium", headless: true },
  webServer: { command: "bun run dev", cwd: ".", url: "http://localhost:3000", reuseExistingServer: false },
});
