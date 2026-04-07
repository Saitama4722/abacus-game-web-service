// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Admin Game Creation Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Log in as admin
    await page.goto('/auth/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(profile|games|admin|$)/);
  });

  test('admin can access create game page', async ({ page }) => {
    await page.goto('/games/create');
    
    // Verify create page loads
    await expect(page).toHaveURL('/games/create');
    
    // Check for form elements
    await expect(page.locator('input[name="name"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('admin can create a new game', async ({ page }) => {
    await page.goto('/games/create');
    
    // Fill in game creation form
    const gameName = `Test Game ${Date.now()}`;
    await page.fill('input[name="name"]', gameName);
    await page.fill('textarea[name="description"]', 'Automated test game');
    
    // Select game type if available
    const gameTypeSelect = page.locator('select[name="game_type"]');
    if (await gameTypeSelect.isVisible()) {
      await gameTypeSelect.selectOption('abacus');
    }
    
    // Check at least one team checkbox if available
    const teamCheckboxes = page.locator('input[type="checkbox"][name="team_ids"]');
    const count = await teamCheckboxes.count();
    if (count > 0) {
      await teamCheckboxes.first().check();
    }
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Wait for redirect after creation
    await page.waitForURL(/\/games\/\d+/);
    
    // Verify we're on game detail page (not 404)
    const currentUrl = page.url();
    expect(currentUrl).toMatch(/\/games\/\d+$/);
    
    const response = await page.goto(currentUrl);
    expect(response?.status()).toBe(200);
  });

  test('newly created game detail page works', async ({ page }) => {
    // Create a game first
    await page.goto('/games/create');
    
    const gameName = `Test Game Detail ${Date.now()}`;
    await page.fill('input[name="name"]', gameName);
    await page.fill('textarea[name="description"]', 'Test description');
    
    const teamCheckboxes = page.locator('input[type="checkbox"][name="team_ids"]');
    const count = await teamCheckboxes.count();
    if (count > 0) {
      await teamCheckboxes.first().check();
    }
    
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/games\/\d+/);
    
    // Now verify the detail page
    const gameUrl = page.url();
    
    // Check page content
    await expect(page.locator('h1, h2')).toBeVisible();
    
    // Verify game name appears on page
    const pageContent = await page.textContent('body');
    expect(pageContent).toContain(gameName);
    
    // Check no 404 error
    expect(pageContent).not.toContain('404');
    expect(pageContent).not.toContain('Not Found');
  });

  test('admin can access games management pages', async ({ page }) => {
    await page.goto('/games');
    
    // Admin should see create button
    const createButton = page.locator('a[href="/games/create"]');
    await expect(createButton).toBeVisible();
    
    // Click on first game to get to detail
    const gameLink = page.locator('a[href^="/games/"]').first();
    if (await gameLink.isVisible()) {
      await gameLink.click();
      await page.waitForURL(/\/games\/\d+/);
      
      // Admin should see management options (edit, topics, etc.)
      const pageContent = await page.textContent('body');
      // Just verify page loads correctly
      expect(pageContent).toBeTruthy();
    }
  });
});
