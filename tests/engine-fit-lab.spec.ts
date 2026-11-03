import { test, expect } from '@playwright/test';

test('the fitting room loads a real catalogue photo and chart-backed size choices', async ({ page }) => {
  test.setTimeout(60_000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/try');
  const fit = page.getByRole('complementary', { name: 'Your fit report' });
  await expect(fit.getByRole('button', { name: 'Garment size M', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await expect(fit.locator('.room-regions')).toContainText('cm', { timeout: 30_000 });
  const preview = page.getByRole('region', { name: 'Garment preview', exact: true });
  await expect(preview.getByAltText(/AI illustration: .*size M, front view/)).toBeVisible({ timeout: 30_000 });
  for (const view of ['side', 'back', 'front']) {
    await page.locator('.room-angle-controls').getByRole('button', { name: view, exact: true }).click();
    await expect(preview.getByAltText(new RegExp(`AI illustration: .*${view} view`))).toBeVisible({ timeout: 30_000 });
  }
  await page.getByRole('button', { name: 'Dresses', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Try Emerald wrap dress', exact: true })).toBeVisible();
  expect(errors).toEqual([]);
  await page.screenshot({ path: '/tmp/stylewise-room-desktop.png', fullPage: true });
});

test('size comparison keeps the body fixed and never substitutes a missing size preview', async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto('/try');
  await expect(page.locator('.room-fit')).toHaveAttribute('aria-busy', 'false', { timeout: 30_000 });
  await page.locator('.room-fit .room-primary').click();
  const comparison = page.getByRole('dialog', { name: 'Compare sizes on your shape' });
  await expect(comparison).toBeVisible();
  await expect(comparison.locator('.room-compare-card')).toHaveCount(3);
  await expect(comparison).toContainText('Same preset and fit preference');
  await expect(comparison.getByText('Best fit', { exact: true })).toHaveCount(0);
  await comparison.getByRole('button', { name: 'View size S', exact: false }).click();
  await expect(comparison).not.toBeVisible();
  await expect(page.getByRole('button', { name: 'Garment size S', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: 'M', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.room-stage-heading')).toContainText('Size S');
});

test('Nisha drawer opens from the verdict, suggests questions and preserves garment context', async ({ page }) => {
  let context: unknown;
  await page.route('**/api/engine/nisha/chat', async route => {
    context = route.request().postDataJSON().context;
    await route.fulfill({ json: { reply: 'Compare the documented dimensions before choosing.', report: null, source: 'engine-template' } });
  });
  await page.goto('/try');
  const trigger = page.getByRole('button', { name: 'Ask Nisha about this size', exact: false });
  await trigger.click();
  const drawer = page.getByRole('dialog', { name: 'Ask Nisha', exact: true });
  await expect(drawer).toBeVisible();
  await drawer.getByRole('button', { name: 'Should I try a larger size?', exact: false }).click();
  await expect(drawer.getByLabel('Message Nisha')).toHaveValue('Should I try a larger size?');
  await drawer.getByRole('button', { name: 'Ask Nisha', exact: true }).click();
  await expect(drawer.locator('.chat-turn.assistant')).toContainText('documented dimensions');
  expect(context).toMatchObject({ garment_id: 'zesica-black-midi-dress', garment_size: 'M', body: { source: 'preset' } });
  await page.keyboard.press('Escape');
  await expect(drawer).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test('body size and garment size remain independent and the body model is available', async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto('/try');
  await page.getByRole('button', { name: 'S', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Garment size M', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Explore your body model', exact: false }).click();
  await expect(page.locator('.canvas-host canvas')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('.viewer-status')).toHaveCount(0, { timeout: 30_000 });
  await page.getByRole('button', { name: 'Rotate model', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Pause rotation' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Enter measurements', exact: true }).click();
  await page.getByLabel('Bust in centimeters').fill('94');
  await expect(page.locator('.room-fit')).toHaveAttribute('aria-busy', 'false', { timeout: 30_000 });
  await expect(page.locator('.room-stage-message')).toContainText('Your measurements');
});

test('loading and missing preview states do not hide the fit report', async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/engine/preview/photo', async route => {
    await gate;
    await route.fulfill({ status: 404, json: { detail: 'Not prepared' } });
  });
  await page.goto('/try');
  await expect(page.getByText('Preparing the front view', { exact: true })).toBeVisible();
  await expect(page.locator('.room-fit')).toHaveAttribute('aria-busy', 'false', { timeout: 30_000 });
  release();
  await expect(page.getByText('PRODUCT PHOTO · NOT A TRY-ON', { exact: true })).toBeVisible();
  await expect(page.getByAltText(/Product photo reference/)).toBeVisible();
  await expect(page.locator('.room-fit .room-regions')).toContainText('cm');
});

test('mobile fitting room and Nisha bottom sheet have no overflow or pill controls', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/try');
  await expect(page.locator('.room-fit')).toHaveAttribute('aria-busy', 'false', { timeout: 30_000 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.evaluate(() => scrollY)).toBe(0);
  const selectedPhoto = page.locator('.room-product[aria-pressed=true]');
  const rail = await page.locator('.room-product-rail').boundingBox();
  const selected = await selectedPhoto.boundingBox();
  expect(selected!.x).toBeGreaterThanOrEqual(rail!.x - 1);
  expect(selected!.x + selected!.width).toBeLessThanOrEqual(rail!.x + rail!.width + 1);
  const design = await page.locator('.room-primary').evaluate(button => ({ radius: parseFloat(getComputedStyle(button).borderRadius), background: getComputedStyle(button).backgroundImage }));
  expect(design.radius).toBeLessThanOrEqual(2);
  expect(design.background).toBe('none');
  await page.screenshot({ path: '/tmp/stylewise-room-mobile.png', fullPage: true });
  await page.locator('.room-header-nisha').click();
  const drawer = page.getByRole('dialog', { name: 'Ask Nisha', exact: true });
  await expect(drawer).toBeVisible();
  const bounds = await drawer.boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.width).toBeLessThanOrEqual(390);
  await page.screenshot({ path: '/tmp/stylewise-room-nisha.png' });
});
