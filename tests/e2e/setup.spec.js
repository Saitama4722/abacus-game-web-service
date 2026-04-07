// @ts-check
const { test, expect } = require('@playwright/test');
const { execSync } = require('child_process');
const path = require('path');

/**
 * Setup test - runs before all other tests to prepare test data
 * This ensures we have clean, predictable demo data for testing
 */
test.describe.configure({ mode: 'serial' });

test.describe('Test Data Setup', () => {
  test('prepare clean demo data', async () => {
    console.log('Preparing clean demo data...');
    
    // Run the demo reset script to create fresh test data
    const scriptPath = path.join(__dirname, '..', '..', 'scripts', 'reset_demo_games.py');
    
    try {
      execSync(`python "${scriptPath}"`, {
        cwd: path.join(__dirname, '..', '..'),
        stdio: 'pipe',
        encoding: 'utf-8'
      });
      console.log('Demo data prepared successfully');
    } catch (error) {
      console.error('Failed to prepare demo data:', error.message);
      throw error;
    }
  });
});
