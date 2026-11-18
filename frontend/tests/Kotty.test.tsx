import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Kotty, type KottyMood } from "../src/components/Kotty";

describe("Kotty", () => {
  it.each<KottyMood>(["wave", "think", "wonder", "reassure"])(
    "s'affiche dans l'état %s",
    (mood) => {
      render(<Kotty mood={mood} />);
      const img = screen.getByRole("img", { name: /Kotty/ });
      expect(img).toHaveAttribute("data-mood", mood);
    },
  );
});
