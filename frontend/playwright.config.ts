import { defineConfig, devices } from "@playwright/test";

// Serveur dédié aux tests, toujours en mode démo (MSW), sur un port à part pour ne jamais
// réutiliser le serveur de développement (qui peut pointer vers le vrai backend).
const PORT = 5180;

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  use: { baseURL: `http://localhost:${PORT}` },
  projects: [
    // Téléphone (360 px, NF-02) et ordinateur
    {
      name: "telephone",
      use: { ...devices["Pixel 5"], viewport: { width: 360, height: 740 } },
    },
    {
      name: "ordinateur",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
    },
  ],
  webServer: {
    command: `npx vite --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: false,
    // Les variables d'environnement priment sur .env.local.
    env: { VITE_USE_MOCKS: "true" },
  },
});
