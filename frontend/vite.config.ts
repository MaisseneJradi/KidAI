import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig } from "vitest/config";

// Node ≥ 25 expose un localStorage natif qui masque celui de jsdom dans les tests. L'option qui le
// désactive n'existe pas sur les Node plus anciens (20 LTS) : on ne la passe que si elle est connue.
const webstorageFlag = process.allowedNodeEnvironmentFlags.has("--experimental-webstorage")
  ? ["--no-experimental-webstorage"]
  : [];

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      injectRegister: null, // enregistré à la main dans main.tsx
      registerType: "autoUpdate",
      includeAssets: ["icon.svg"],
      manifest: {
        name: "KidAI — Chaty",
        short_name: "KidAI",
        description: "Pose tes questions à Chaty, ton assistant curieux et bienveillant.",
        lang: "fr",
        start_url: "/",
        display: "standalone",
        theme_color: "#4FA3F7",
        background_color: "#FFF8EC",
        icons: [
          { src: "icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
          { src: "icon-maskable.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
        globIgnores: ["mockServiceWorker.js"],
        navigateFallbackDenylist: [/^\/api/, /^\/health/],
      },
    }),
  ],
  server: {
    port: 5173,
    // Le navigateur ne parle qu'au backend FastAPI, via ce proxy.
    proxy: {
      "/health": process.env.API_PROXY_TARGET ?? "http://localhost:8000",
      "/api": process.env.API_PROXY_TARGET ?? "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
    poolOptions: { forks: { execArgv: webstorageFlag } },
  },
});
