import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { useAppStore } from "../src/store/useAppStore";
import { renderApp } from "./utils";

async function typePin(pin: string) {
  const user = userEvent.setup();
  for (const digit of pin) {
    await user.click(await screen.findByRole("button", { name: `Chiffre ${digit}` }));
  }
}

describe("espace parent", () => {
  it("refuse un mauvais PIN sans déconnecter le parent", async () => {
    renderApp("/parent");
    await typePin("0000");
    expect(await screen.findByRole("alert")).toHaveTextContent("Code incorrect");
    expect(useAppStore.getState().token).toBe("test-token");
  });

  it("ajoute un enfant avec date de naissance, sexe, intérêts et besoins", async () => {
    const user = userEvent.setup();
    renderApp("/parent");
    await typePin("1234");

    await user.click(await screen.findByRole("button", { name: /Ajouter un enfant/ }));
    await user.type(screen.getByLabelText("Prénom"), "Sami");
    const year = new Date().getFullYear() - 9;
    await user.type(screen.getByLabelText("Date de naissance"), `${year}-01-15`);
    await user.selectOptions(screen.getByLabelText("Sexe"), "garcon");
    await user.click(screen.getByRole("button", { name: "Espace" }));
    await user.click(screen.getByRole("checkbox", { name: /Dyslexie/ }));
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));

    expect(await screen.findByText(/9 ans · Garçon · 4e année|9 ans · Garçon/)).toBeInTheDocument();
    expect(screen.getAllByText("Sami").length).toBeGreaterThan(0);
  });

  it("affiche les profils et les alertes avec le bon PIN", async () => {
    renderApp("/parent");
    await typePin("1234");
    expect(await screen.findByRole("heading", { name: "Profils des enfants" })).toBeInTheDocument();
    expect(screen.getByText("Aucune alerte.")).toBeInTheDocument();
    expect(screen.getAllByText("Yasmine").length).toBeGreaterThan(0);
  });
});
