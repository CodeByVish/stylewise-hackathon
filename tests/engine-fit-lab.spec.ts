import { test, expect } from '@playwright/test';

test('live presets, fit reports and fit-shell scene stay in sync', async ({page})=>{
  test.setTimeout(90_000);
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('combobox',{name:'Garment',exact:true})).toContainText(/kurta/i);
  await expect(page.locator('.engine-regions')).toBeVisible({timeout:30_000});
  await expect(page.locator('.viewer-caption')).toHaveText('Approximate fit shell · no cloth drape',{timeout:45_000});
  await expect(page.locator('.viewer-status')).toHaveCount(0);
  await page.getByRole('button',{name:'The Anchor',exact:true}).click();
  await expect(page.locator('.viewer-top h2')).toHaveText('The Anchor');
  await expect(page.locator('.viewer-caption')).toHaveText('Approximate fit shell · no cloth drape',{timeout:45_000});
  await page.getByRole('combobox',{name:'Body proportions'}).selectOption('male');
  await page.getByRole('combobox',{name:'Usual size'}).selectOption('L');
  await expect(page.locator('.viewer-caption')).toHaveText('Approximate fit shell · no cloth drape',{timeout:45_000});
  await expect(page.locator('.viewer-status')).toHaveCount(0);
  for(const view of ['front','side','back'])await page.getByRole('button',{name:view,exact:true}).click();
  await page.getByRole('button',{name:'front',exact:true}).click();
  await page.screenshot({path:'/tmp/stylewise-engine-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Use measurements'}).click();
  await expect(page.locator('.viewer-status')).toContainText('The engine evaluates your measurements');
  await expect(page.locator('.engine-regions')).toBeVisible({timeout:30_000});
  expect(errors).toEqual([]);
});

test('Nisha uses the current garment context and mobile layout stays within screen',async({page})=>{
  let context:unknown;
  await page.route('**/api/engine/nisha/chat',async route=>{
    context=route.request().postDataJSON().context;
    await route.fulfill({json:{reply:'Beta, compare the documented dimensions before choosing.',report:null,source:'engine-template'}});
  });
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await page.getByLabel('Message Nisha').fill('Compare this size');
  await page.getByRole('button',{name:'Ask Nisha',exact:true}).click();
  await expect(page.locator('.chat-turn.assistant')).toContainText('documented dimensions');
  expect(context).toMatchObject({garment_id:'green-kurta',garment_size:'M',body:{source:'preset'}});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:'/tmp/stylewise-engine-mobile.png',fullPage:true});
});

test('size comparison selects the viewed size and garment photos stay linked to SAM',async({page})=>{
  test.setTimeout(90_000);
  await page.goto('/');
  const comparison=page.getByRole('region',{name:'Size comparison'});
  await expect(comparison.getByRole('table')).toBeVisible({timeout:30_000});
  await expect(comparison.getByRole('row')).toHaveCount(4);
  await comparison.getByRole('button',{name:'S',exact:true}).click();
  await expect(page.locator('.scene-badge')).toHaveText('3D / S');
  await expect(comparison.getByRole('button',{name:/^S\s*Viewing$/})).toHaveAttribute('aria-pressed','true',{timeout:30_000});
  const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l1sAAAAASUVORK5CYII=','base64');
  await page.getByLabel('Selected garment photo').setInputFiles({name:'kurta.png',mimeType:'image/png',buffer:png});
  await expect(page.getByAltText('Green kurta product photo')).toBeVisible();
  await expect(page.getByAltText('Selected garment product photo')).toBeVisible();
  await expect(page.getByRole('textbox',{name:'Photo source'})).toHaveValue('kurta.png');
  await page.getByRole('combobox',{name:'Garment',exact:true}).selectOption('evening-kurta');
  await expect(page.getByAltText('Selected garment product photo')).toHaveCount(0);
  await page.getByRole('combobox',{name:'Garment',exact:true}).selectOption('green-kurta');
  await expect(page.getByAltText('Green kurta product photo')).toBeVisible();
  await page.getByRole('button',{name:'Remove',exact:true}).click();
  await expect(page.getByAltText('Selected garment product photo')).toHaveCount(0);
});

test('scene preparation is announced until the garment response arrives',async({page})=>{
  test.setTimeout(60_000);
  let release!:()=>void;
  const gate=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/engine/viewer/scene',async route=>{await gate;await route.continue();});
  await page.goto('/');
  await expect(page.getByText('Preparing garment preview…',{exact:true})).toBeVisible({timeout:30_000});
  await expect(page.getByRole('region',{name:'3D fitting room'})).toHaveAttribute('aria-busy','true');
  release();
  await expect(page.locator('.viewer-caption')).toHaveText('Approximate fit shell · no cloth drape',{timeout:45_000});
  await expect(page.getByRole('region',{name:'3D fitting room'})).toHaveAttribute('aria-busy','false');
});
