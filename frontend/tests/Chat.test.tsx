import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderApp } from "./utils";

async function ask(question: string) {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("Ta question pour Chaty"), question);
  await user.click(screen.getByRole("button", { name: "Envoyer" }));
}

describe("parcours enfant", () => {
  it("choisir un profil puis poser une question affiche la réponse", async () => {
    const user = userEvent.setup();
    renderApp("/");

    await user.click(await screen.findByRole("button", { name: /Yasmine/ }));
    expect(await screen.findByText(/Bonjour Yasmine/)).toBeInTheDocument();

    await ask("Pourquoi les volcans explosent ?");

    expect(await screen.findByText(/Chaty réfléchit/)).toBeInTheDocument();
    expect(
      await screen.findByText(/montagne qui a très chaud/, {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Chaty/ })).toHaveAttribute("data-mood", "wonder");
    expect(screen.getByRole("button", { name: /Explique plus simplement/ })).toBeInTheDocument();
    expect(screen.getByText(/Chaty dessine/)).toBeInTheDocument();
    // L'action technique n'est jamais affichée à l'enfant.
    expect(screen.queryByText("ALLOW")).not.toBeInTheDocument();
  });

  it("répond avec douceur et rassure quand il faut parler à un adulte", async () => {
    renderApp("/");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /Yasmine/ }));

    await ask("J'ai peur, un garçon me frappe");

    const reply = await screen.findByText(
      /adulte de confiance : ils sont là/,
      {},
      { timeout: 3000 },
    );
    expect(reply).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Chaty/ })).toHaveAttribute("data-mood", "reassure");
    expect(
      screen.queryByRole("button", { name: /Explique plus simplement/ }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Chaty dessine/)).not.toBeInTheDocument();
  });

  it("« Explique plus simplement » renvoie une version plus courte", async () => {
    renderApp("/");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /Lina/ }));
    await ask("Pourquoi les volcans explosent ?");

    await user.click(
      await screen.findByRole("button", { name: /Explique plus simplement/ }, { timeout: 3000 }),
    );

    const simpler = await screen.findByText(/^En plus simple/, {}, { timeout: 3000 });
    expect(simpler).toBeInTheDocument();
    expect(within(simpler.closest("div")!).queryByText(/soda/)).not.toBeInTheDocument();
  });
});
