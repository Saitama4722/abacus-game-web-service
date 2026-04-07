// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Games Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Log in as user
    await page.goto('/auth/login');
    await page.fill('input[name="username"]', 'user');
    await page.fill('input[name="password"]', 'user');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(profile|games|$)/);
  });

  test('games list page loads and shows games', async ({ page }) => {
    await page.goto('/games');
    
    // Verify games list page
    await expect(page).toHaveURL('/games');
    await expect(page.locator('h1')).toContainText(/Игры/);
    
    // Check for game cards or table (demo games should exist)
    const gamesContent = page.locator('body');
    await expect(gamesContent).toContainText(/Демо-игра|Абакус|игр/i);
  });

  test('can open a game detail page', async ({ page }) => {
    await page.goto('/games');
    
    // Find first game link (should be demo game)
    const gameLink = page.locator('a[href^="/games/"]').first();
    await expect(gameLink).toBeVisible();
    
    // Click to open game detail
    await gameLink.click();
    
    // Verify we're on a game detail page (not 404)
    await page.waitForURL(/\/games\/\d+/);
    const response = await page.goto(page.url());
    expect(response?.status()).toBe(200);
    
    // Page should have game content
    await expect(page.locator('h1, h2')).toBeVisible();
  });

  test('can access game results page', async ({ page }) => {
    await page.goto('/games');
    
    // Get first game ID from a link
    const gameLink = page.locator('a[href^="/games/"]').first();
    const href = await gameLink.getAttribute('href');
    const gameId = href?.match(/\/games\/(\d+)/)?.[1];
    
    if (gameId) {
      // Navigate to results page
      await page.goto(`/games/${gameId}/results`);
      
      // Verify results page loads (not 404)
      const response = await page.goto(`/games/${gameId}/results`);
      expect(response?.status()).toBe(200);
      
      // Should have results content
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('no 404 on main game navigation', async ({ page }) => {
    await page.goto('/games');
    
    // Click through to a game detail
    const gameLink = page.locator('a[href^="/games/"]').first();
    await gameLink.click();
    await page.waitForURL(/\/games\/\d+/);
    
    // Verify not 404
    const pageContent = await page.textContent('body');
    expect(pageContent).not.toContain('404');
    expect(pageContent).not.toContain('Not Found');
  });
});
