# DECISIONS

One line per judgment call, newest at the bottom.

## Licenses (commercial use)

- **ADTOF (MZehren/ADTOF)** — repo README + LICENSE: *CC BY-NC-SA 4.0* ("Attribution-NonCommercial-ShareAlike"). **Commercial use is not permitted** without separate permission from the authors; ShareAlike applies to derivatives.
- **ADTOF-pytorch (xavriley/ADTOF-pytorch)** — **no LICENSE file at all** (checked at commit `85c192e`), so no rights are granted by default for the port code. Its bundled weights are a direct conversion of ADTOF's released Keras weights, so they inherit CC BY-NC-SA 4.0 at minimum. Net: fine for local testing/evaluation, **not OK to sell a product on** → listed under NEEDS BUFORD.
- **Demucs** — code MIT. Pretrained `htdemucs` weights were trained on MUSDB-HQ + an internal Meta set; the repo ships them under the same MIT license. Generally treated as commercially usable.
- **Beat This! (CPJKU/beat_this)** — code and published weights MIT; README warns some training data is copyrighted/CC-limited and "it is up to the user to assess".
- **Verovio** — LGPL-3.0 (used unmodified as an npm dependency). **SoundTouchJS** — LGPL-2.1 (same). Both OK for a web app as long as they stay replaceable/unmodified; noted for later.

## Calls

- Branch: work on `autonomous/testable-mvp` as instructed (the session default was a `claude/...` branch; the explicit instruction wins).
- Pipeline lives in a new top-level `drumscript/` package with no web dependencies, so the CLI, the eval and the Celery worker all call the same code.
- MusicXML is written by a small hand-rolled writer instead of music21: percussion needs exact control of display positions, x noteheads, tuplets and beams, and measures must line up 1:1 with the bar grid for the cursor. music21 dropped from the stack.
- Notation is single-voice, stems up (kick included in the chords). Simpler to read at this accuracy level than two voices; revisit with editing.
- One time signature per song (mode of the beats-per-downbeat count), every beat = a quarter note. 6/8 comes out as 3/4 or as triplets in 4/4. Good enough for v1.
- Each beat is notated as 16ths or 8th-triplets (chosen per bar, a beat can override with strong evidence). 32nds, sextuplets and flams collapse to the nearest slot. `time_s` in hits.json is never altered by this.
- Tracked beats are nudged (±35 ms) onto the drum hits played on them before building the grid: Beat This! runs at 20 ms resolution, and notation should follow the drummer's pulse.
- The grid is extended with extrapolated beats so every hit sits in a full bar; bar 1 can therefore start slightly before 0 s. No pickup measures.
- Velocity: ADTOF predicts none, so it is estimated from the RMS of the drum stem in the 50 ms after each onset, scaled per class. Coarse (and wrong when two drums hit together).
- MIDI keeps performed timing against a per-beat tempo map (bar 1 of the MIDI = bar 1 of the chart); `--midi-quantized` snaps to the notated grid.
- Player audio is stored as FLAC (`mix.flac`, `drums.flac`): sample-exact alignment between the two and with hit times (mp3/aac add encoder delay), and it decodes in every current browser.
- Demucs weights: Meta's CDN (`dl.fbaipublicfiles.com`) served an expired TLS certificate from the build sandbox, so `separate.py` falls back to a byte-identical Hugging Face copy and verifies the sha256 (`8726e21a…`, the hash embedded in the official filename). Official URL is still tried first.
- Demucs runs with `shifts=0`, `overlap=0.25` (fastest setting); quality is fine for transcription, slightly rougher for listening.
- madmom is supported as a beat fallback only if it happens to be installed (it does not build cleanly on modern Python); librosa is the always-available last resort.
- ADTOF is called through its model + filterbank classes directly (in-memory audio) rather than its file-based helper; peak picking and thresholds are the package defaults.
- Eval fixtures are generated in code (grooves with fills, 16th hats, a shuffle, a tempo-drift song) and rendered with FluidSynth + FluidR3_GM. The mp3s are committed (2.6 MB) so tests and the first manual upload need no extra tools.
- Pooled F1 = micro-average over all classes (sum of TP/FP/FN), one-to-one matching within ±50 ms via mir_eval.
- Backend: `app.models` was missing from git (a blanket `models/` ignore rule), so the API could never start from a clone. Rebuilt as a single `app/models.py`; ignore rules for `models/` and `lib/` are now anchored (the `lib/` rule was also hiding `frontend/src/lib`).
- Dropped the `backend_worker` hop (it only forwarded the task), the S3 paths, the MuseScore/PDF exports and the demo-user table: none are needed for the test loop and each was a way for `docker compose up` to fail. Results are files on a shared volume; Postgres holds only job rows and a small summary.
- Tables come from SQLAlchemy `create_all` (job status is a plain string); `database/init.sql` with its PG enums duplicated the models and is removed.
- Job status in the UI is polled once a second; the Redis-pub/sub websocket endpoint is kept but unused by the frontend.
- No automatic Celery retry: a failed transcription fails once with a readable message instead of re-running Demucs three times.
- Worker runs `--pool=solo` (one job at a time, PyTorch uses all cores) and preloads/warms all three models at startup.
- Progress during separation is a time-based estimate (Demucs 4.0.1 has no progress callback); it only reaches the next stage when separation really finishes.
- Dependencies in both images are pinned to the exact versions that were run here (first attempt with older Celery/redis-py pins crashed the worker on a kombu version check).
- Frontend: removed axios, react-query, react-dropzone, react-hook-form and VexFlow (unused after the rewrite); routing is a 20-line hash router so a job URL survives reload.
- Verovio renders the whole chart as one tall page that re-flows to the window width; the cursor is interpolated between note positions taken from Verovio's timemap (`qstamp`), and quarter positions are mapped to audio time through the beats in hits.json, so the cursor follows tempo drift.
- Player reads mix and drums from one shared position instead of running two players: toggling just switches which buffer is read, so they cannot drift.
- Click track is synthesised after the time-stretcher at the detected beat times (not mixed in before it), so it stays sharp at 50 %.
- Count-in plays when Play is pressed with a loop set, not on every repeat (repeats are seamless).
- **Time-stretch: neither Rubber Band nor SoundTouchJS in the end.** SoundTouchJS was integrated first and measured: at 50 % it turned 76 drum onsets into 185 with its default settings (104 with the best stable settings), and many parameter combinations output NaN (silence), which is sample-rate dependent and therefore a gamble on other machines. Rubber Band's WASM builds are GPL and its real-time mode does not give the exact source-position mapping the cursor and click rely on. Replaced with ~150 lines in `frontend/src/lib/stretch.ts`: cut at the known hit times, copy each attack 1:1, WSOLA only the tails. Measured: no NaNs at 44.1/48 kHz, exact length, every strong hit in the test window found at 50 % (18/18 and 21/21 on two fixtures, vs 15/18 with SoundTouchJS). Trade-off: sustained instruments are grainy when slowed (see TESTING.md).
- Stretcher grain settings (80 ms grain, 20 ms cross-fade, ±15 ms search) were picked from a small tone-purity test and then left alone.
- ADTOF is fed the Demucs drum stem, not the mix: 0.838 vs 0.792 pooled F1 on MDB Drums.
- ENST-Drums skipped: openly downloadable but 9.6 GB at ~1 MB/s with not enough disk in the sandbox. MDB Drums (23 real tracks) is the real-music benchmark instead.
- Upload limit 100 MB / 12 minutes; accepted types mp3, wav, m4a, flac (ffmpeg decodes them all; the brief only required mp3/wav).
- `tests/e2e` scripts are kept as plain Node files run by hand rather than wired into a test runner: they need the Compose stack up.
