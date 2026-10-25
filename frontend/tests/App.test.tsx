import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("affiche « backend OK » quand /health répond", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
    render(<App />);
    expect(await screen.findByText("backend OK")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/health");
  });

  it("signale un backend indisponible", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    render(<App />);
    expect(await screen.findByText("backend indisponible")).toBeInTheDocument();
  });
});
