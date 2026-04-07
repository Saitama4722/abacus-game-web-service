# E2E Tests for Abacus Game

Automated browser tests using Playwright.

## Setup

1. Install Node.js dependencies:
```bash
npm install
```

2. Install Playwright browsers:
```bash
npx playwright install chromium
```

## Running Tests

### Run all tests:
```bash
npm test
```

### Run tests with browser visible (headed mode):
```bash
npm run test:headed
```

### Run tests in interactive UI mode:
```bash
npm run test:ui
```

### View test report:
```bash
npm run test:report
```

## Test Structure

- `setup.spec.js` - Prepares clean demo data before tests
- `01-basic-access.spec.js` - Basic site accessibility tests
- `02-authentication.spec.js` - Login/logout flow tests
- `03-profile.spec.js` - User profile page tests
- `04-games-flow.spec.js` - Games list and navigation tests
- `05-admin-flow.spec.js` - Admin game creation tests
- `06-regression-checks.spec.js` - Broken link regression tests

## Test Data

Tests use the existing demo data reset script (`scripts/reset_demo_games.py`) to ensure predictable test data. The setup test runs automatically before other tests.

## Configuration

See `playwright.config.js` for configuration details. The tests:
- Run against local server at http://localhost:8000
- Automatically start the FastAPI server before tests
- Generate HTML reports in `test-results/html-report/`
- Capture screenshots and videos on failure
- Capture traces on retry
