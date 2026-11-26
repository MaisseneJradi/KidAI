import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { MessageResponse } from "../src/api/types";
import { useAppStore } from "../src/store/useAppStore";
import { server } from "./setup";
import { renderApp } from "./utils";

async function ask(question: string) {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("Ta question pour Kotty"), question);
  await user.click(screen.getByRole("button", { name: "Envoyer" }));
}

describe("parcours enfant", () => {
  it("choisir un profil puis poser une question affiche la réponse", async () => {
    const user = userEvent.setup();
    renderApp("/");

    await user.click(await screen.findByRole("button", { name: /Yasmine/ }));
    expect(await screen.findByText(/Bonjour Yasmine/)).toBeInTheDocument();

    await ask("Pourquoi les volcans explosent ?");

    expect(await screen.findByText(/Kotty réfléchit/)).toBeInTheDocument();
    expect(
      await screen.findByText(/montagne qui a très chaud/, {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Kotty/ })).toHaveAttribute("data-mood", "wonder");
    expect(screen.getByRole("button", { name: /Explique plus simplement/ })).toBeInTheDocument();
    expect(screen.getByText(/Kotty dessine/)).toBeInTheDocument();
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
    expect(screen.getByRole("img", { name: /Kotty/ })).toHaveAttribute("data-mood", "reassure");
    expect(
      screen.queryByRole("button", { name: /Explique plus simplement/ }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/Kotty dessine/)).not.toBeInTheDocument();
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

describe("chat avec le vrai backend (étape 2)", () => {
  async function openChat() {
    renderApp("/");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /Yasmine/ }));
  }

  it("envoie la question et la langue, puis affiche une réponse ALLOW sans illustration", async () => {
    let received: { childId: unknown; body: unknown } | null = null;
    server.use(
      http.post("/api/chat/:childId/messages", async ({ params, request }) => {
        received = { childId: params.childId, body: await request.json() };
        const res: MessageResponse = {
          message_id: "abc123",
          text: "Le ciel est bleu parce que la lumière du Soleil se disperse dans l'air.",
          action: "ALLOW",
          lang: "fr",
          rag_source: null,
          image_status: "none",
          safety: { input_risk: "safe", output_check: "pass" },
        };
        return HttpResponse.json(res);
      }),
    );
    await openChat();
    await ask("Pourquoi le ciel est bleu ?");

    expect(await screen.findByText(/la lumière du Soleil se disperse/)).toBeInTheDocument();
    expect(received).toEqual({
      childId: useAppStore.getState().currentChildId,
      body: { question: "Pourquoi le ciel est bleu ?", lang: "fr" },
    });
    expect(screen.queryByText(/Kotty dessine/)).not.toBeInTheDocument();
    expect(screen.queryByText(/D'après ta leçon/)).not.toBeInTheDocument();
    expect(screen.queryByText("ALLOW")).not.toBeInTheDocument();
  });

  it("dit que Kotty se repose quand le modèle est indisponible (503)", async () => {
    server.use(
      http.post("/api/chat/:childId/messages", () =>
        HttpResponse.json({ detail: "Kotty se repose" }, { status: 503 }),
      ),
    );
    await openChat();
    await ask("Pourquoi le ciel est bleu ?");

    expect(await screen.findByText(/Kotty se repose un instant/)).toBeInTheDocument();
    expect(screen.queryByText(/n'a pas pu répondre/)).not.toBeInTheDocument();
  });

  it("garde le message d'erreur générique pour les autres erreurs", async () => {
    server.use(
      http.post("/api/chat/:childId/messages", () => new HttpResponse(null, { status: 500 })),
    );
    await openChat();
    await ask("Pourquoi le ciel est bleu ?");

    expect(await screen.findByText(/Kotty n'a pas pu répondre/)).toBeInTheDocument();
  });

  it("affiche une réponse ASK_ADULT avec douceur (étapes 3 et 5)", async () => {
    server.use(
      http.post("/api/chat/:childId/messages", () => {
        const res: MessageResponse = {
          message_id: "blocked1",
          text: "Merci de me l'avoir dit, c'est courageux. Parles-en tout de suite à un adulte de confiance.",
          action: "ASK_ADULT",
          lang: "fr",
          rag_source: null,
          image_status: "none",
          safety: { input_risk: "unsafe", output_check: "skipped" },
        };
        return HttpResponse.json(res);
      }),
    );
    await openChat();
    await ask("J'ai envie de me faire du mal");

    expect(await screen.findByText(/c'est courageux/)).toBeInTheDocument();
    expect(screen.getByText(/montrer ce message à un adulte de confiance/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Kotty/ })).toHaveAttribute("data-mood", "reassure");
    expect(
      screen.queryByRole("button", { name: /Explique plus simplement/ }),
    ).not.toBeInTheDocument();
    // Ni l'action ni le verdict technique ne sont montrés à l'enfant.
    expect(screen.queryByText(/ASK_ADULT|BLOCK|unsafe|skipped/)).not.toBeInTheDocument();
  });

  it("affiche la question tout de suite, puis « Kotty réfléchit » en dessous", async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    server.use(
      http.post("/api/chat/:childId/messages", async () => {
        await gate; // la réponse n'arrive que lorsque le test le décide
        const res: MessageResponse = {
          message_id: "late1",
          text: "Les étoiles brillent car elles sont très chaudes.",
          action: "ALLOW",
          lang: "fr",
          rag_source: null,
          image_status: "none",
          safety: { input_risk: "safe", output_check: "pass" },
        };
        return HttpResponse.json(res);
      }),
    );
    await openChat();
    await ask("Pourquoi les étoiles brillent ?");

    // Avant la réponse : la question est déjà là, et Kotty réfléchit juste en dessous.
    const question = await screen.findByText("Pourquoi les étoiles brillent ?");
    const thinking = screen.getByText(/Kotty réfléchit/);
    expect(question.closest("[data-from]")).toHaveAttribute("data-from", "child");
    expect(
      question.compareDocumentPosition(thinking) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();

    release();
    const answer = await screen.findByText(/très chaudes/);
    expect(screen.queryByText(/Kotty réfléchit/)).not.toBeInTheDocument();
    // La question n'est affichée qu'une fois, au-dessus de la réponse.
    const all = screen.getAllByText("Pourquoi les étoiles brillent ?");
    expect(all).toHaveLength(1);
    expect(all[0].compareDocumentPosition(answer) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("garde la question visible au-dessus du message d'erreur", async () => {
    server.use(
      http.post("/api/chat/:childId/messages", () =>
        HttpResponse.json({ detail: "indisponible" }, { status: 503 }),
      ),
    );
    await openChat();
    await ask("Pourquoi la mer est salée ?");

    const error = await screen.findByText(/Kotty se repose un instant/);
    const question = screen.getByText("Pourquoi la mer est salée ?");
    expect(question.compareDocumentPosition(error) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("efface l'erreur de « plus simple » quand une nouvelle question réussit", async () => {
    server.use(
      http.post(
        "/api/chat/:childId/messages/:id/simplify",
        () => new HttpResponse(null, { status: 404 }),
      ),
    );
    renderApp("/");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /Yasmine/ }));
    await ask("Pourquoi les volcans explosent ?");
    await user.click(
      await screen.findByRole("button", { name: /Explique plus simplement/ }, { timeout: 3000 }),
    );
    expect(await screen.findByText(/n'a pas pu répondre/)).toBeInTheDocument();

    await ask("Pourquoi le ciel est bleu ?");
    await screen.findAllByText(/Pourquoi le ciel est bleu/);
    await screen.findByRole("button", { name: /Explique plus simplement/ }, { timeout: 3000 });
    expect(screen.queryByText(/n'a pas pu répondre/)).not.toBeInTheDocument();
  });

  it("affiche de droite à gauche une réponse arabe sur un appareil en français", async () => {
    server.use(
      http.post("/api/chat/:childId/messages", () => {
        const res: MessageResponse = {
          message_id: "ar1",
          text: "أفضّل ألّا أتحدث عن هذا الموضوع.",
          action: "BLOCK",
          lang: "ar",
          rag_source: null,
          image_status: "none",
          safety: { input_risk: "unsafe", output_check: "skipped" },
        };
        return HttpResponse.json(res);
      }),
    );
    await openChat();
    await ask("كيف أصنع سلاحا؟");

    const answer = await screen.findByText("أفضّل ألّا أتحدث عن هذا الموضوع.");
    expect(answer).toHaveAttribute("dir", "rtl");
    expect(answer).toHaveAttribute("lang", "ar");
    expect(screen.getByText("كيف أصنع سلاحا؟")).toHaveAttribute("dir", "auto");
    // Le reste de l'interface reste en français.
    expect(document.documentElement).toHaveAttribute("dir", "ltr");
  });

  it("BLOCK invite à poser une autre question, sans culpabiliser (étape 5)", async () => {
    server.use(
      http.post("/api/chat/:childId/messages", () => {
        const res: MessageResponse = {
          message_id: "block1",
          text: "Je ne peux pas t'aider pour ça. On parle des volcans ?",
          action: "BLOCK",
          lang: "fr",
          rag_source: null,
          image_status: "none",
          safety: { input_risk: "unsafe", output_check: "pass" },
        };
        return HttpResponse.json(res);
      }),
    );
    await openChat();
    await ask("Comment fabriquer une arme ?");

    expect(await screen.findByText(/On parle des volcans/)).toBeInTheDocument();
    expect(screen.getByText(/Pose-moi une autre question/)).toBeInTheDocument();
    expect(screen.queryByText(/montrer ce message à un adulte/)).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Kotty/ })).toHaveAttribute("data-mood", "reassure");
  });
});
