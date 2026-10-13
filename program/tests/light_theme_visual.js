const { chromium } = require('D:/Codex/tools/playwright/node_modules/playwright-core');
const path = require('path');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  });
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: 1,
    serviceWorkers: 'block',
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`));
  page.on('console', message => {
    if (message.type() === 'error' && !message.text().includes('fonts.googleapis.com')) {
      errors.push(`console: ${message.text()}`);
    }
  });

  const routes = [
    ['today', '/today'],
    ['card', '/cards/c21aa6f7dfa6-002'],
    ['settings', '/settings'],
    ['statistics', '/statistics'],
  ];
  const results = [];
  for (const [name, route] of routes) {
    await page.goto(`http://127.0.0.1:8765${route}`, { waitUntil: 'networkidle' });
    await page.locator('main').waitFor({ state: 'visible' });
    const colors = await page.evaluate(() => {
      const read = selector => {
        const element = document.querySelector(selector);
        if (!element) return null;
        const style = getComputedStyle(element);
        return { color: style.color, background: style.backgroundColor, backgroundImage: style.backgroundImage };
      };
      return {
        body: read('body'),
        aside: read('.app aside'),
        topbar: read('.topbar'),
        surface: read('.card-tile,.detail,.panel,.form-panel'),
        performance: {
          backdropFilterCount: [...document.querySelectorAll('*')].filter(element => {
            const style = getComputedStyle(element);
            return [style.backdropFilter, style.webkitBackdropFilter].filter(Boolean).some(value => value !== 'none');
          }).length,
          mainBackgroundAnimation: getComputedStyle(document.querySelector('.blue-sky-scene')).animationName,
          waterDisplay: getComputedStyle(document.querySelector('.water-shimmer')).display,
        },
      };
    });
    const file = path.resolve('artifacts', `light-theme-${name}.png`);
    await page.screenshot({ path: file, fullPage: false });
    results.push({ name, route, file, colors });
  }

  await browser.close();
  const performanceFailures = results.filter(result =>
    result.colors.performance.backdropFilterCount !== 0 ||
    result.colors.performance.mainBackgroundAnimation !== 'none' ||
    result.colors.performance.waterDisplay !== 'none'
  );
  console.log(JSON.stringify({ results, errors, performanceFailures }, null, 2));
  if (errors.length || performanceFailures.length) process.exitCode = 1;
})().catch(error => {
  console.error(error);
  process.exit(1);
});
