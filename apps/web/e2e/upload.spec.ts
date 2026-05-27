import { test, expect } from "@playwright/test";

test.describe("Routing smoke tests", () => {
  test("upload page renders", async ({ page }) => {
    await page.goto("/upload");
    await expect(page).toHaveURL(/upload/);
  });

  test("files page renders", async ({ page }) => {
    await page.goto("/files");
    await expect(page).toHaveURL(/files/);
  });

  test("dashboard renders", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
  });

  test("memos page renders", async ({ page }) => {
    await page.goto("/memos");
    await expect(page).toHaveURL(/memos/);
  });

  test("record page renders", async ({ page }) => {
    await page.goto("/record");
    await expect(page).toHaveURL(/record/);
  });

  test("summary page renders", async ({ page }) => {
    await page.goto("/summary");
    await expect(page).toHaveURL(/summary/);
  });
});
