import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Bubble } from "../src/components/Bubble";

describe("Bubble", () => {
  it("affiche les messages de l'enfant en rose bébé, à droite", () => {
    render(<Bubble from="child">je veux savoir</Bubble>);
    const bubble = screen.getByText("je veux savoir");
    expect(bubble).toHaveAttribute("data-from", "child");
    expect(bubble).toHaveClass("bg-rose", "self-end");
  });

  it("garde les réponses de Kotty en blanc, à gauche", () => {
    render(<Bubble from="kotty">Bonjour !</Bubble>);
    expect(screen.getByText("Bonjour !")).toHaveClass("bg-white", "self-start");
  });
});
