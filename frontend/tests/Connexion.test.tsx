import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { useAppStore } from "../src/store/useAppStore";
import { server } from "./setup";
import { renderApp } from "./utils";

describe("connexion parent", () => {
  it("affiche la connexion tant que le parent n'est pas connecté", async () => {
    useAppStore.setState({ token: null });
    renderApp("/");
    expect(screen.getByRole("heading", { name: "Bienvenue sur KidAI" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Qui es-tu ?" })).not.toBeInTheDocument();
  });

  it("crée un compte puis affiche les profils", async () => {
    useAppStore.setState({ token: null });
    const user = userEvent.setup();
    renderApp("/");

    await user.click(screen.getByRole("button", { name: /Créer un compte/ }));
    await user.type(screen.getByLabelText("Email"), "parent@example.com");
    await user.type(screen.getByLabelText(/Mot de passe/), "motdepasse123");
    await user.type(screen.getByLabelText(/Code PIN/), "1234");
    await user.click(screen.getByRole("button", { name: "Créer un compte" }));

    expect(await screen.findByRole("heading", { name: "Qui es-tu ?" })).toBeInTheDocument();
    expect(useAppStore.getState().token).toBe("mock-token");
  });

  it("affiche une erreur si les identifiants sont faux", async () => {
    useAppStore.setState({ token: null });
    server.use(http.post("/api/auth/parent/login", () => HttpResponse.json({}, { status: 401 })));
    const user = userEvent.setup();
    renderApp("/");

    await user.type(screen.getByLabelText("Email"), "parent@example.com");
    await user.type(screen.getByLabelText("Mot de passe"), "mauvais");
    await user.click(screen.getByRole("button", { name: "Se connecter" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("incorrect");
    expect(useAppStore.getState().token).toBeNull();
  });

  it("revient à la connexion si le serveur refuse le jeton", async () => {
    server.use(http.get("/api/children", () => HttpResponse.json({}, { status: 401 })));
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Bienvenue sur KidAI" })).toBeInTheDocument();
  });
});
