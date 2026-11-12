// End-to-end UI check against the running Compose stack.
const { chromium } = require('playwright');
const path = require('path');
const BASE = process.env.BASE || 'http://localhost:3000';
const FILE = process.argv[2];
const SHOTS = process.argv[3] || '.';
const log = (...a) => console.log(...a);
(async () => {
  const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  await page.goto(BASE);
  await page.screenshot({ path: path.join(SHOTS, '1-upload.png') });
  await page.setInputFiles('[data-testid=file-input]', FILE);
  await page.waitForSelector('[data-testid=processing]', { timeout: 30000 });
  const seen = new Set();
  let shot = false;
  for (let i = 0; i < 600; i++) {
    if (await page.locator('[data-testid=score]').count()) break;
    if (await page.locator('[data-testid=job-error]').count()) throw new Error('job error: ' + await page.locator('[data-testid=job-error]').innerText());
    const st = await page.locator('[data-testid=stage]').innerText().catch(() => '');
    const pr = await page.locator('[data-testid=progress]').innerText().catch(() => '');
    if (st) seen.add(st + ' @' + pr);
    if (!shot && /Isolating/.test(st)) { await page.screenshot({ path: path.join(SHOTS, '2-processing.png') }); shot = true; }
    await page.waitForTimeout(500);
  }
  log('stages seen:', [...seen].join(' | '));
  await page.waitForFunction(() => Number(document.querySelector('[data-testid=score]')?.getAttribute('data-bars')) > 0, null, { timeout: 60000 });
  log('bars rendered:', await page.locator('[data-testid=score]').getAttribute('data-bars'));
  log('summary:', await page.locator('[data-testid=summary]').innerText());
  await page.waitForFunction(() => !!window.__engine, null, { timeout: 60000 });
  log('engine: sr', await page.evaluate(() => __engine.sampleRate), 'duration', await page.evaluate(() => __engine.duration.toFixed(2)));
  await page.screenshot({ path: path.join(SHOTS, '3-chart.png') });

  const cur = async () => page.evaluate(() => { const c = document.querySelector('[data-testid=cursor]'); return { bar: +c.dataset.bar, x: +c.dataset.x, t: __engine.currentTime, playing: __engine.playing }; });
  // play: cursor moves
  await page.click('[data-testid=play]');
  await page.waitForTimeout(3000);
  const a = await cur();
  await page.waitForTimeout(2000);
  const b = await cur();
  log('play: t', a.t.toFixed(2), '->', b.t.toFixed(2), 'bar', a.bar, '->', b.bar, 'rate', ((b.t - a.t) / 2).toFixed(3));
  await page.screenshot({ path: path.join(SHOTS, '4-playing.png') });
  // speed 50%
  await page.locator('[data-testid=speed]').fill('50');
  await page.waitForTimeout(1000);
  const c = await cur();
  await page.waitForTimeout(3000);
  const d = await cur();
  log('speed', await page.locator('[data-testid=speed-label]').innerText(), 'rate', ((d.t - c.t) / 3).toFixed(3));
  // toggle drums: position continuous
  const before = await cur();
  await page.click('[data-testid=source-drums]');
  await page.waitForTimeout(300);
  const after = await cur();
  log('toggle drums: source', await page.evaluate(() => __engine.source), 't', before.t.toFixed(2), '->', after.t.toFixed(2));
  // click on
  await page.check('[data-testid=click]');
  const c0 = await page.evaluate(() => __engine.stats.clicks);
  await page.waitForTimeout(3000);
  log('click track: clicks rendered in 3s at 50%:', (await page.evaluate(() => __engine.stats.clicks)) - c0);
  // loop bars 3-4 with count-in
  await page.click('[data-testid=play]'); // pause
  await page.locator('[data-testid=speed]').fill('100');
  await page.locator('[data-testid=loop-from]').fill('3');
  await page.locator('[data-testid=loop-to]').fill('4');
  log('loop highlight bars:', await page.locator('[data-testid=loop-bar]').count(), 'range', JSON.stringify(await page.evaluate(() => __engine.loopRange)));
  await page.click('[data-testid=play]');
  await page.waitForTimeout(300);
  log('count-in active:', await page.evaluate(() => __engine.countingIn), 'label:', await page.locator('[data-testid=bar]').innerText());
  const barsSeen = new Set();
  const w0 = await page.evaluate(() => __engine.stats.wraps);
  for (let i = 0; i < 60; i++) { barsSeen.add((await cur()).bar); await page.waitForTimeout(200); }
  log('loop: bars visited', [...barsSeen].sort((x, y) => x - y).join(','), 'wraps', (await page.evaluate(() => __engine.stats.wraps)) - w0);
  await page.screenshot({ path: path.join(SHOTS, '5-loop.png') });
  await page.click('[data-testid=play]');
  await page.click('[data-testid=loop-clear]');
  // click a bar to seek, drag across bars to loop
  const boxOf = async (bar) => {
    await page.locator('[data-testid=loop-from]').fill(String(bar));
    await page.locator('[data-testid=loop-to]').fill(String(bar));
    const box = await page.locator('[data-testid=loop-bar]').first().boundingBox();
    await page.click('[data-testid=loop-clear]');
    return box;
  };
  const b6 = await boxOf(6), b2 = await boxOf(2), b3 = await boxOf(3);
  await page.mouse.click(b6.x + b6.width / 2, b6.y + b6.height / 2);
  await page.waitForTimeout(200);
  log('click bar 6 -> label:', await page.locator('[data-testid=bar]').innerText(), 't', (await cur()).t.toFixed(2));
  await page.mouse.move(b2.x + b2.width / 2, b2.y + b2.height / 2);
  await page.mouse.down();
  await page.mouse.move(b3.x + b3.width / 2, b3.y + b3.height / 2, { steps: 5 });
  await page.mouse.up();
  log('drag bars 2-3 -> loop inputs:', await page.locator('[data-testid=loop-from]').inputValue(), '-', await page.locator('[data-testid=loop-to]').inputValue());
  await page.click('[data-testid=loop-clear]');
  // downloads
  for (const id of ['dl-musicxml', 'dl-midi']) {
    const [dl] = await Promise.all([page.waitForEvent('download'), page.click(`[data-testid=${id}]`)]);
    const p = await dl.path();
    log('download', dl.suggestedFilename(), require('fs').statSync(p).size, 'bytes');
  }
  log('console errors:', errors.length ? errors : 'none');
  await browser.close();
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
