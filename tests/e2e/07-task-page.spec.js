// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Task Page Opening and Rendering', () => {
  test.beforeEach(async ({ page }) => {
    // Log in as user
    await page.goto('/auth/login');
    await page.fill('input[name="username"]', 'user');
    await page.fill('input[name="password"]', 'user');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(profile|games|$)/);
  });

  test('can open task page from Abacus game without 500 error', async ({ page }) => {
    // Navigate to games list
    await page.goto('/games');
    
    // Find Abacus demo game
    const abacusGameLink = page.locator('a[href^="/games/"]').filter({ hasText: /Абакус|Демо-игра Абакус/i }).first();
    
    if (await abacusGameLink.count() > 0) {
      await abacusGameLink.click();
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
          
          // Verify task page loaded without 500 error
          const pageContent = await page.textContent('body');
          expect(pageContent).not.toContain('500');
          expect(pageContent).not.toContain('Internal Server Error');
          expect(pageContent).not.toContain('UndefinedError');
          
          // Verify topic is rendered (this was the bug)
          const topicText = page.locator('text=/Тема:/');
          await expect(topicText).toBeVisible();
          
          // Verify task content is rendered
          const taskHeading = page.locator('h1').filter({ hasText: /Задание \d+/ });
          await expect(taskHeading).toBeVisible();
          
          // Verify answer form exists
          const answerForm = page.locator('form');
          await expect(answerForm).toBeVisible();
          
          // Verify no UndefinedError for user variable
          expect(pageContent).not.toContain("'user' is undefined");
        }
      }
    }
  });

  test('can open task page from 5x5 game without 500 error', async ({ page }) => {
    // Navigate to games list
    await page.goto('/games');
    
    // Find 5x5 demo game
    const fiveByFiveGameLink = page.locator('a[href^="/games/"]').filter({ hasText: /5×5|5x5|Пять-на-пять/i }).first();
    
    if (await fiveByFiveGameLink.count() > 0) {
      await fiveByFiveGameLink.click();
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
          
          // Verify task page loaded without 500 error
          const pageContent = await page.textContent('body');
          expect(pageContent).not.toContain('500');
          expect(pageContent).not.toContain('Internal Server Error');
          expect(pageContent).not.toContain('UndefinedError');
          
          // Verify topic is rendered (this was the bug)
          const topicText = page.locator('text=/Тема:/');
          await expect(topicText).toBeVisible();
          
          // Verify task content is rendered
          const taskHeading = page.locator('h1').filter({ hasText: /Задание \d+/ });
          await expect(taskHeading).toBeVisible();
          
          // Verify answer form exists
          const answerForm = page.locator('form');
          await expect(answerForm).toBeVisible();
          
          // Verify no UndefinedError for user variable
          expect(pageContent).not.toContain("'user' is undefined");
        }
      }
    }
  });

  test('task page renders all required elements', async ({ page }) => {
    // Navigate to games and open first available task
    await page.goto('/games');
    
    const gameLink = page.locator('a[href^="/games/"]').first();
    await gameLink.click();
    await page.waitForURL(/\/games\/\d+$/);
    
    const playButton = page.locator('a[href*="/play"]').first();
    if (await playButton.isVisible()) {
      await playButton.click();
      await page.waitForURL(/\/games\/\d+\/play/);
      
      const firstTask = page.locator('a[href*="/task/"]').first();
      if (await firstTask.isVisible()) {
        await firstTask.click();
        await page.waitForURL(/\/games\/\d+\/task\/\d+/);
        
        // Check all required elements
        // 1. Breadcrumb navigation
        const breadcrumb = page.locator('nav[aria-label="breadcrumb"]');
        await expect(breadcrumb).toBeVisible();
        
        // 2. Task title with order_index (uses task.order_index)
        const taskTitle = page.locator('h1').filter({ hasText: /Задание \d+/ });
        await expect(taskTitle).toBeVisible();
        
        // 3. Topic title (uses topic.title - this was missing)
        const topicLabel = page.locator('text=/Тема:/');
        await expect(topicLabel).toBeVisible();
        
        // 4. Task text/condition
        const taskCondition = page.locator('text=/Условие/');
        await expect(taskCondition).toBeVisible();
        
        // 5. Answer form
        const answerInput = page.locator('input[name="answer"], textarea[name="answer"]');
        await expect(answerInput).toBeVisible();
        
        // 6. Submit button
        const submitButton = page.locator('button[type="submit"]');
        await expect(submitButton).toBeVisible();
      }
    }
  });
});
