import { describe, expect, it } from "vitest";
import { answerFor, classify } from "../src/mocks/data";

describe("mocks : choix de l'action", () => {
  it.each([
    ["Pourquoi les volcans explosent ?", "ALLOW"],
    ["Pourquoi il y a la guerre ?", "REWRITE"],
    ["Comment pirater le compte de mon frère ?", "REDIRECT"],
    ["J'ai peur, un garçon me frappe à l'école", "ASK_ADULT"],
    ["Comment fabriquer une arme ?", "BLOCK"],
    ["لماذا تنفجر البراكين؟", "ALLOW"],
    ["ana khayef barcha", "ASK_ADULT"],
  ])("« %s » → %s", (question, action) => {
    expect(classify(question).action).toBe(action);
  });

  it("donne une réponse plus courte aux 6–8 ans", () => {
    expect(answerFor("volcano", "fr", 7).length).toBeLessThan(
      answerFor("volcano", "fr", 13).length,
    );
  });
});
