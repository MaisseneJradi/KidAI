import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./i18n";
import "./index.css";

const useMocks = import.meta.env.VITE_USE_MOCKS !== "false";

async function start() {
  if (useMocks) {
    // Mode démo : MSW simule l'API de la section 14 (pas de backend nécessaire).
    const { worker } = await import("./mocks/browser");
    await worker.start({ onUnhandledRequest: "bypass" });
  } else {
    // Le service worker PWA n'est enregistré qu'avec la vraie API (il entrerait en conflit avec MSW).
    const { registerSW } = await import("virtual:pwa-register");
    registerSW({ immediate: true });
  }

  const queryClient = new QueryClient({
    defaultOptions: { queries: { staleTime: 10_000, retry: 1 } },
  });

  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </StrictMode>,
  );
}

void start();
