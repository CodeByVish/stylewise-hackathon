import { test, expect } from '@playwright/test';
import path from 'node:path';

test('both sizes load across three views and controls update the scene', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/fixtures-demo');
  await expect(page.locator('.canvas-host canvas')).toBeVisible();
  await expect(page.locator('.viewer-status')).toHaveCount(0);
  for (const size of ['S', 'M']) {
    await page.getByRole('button', { name: new RegExp(`^${size} \\d+ cm chest$`) }).click();
    await expect(page.locator('.viewer-status')).toHaveCount(0);
    await expect(page.locator('.scene-badge')).toHaveText(`3D / ${size}`);
    for (const view of ['front', 'side', 'back']) {
      const button = page.getByRole('button', { name: view, exact: true });
      await button.click();
      await expect(button).toHaveAttribute('aria-pressed', 'true');
      await expect(page.locator('.canvas-host')).toHaveAttribute('aria-label', new RegExp(`${view} view`));
    }
  }
  await page.getByRole('button', { name: 'Rotate', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Pause', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'front', exact: true }).click();
  await page.getByLabel('Show body').uncheck();
  await expect(page.getByLabel('Show body')).not.toBeChecked();
  await page.getByLabel('Show body').check();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: '/tmp/stylewise-fitlab-desktop.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('report imports, input invalidation, metadata and request export', async ({ page }) => {
  await page.goto('/fixtures-demo');
  await page.getByLabel('Fit report file').setInputFiles(path.resolve('public/fixtures/report-m.json'));
  await expect(page.locator('.evidence-tag')).toHaveText('IMPORTED FIT REPORT');
  await page.getByLabel('Chest in centimeters').fill('94');
  await expect(page.locator('.evidence-tag')).toHaveText('FIXTURE · DIMENSION COMPARISON');
  const custom = { id: 'test-top', name: 'Test sourced top', source: 'Controlled test size chart', sizes: { S: {chestCm: 90, waistCm: 75, meshUrl:'/fixtures/top-s.glb'}, M: {chestCm: 104, waistCm: 88, meshUrl:'/fixtures/top-m.glb'} } };
  await page.getByLabel('Garment metadata file').setInputFiles({name:'garment.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(custom))});
  await expect(page.getByRole('heading', {name:'Test sourced top'})).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export fit request' }).click();
  const request = JSON.parse(await (await (await download).createReadStream())!.toArray().then(parts => Buffer.concat(parts).toString()));
  expect(request.garment.chestCm).toBe(104);
  expect(request.garment.source).toBe(custom.source);
  await page.getByLabel('Fit report file').setInputFiles({name:'invalid.json',mimeType:'application/json',buffer:Buffer.from('{}')});
  await expect(page.locator('.message')).toContainText('Invalid report');
  await expect(page.locator('.evidence-tag')).toHaveText('SUPPLIED SPECS · DIMENSION COMPARISON');
});

test('mobile layout has no horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/fixtures-demo');
  await expect(page.locator('.canvas-host canvas')).toBeVisible();
  await expect(page.locator('.viewer-status')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({path:'/tmp/stylewise-fitlab-mobile.png',fullPage:true});
});

test('missing garment mesh shows a recoverable error', async ({ page }) => {
  await page.goto('/fixtures-demo');
  await page.getByLabel('Garment metadata file').setInputFiles({
    name: 'missing-mesh.json', mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify({id:'missing',name:'Missing asset test',source:'Controlled missing-asset test',sizes:{S:{chestCm:86,waistCm:72,meshUrl:'/fixtures/missing.glb'},M:{chestCm:98,waistCm:84,meshUrl:'/fixtures/missing.glb'}}})),
  });
  await expect(page.locator('.viewer-status')).toContainText('Could not load these 3D assets');
  await page.getByRole('button', {name:'Use synthetic garment'}).click();
  await expect(page.locator('.viewer-status')).toHaveCount(0);
  await expect(page.locator('.canvas-host canvas')).toBeVisible();
});
