// Renders the player engine offline (calling its audio callback directly) and checks the output numerically.
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(process.argv[2]);
  await page.waitForFunction(() => !!window.__engine, null, { timeout: 60000 });
  const res = await page.evaluate(async () => {
    const e = window.__engine, sr = e.sampleRate, N = 2048;
    const render = (blocks) => {
      const L = new Float32Array(blocks * N), R = new Float32Array(blocks * N);
      for (let b = 0; b < blocks; b++) {
        const l = new Float32Array(N), r = new Float32Array(N);
        e.process({ outputBuffer: { getChannelData: (i) => (i ? r : l) } });
        L.set(l, b * N); R.set(r, b * N);
      }
      return L;
    };
    const start = (t) => { e.seek(t); e._playing = true; };
    const out = {};
    const mix = e.data.mix[0], drums = e.data.drums[0];
    const maxDiff = (a, b, off) => { let m = 0; for (let i = 0; i < a.length; i++) m = Math.max(m, Math.abs(a[i] - b[off + i])); return m; };
    const rms = (a) => Math.sqrt(a.reduce((s, x) => s + x * x, 0) / a.length);

    // 1. 100% speed is a bit-exact copy of the selected source
    e.setSpeed(1); e.clickEnabled = false; e.setLoop(null); e.setSource('mix'); start(5);
    let o = render(20);
    out.exactMix = maxDiff(o, mix, Math.round(5 * sr));
    e.setSource('drums'); start(5); o = render(20);
    out.exactDrums = maxDiff(o, drums, Math.round(5 * sr));
    out.mixVsDrumsDiffer = maxDiff(mix.subarray(5 * sr, 6 * sr), drums, 5 * sr) > 0.01;

    // 2. loop wraps sample-accurately
    e.setSource('mix'); e.setLoop({ start: 4, end: 6 }); start(5.9);
    o = render(10);
    const wrapAt = Math.round(0.1 * sr);
    out.loopBeforeWrap = maxDiff(o.subarray(0, wrapAt), mix, Math.round(5.9 * sr));
    out.loopAfterWrap = maxDiff(o.subarray(wrapAt, wrapAt + 8000), mix, Math.round(4 * sr));
    e.setLoop(null);

    // 3. 50% speed: twice as long, same pitch. Compare drum onsets and zero-crossing rate.
    const onsets = (a) => { // crude energy-rise onset detector, 10 ms frames
      const h = Math.round(sr * 0.01), env = [];
      for (let i = 0; i + h <= a.length; i += h) { let s = 0; for (let k = 0; k < h; k++) s += a[i + k] * a[i + k]; env.push(Math.sqrt(s / h)); }
      const peak = Math.max(...env), t = [];
      for (let i = 2; i < env.length; i++) if (env[i] > 0.25 * peak && env[i] > 2.2 * (env[i - 2] + 1e-4) && (!t.length || i - t[t.length - 1] > 6)) t.push(i);
      return t.map((i) => (i * h) / sr);
    };
    const zcr = (a) => { let z = 0; for (let i = 1; i < a.length; i++) if ((a[i] >= 0) !== (a[i - 1] >= 0)) z++; return z / a.length; };
    e.setSource('drums');
    const srcSeg = drums.subarray(Math.round(4 * sr), Math.round(12 * sr));
    const srcOn = onsets(srcSeg);
    for (const sp of [0.5, 0.75]) {
      e.setSpeed(sp); start(4);
      const blocks = Math.round((8 / sp) * sr / N);
      o = render(blocks);
      const on = onsets(o).map((t) => t * sp);
      // match stretched onsets (rescaled to song time) against source onsets within 30 ms
      let matched = 0; const used = new Set();
      for (const t of srcOn) { const j = on.findIndex((u, k) => !used.has(k) && Math.abs(u - t) < 0.03); if (j >= 0) { matched++; used.add(j); } }
      out['stretch' + sp] = { srcOnsets: srcOn.length, outOnsets: on.length, matched, zcrRatio: +(zcr(o) / zcr(srcSeg)).toFixed(3), rmsRatio: +(rms(o) / rms(srcSeg)).toFixed(3), endSong: +((e.songAt(e.vOut)) / sr).toFixed(3) };
    }

    // 4. click placement: render with and without click, the difference is the click track
    const beats = Array.from(e.beatFrames).map((f) => f / sr);
    for (const sp of [1, 0.5]) {
      e.setSpeed(sp); e.setSource('mix');
      const blocks = Math.round((6 / sp) * sr / N);
      e.clickEnabled = false; start(4); const dry = render(blocks);
      e.clickEnabled = true; start(4); const wet = render(blocks);
      e.clickEnabled = false;
      const found = [];
      for (let i = 0; i < wet.length; i++) if (Math.abs(wet[i] - dry[i]) > 1e-4 && (!found.length || i - found[found.length - 1] > sr * 0.1)) found.push(i);
      const expected = beats.filter((b) => b >= 4 && b < 10 - 0.05).map((b) => (b - 4) / sp);
      const errs = found.map((f, k) => Math.abs(f / sr - (expected[k] ?? 1e9)) * 1000);
      out['click' + sp] = { expected: expected.length, found: found.length, maxErrMs: +Math.max(...errs).toFixed(2) };
    }

    // 5. count-in: one bar of clicks, then music starts exactly at the loop start
    e.setSpeed(1); e.setLoop({ start: beats[8], end: beats[12] }); e.countInEnabled = true;
    e.seek(0); e.countIn = e.buildCountIn(e.loop.start); e.seek(beats[8]); e.countIn = e.buildCountIn(e.loop.start); e._playing = true;
    const total = e.countIn.total;
    o = render(Math.ceil(total / N) + 4);
    out.countIn = { bars: 1, clicks: e.countIn === null, lengthS: +(total / sr).toFixed(3), barS: +(beats[12] - beats[8]).toFixed(3),
      musicStartsAtLoop: maxDiff(o.subarray(total + 2000, total + 6000), mix, Math.round(beats[8] * sr) + 2000) < 1e-6 };
    e._playing = false; e.setLoop(null);
    return out;
  });
  console.log(JSON.stringify(res, null, 1));
  await browser.close();
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
