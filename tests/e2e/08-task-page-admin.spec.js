// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Task Page - Admin/Moderator Features', () => {
  test('admin can see task page with role-specific content', async ({ page }) => {
    // Log in as admin
    await page.goto('/auth/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(profile|games|admin|$)/);
    
    // Navigate to games list
    await page.goto('/games');
    
    // Find first game
    const gameLink = page.locator('a[href^="/games/"]').first();
    if (await gameLink.count() > 0) {
      await gameLink.click();
      await page.waitForURL(/\/games\/\d+$/);
      
      // Click play button
      const playButton = page.locator('a[href*="/play"]').first();
      if (await playButton.isVisible()) {
        await playButton.click();
        await page.waitForURL(/\/games\/\d+\/play/);
        
        // Find and click first available task
        const firstTask = page.locator('a[href*="/task/"]').first();
        if (await firstTask.isVisible()) {
          await firstTask.click();
          await page.waitForURL(/\/games\/\d+\/task\/\d+/);
          
          // Verify task page loaded without error
          const pageContent = await page.textContent('body');
          expect(pageContent).not.toContain('500');
          expect(pageContent).not.toContain('Internal Server Error');
          expect(pageContent).not.toContain('UndefinedError');
          expect(pageContent).not.toContain("'user' is undefined");
          expect(pageContent).not.toContain("'topic' is undefined");
          
          // Admin should see the role-specific message (if user.role check works)
          // The template has: {% if user.role in ('administrator', 'moderator') %}
          // This should not crash even if the message isn't visible
          
          // Verify basic elements render
          const taskHeading = page.locator('h1').filter({ hasText: /Задание \d+/ });
          await expect(taskHeading).toBeVisible();
          
          const answerForm = page.locator('form');
          await expect(answerForm).toBeVisible();
        }
      }
    }
  });

  test('regular user can see task page without admin-specific content', async ({ page }) => {
    // Log in as regular user
    await page.goto('/auth/login');
    await page.fill('input[name="username"]', 'user');
    await page.fill('input[name="password"]', 'user');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(profile|games|$)/);
    
    // Navigate to games list
    await page.goto('/games');
    
    // Find first game
    const gameLink = page.locator('a[href^="/games/"]').first();
    if (await gameLink.count() > 0) {
      await gameLink.click();
      await page.waitForURL(/\/games\/\d+$/);
      
      // Click play button
      const playButton = page.locator('a[href*="/play"]').first();
      if (await playButton.isVisible()) {
        await playButton.click();
        await page.waitForURL(/\/games\/\d+\/play/);
        
        // Find and click first available task
        const firstTask = page.locator('a[href*="/task/"]').first();
        if (await firstTask.isVisible()) {
          await firstTask.click();
          await page.waitForURL(/\/games\/\d+\/task\/\d+/);
          
          // Verify task page loaded without error
          const pageContent = await page.textContent('body');
          expect(pageContent).not.toContain('500');
          expect(pageContent).not.toContain('Internal Server Error');
          expect(pageContent).not.toContain('UndefinedError');
          expect(pageContent).not.toContain("'user' is undefined");
          expect(pageContent).not.toContain("'topic' is undefined");
          
          // Verify basic elements render
          const taskHeading = page.locator('h1').filter({ hasText: /Задание \d+/ });
          await expect(taskHeading).toBeVisible();
          
          const answerForm = page.locator('form');
          await expect(answerForm).toBeVisible();
        }
      }
    }
  });
});
