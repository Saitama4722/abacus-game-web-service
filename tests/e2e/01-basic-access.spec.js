// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Basic Site Access', () => {
  test('home page loads successfully', async ({ page }) => {
    await page.goto('/');
    
    // Check page loads without error
    await expect(page).toHaveTitle(/Абакус/);
    
    // Check for main heading
    await expect(page.locator('h1')).toBeVisible();
  });

  test('login page is accessible', async ({ page }) => {
    await page.goto('/');
    
    // Find and click login link
    await page.click('a[href="/auth/login"]');
    
    // Verify we're on login page
    await expect(page).toHaveURL('/auth/login');
    await expect(page.locator('h1, h2')).toContainText(/Вход/);
    
    // Check form elements exist
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('games list page is accessible', async ({ page }) => {
    await page.goto('/games');
    
    // Check page loads
    await expect(page).toHaveURL('/games');
    await expect(page.locator('h1')).toContainText(/Игры/);
  });
});
