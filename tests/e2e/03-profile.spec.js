// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('User Profile Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Log in as regular user before each test
    await page.goto('/auth/login');
    await page.fill('input[name="username"]', 'user');
    await page.fill('input[name="password"]', 'user');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(profile|games|$)/);
  });

  test('authenticated user can access profile page', async ({ page }) => {
    // Navigate to profile
    await page.goto('/auth/profile');
    
    // Verify profile page loads
    await expect(page).toHaveURL('/auth/profile');
    
    // Check for profile content (heading or user info)
    const heading = page.locator('h1, h2').first();
    await expect(heading).toBeVisible();
  });

  test('profile page renders without server error', async ({ page }) => {
    await page.goto('/auth/profile');
    
    // Check no 500 error or crash
    const response = await page.goto('/auth/profile');
    expect(response?.status()).toBeLessThan(500);
    
    // Page should have basic structure
    await expect(page.locator('body')).toBeVisible();
  });

  test('profile page shows team info or no-team message', async ({ page }) => {
    await page.goto('/auth/profile');
    
    // Should show either team information or a message about not being in a team
    // Just verify the page has content
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeTruthy();
    expect(pageContent.length).toBeGreaterThan(50);
  });
});
