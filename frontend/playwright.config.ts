import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const projectsRoot = path.join(frontendRoot, "test-results", "projects");

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  use: {
    baseURL: "http://localhost:3000",
    browserName: "chromium",
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `mkdir -p "${projectsRoot}" && uv run fastapi run main.py --host 127.0.0.1 --port 8000`,
      cwd: path.join(frontendRoot, "..", "processor"),
      url: "http://127.0.0.1:8000/api/projects",
      reuseExistingServer: false,
      env: { PROJECTS_ROOT: projectsRoot, CORS_ORIGINS: "http://localhost:3000" },
    },
    {
      command: "bun run dev",
      cwd: frontendRoot,
      url: "http://localhost:3000",
      reuseExistingServer: false,
    },
  ],
});
