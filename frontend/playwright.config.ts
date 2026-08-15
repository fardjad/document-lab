import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";
import path from "node:path";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const projectsRoot = path.join(frontendRoot, "test-results", "projects");
const backendPort = Number(process.env.E2E_BACKEND_PORT || 8000);
const frontendPort = Number(process.env.E2E_FRONTEND_PORT || 3000);
const frontendOrigin = `http://localhost:${frontendPort}`;

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  use: {
    baseURL: frontendOrigin,
    browserName: "chromium",
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `mkdir -p "${projectsRoot}" && uv run uvicorn main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: path.join(frontendRoot, "..", "processor"),
      url: `http://127.0.0.1:${backendPort}/api/projects`,
      reuseExistingServer: false,
      env: { PROJECTS_ROOT: projectsRoot, CORS_ORIGINS: frontendOrigin },
    },
    {
      command: `PORT=${frontendPort} BACKEND_PORT=${backendPort} bun run dev`,
      cwd: frontendRoot,
      url: frontendOrigin,
      reuseExistingServer: false,
    },
  ],
});
