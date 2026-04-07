// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Authentication Flow', () => {
  test('admin can log in successfully', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Fill in admin credentials
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin');
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Wait for navigation after login
    await page.waitForURL(/\/(profile|games|admin|$)/);
    
    // Verify we're logged in - check for logout link or user menu
    const logoutLink = page.locator('a[href="/auth/logout"]');
    await expect(logoutLink).toBeVisible();
  });

  test('regular user can log in successfully', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Fill in user credentials
    await page.fill('input[name="username"]', 'user');
    await page.fill('input[name="password"]', 'user');
    
    // Submit form
    await page.click('button[type="submit"]');
    
    // Wait for navigation
    await page.waitForURL(/\/(profile|games|$)/);
    
    // Verify logged in
    const logoutLink = page.locator('a[href="/auth/logout"]');
    await expect(logoutLink).toBeVisible();
  });

  test('invalid credentials show error', async ({ page }) => {
    await page.goto('/auth/login');
    
    // Try invalid credentials
    await page.fill('input[name="username"]', 'invalid_user');
    await page.fill('input[name="password"]', 'wrong_password');
    await page.click('button[type="submit"]');
    
    // Should stay on login page or show error
    await page.waitForTimeout(1000);
    
    // Check we're still on login page or error is shown
    const currentUrl = page.url();
    expect(currentUrl).toContain('/auth/login');
  });
});
