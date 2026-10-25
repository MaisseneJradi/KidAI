import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { bandForAge } from "../src/lib/ageBand";
import { useAppStore } from "../src/store/useAppStore";
import { renderApp } from "./utils";

describe("langue et thèmes", () => {
  it("passe toute la page en RTL en arabe", async () => {
    useAppStore.setState({ lang: "ar" });
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "من أنت؟" })).toBeInTheDocument();
    expect(document.documentElement.dir).toBe("rtl");
    expect(document.documentElement.lang).toBe("ar");
  });

  it("reste en LTR en français", async () => {
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Qui es-tu ?" })).toBeInTheDocument();
    expect(document.documentElement.dir).toBe("ltr");
  });

  it.each([
    [6, "small"],
    [8, "small"],
    [9, "middle"],
    [11, "middle"],
    [12, "teen"],
    [14, "teen"],
  ] as const)("%i ans → thème %s", (age, band) => {
    expect(bandForAge(age)).toBe(band);
  });
});
