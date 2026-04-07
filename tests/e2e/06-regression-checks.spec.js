// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Broken Link Regression Checks', () => {
  test.beforeEach(async ({ page }) => {
    // Log in as user
    await page.goto('/auth/login');
    await page.fill('input[name="username"]', 'user');
    await page.fill('input[name="password"]', 'user');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(profile|games|$)/);
  });

  test('key pages return 200 not 404', async ({ page }) => {
    const pagesToCheck = [
      '/games',
      '/auth/profile',
    ];
    
    for (const url of pagesToCheck) {
      const response = await page.goto(url);
      expect(response?.status()).toBe(200);
      
      // Verify no 404 text
      const content = await page.textContent('body');
      expect(content).not.toContain('404');
      expect(content).not.toContain('Not Found');
    }
  });

  test('navigation through UI links works', async ({ page }) => {
    // Start at home
    await page.goto('/');
    
    // Navigate to games via UI link
    await page.click('a[href="/games"]');
    await expect(page).toHaveURL('/games');
    
    // Navigate to profile via UI link
    const profileLink = page.locator('a[href="/auth/profile"]');
    if (await profileLink.isVisible()) {
      await profileLink.click();
      await expect(page).toHaveURL('/auth/profile');
    }
    
    // Go back to games
    await page.goto('/games');
    
    // Click on a game detail link
    const gameLink = page.locator('a[href^="/games/"]').first();
    if (await gameLink.isVisible()) {
      await gameLink.click();
      await page.waitForURL(/\/games\/\d+/);
      
      // Verify we're on a valid page
      const response = await page.goto(page.url());
      expect(response?.status()).toBe(200);
    }
  });

  test('game detail pages are accessible', async ({ page }) => {
    await page.goto('/games');
    
    // Get all game links
    const gameLinks = page.locator('a[href^="/games/"][href*="/games/"]');
    const count = await gameLinks.count();
    
    // Check at least first game detail page
    if (count > 0) {
      const firstLink = gameLinks.first();
      const href = await firstLink.getAttribute('href');
      
      if (href && href.match(/\/games\/\d+$/)) {
        const response = await page.goto(href);
        expect(response?.status()).toBe(200);
        
        const content = await page.textContent('body');
        expect(content).not.toContain('404');
      }
    }
  });

  test('results pages are accessible', async ({ page }) => {
    await page.goto('/games');
    
    // Find a game ID
    const gameLink = page.locator('a[href^="/games/"]').first();
    const href = await gameLink.getAttribute('href');
    const gameId = href?.match(/\/games\/(\d+)/)?.[1];
    
    if (gameId) {
      const resultsUrl = `/games/${gameId}/results`;
      const response = await page.goto(resultsUrl);
      
      // Should return 200 (even if no results yet)
      expect(response?.status()).toBe(200);
      
      const content = await page.textContent('body');
      expect(content).not.toContain('404');
    }
  });
});
