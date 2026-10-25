import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  // Mode démo : n'importe quels identifiants sont acceptés.
  await page.getByLabel("Email").fill("parent@example.com");
  await page.getByLabel("Mot de passe").fill("motdepasse123");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.getByRole("heading", { name: "Qui es-tu ?" })).toBeVisible();
});

test("FR : choisir un profil → poser une question → voir la réponse et l'illustration", async ({
  page,
}) => {
  await page.getByRole("button", { name: /Yasmine/ }).click();
  await expect(page.getByText(/Bonjour Yasmine/)).toBeVisible();

  await page.getByLabel("Ta question pour Chaty").fill("Pourquoi les volcans explosent ?");
  await page.getByRole("button", { name: "Envoyer" }).click();

  await expect(page.getByText(/montagne qui a très chaud/)).toBeVisible();
  await expect(page.getByRole("img", { name: /Illustration/ })).toBeVisible({ timeout: 10_000 });
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");

  // Pas de défilement horizontal, même à 360 px.
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test("AR : la page passe en RTL et Chaty répond en arabe", async ({ page }) => {
  await page.getByRole("button", { name: /Adam/ }).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

  await page.getByLabel("سؤالك لشاتي").fill("لماذا تنفجر البراكين؟");
  await page.getByRole("button", { name: "إرسال" }).click();

  await expect(page.getByText(/البركان مثل جبل ساخن/)).toBeVisible();
});

test("ASK_ADULT : réponse rassurante et alerte dans l'espace parent", async ({ page }) => {
  await page.getByRole("button", { name: /Yasmine/ }).click();
  await page.getByLabel("Ta question pour Chaty").fill("J'ai peur, un garçon me frappe");
  await page.getByRole("button", { name: "Envoyer" }).click();
  await expect(page.getByText(/adulte de confiance/).first()).toBeVisible();

  await page.goto("/parent");
  for (const digit of "1234") await page.getByRole("button", { name: `Chiffre ${digit}` }).click();
  await expect(page.getByText(/Yasmine a demandé/)).toBeVisible();
});
