import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";
import { applyLanguage } from "../src/i18n";
import { handlers, resetMockDb } from "../src/mocks/handlers";
import { useAppStore } from "../src/store/useAppStore";

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => {
  resetMockDb();
  localStorage.clear();
  useAppStore.setState({
    token: "test-token",
    currentChildId: null,
    lang: "fr",
    sounds: false,
    theme: "auto",
    parentUnlocked: false,
  });
  applyLanguage("fr");
});
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
