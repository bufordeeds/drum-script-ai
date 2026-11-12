# Browser end-to-end checks

Both scripts drive the running Compose stack (`docker compose up`) with Playwright + Chromium.

```bash
npm i playwright && npx playwright install chromium     # once, anywhere outside the repo is fine

# full flow: upload -> progress -> chart -> play / 50% / drums / click / loop + count-in / bar click / downloads
node tests/e2e/ui.cjs eval/fixtures/rock_120.mp3 /tmp/shots

# numeric checks of the player (bit-exact at 100%, loop wrap, stretch length/pitch, click timing, count-in)
node tests/e2e/engine.cjs "http://localhost:3000/#/job/<job id>"
```

`engine.cjs` calls the player's audio callback directly and inspects the samples, so it does not need a sound device.
