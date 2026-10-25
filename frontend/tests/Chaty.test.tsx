import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Chaty, type ChatyMood } from "../src/components/Chaty";

describe("Chaty", () => {
  it.each<ChatyMood>(["wave", "think", "wonder", "reassure"])(
    "s'affiche dans l'état %s",
    (mood) => {
      render(<Chaty mood={mood} />);
      const img = screen.getByRole("img", { name: /Chaty/ });
      expect(img).toHaveAttribute("data-mood", mood);
    },
  );
});
