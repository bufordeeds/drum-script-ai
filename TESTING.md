# TESTING — DrumScript testable MVP

Everything below was run on this branch (`autonomous/testable-mvp`) from a fresh `git clone`, CPU only (4 cores, 16 GB).

## 1. Start it

Needs Docker with Compose v2, ~4 GB of disk for images, and internet on first run.

```bash
git clone <repo> && cd drum-script-ai && git checkout autonomous/testable-mvp
docker compose up --build
```

- First build: **~6–7 minutes** (the worker image is 2.8 GB — CPU PyTorch + Demucs).
- On first start the worker downloads the models (~250 MB, kept in the `model_cache` volume) and logs
  `Models loaded` then `celery@… ready.` About 35 s here. Jobs uploaded before that simply wait in the queue.
- Open **http://localhost:3000**. (API docs: http://localhost:8000/docs.)

No `.env` is needed. To reset everything: `docker compose down -v`.

## 2. Walk through it

Start with a file whose right answer is known — `eval/fixtures/rock_drift.mp3` (38 s, tempo creeps from 104 to ~124 BPM,
one bar of bass/keys before the drums enter) — then try your own mp3.

| Step | Do | Expect |
|---|---|---|
| Upload | Drop the mp3 on the upload page (or "Choose a file") | Upload bar, then the job page. URL becomes `#/job/<id>` and survives a reload. |
| Processing | Watch | Stages in order: reading audio → **isolating drums** (longest; the % during this stage is a time estimate) → detecting hits → beats/bar lines → writing chart. `rock_drift.mp3`: ~25 s. A 4:20 song: ~2 min 10 s. Rule of thumb on 4 cores: **half the song's length**. |
| Chart | — | Percussion-clef chart, bar numbers on every bar, tempo mark. For `rock_drift`: 15 bars of 4/4, bar 1 empty (no drums yet), crash on the first beat of bar 2, 8th-note hats with kick/snare, tom fills in bars 5, 9, 13. Header line shows `4/4 · ~113 BPM · 15 bars · 175 hits`. |
| Play | ▶ Play or **Space** | Audio starts; a red cursor moves through the bar and the page follows it system by system. Time and bar number tick in the transport. |
| Mix / drums | Click "Drums only" while playing | Switches to the isolated drum stem at the same position (no restart, no drift). "Full mix" switches back. |
| Speed | Drag the slider (50–100 %, 5 % steps) | Slower, **same pitch**. Cursor and click slow down with it. |
| Click | Tick "Click" | A click on every detected beat, higher pitch on beat 1. On `rock_drift` it speeds up with the song (it follows the detected beats, not a fixed BPM). |
| Jump | Click any bar, or ← / → | Playback jumps to the start of that bar. |
| Loop | Drag across bars on the chart, **or** shift-click a second bar, **or** type bar numbers into "Loop bars" | Bars get a yellow band and playback repeats them seamlessly. "Clear" (or clicking a bar outside the loop) removes it. |
| Count-in | With a loop set and "1-bar count-in" ticked, press Play | One bar of clicks at the loop's tempo (scaled by the speed slider), then the loop starts. The count-in happens on Play, not on every repeat. |
| Downloads | "Download MusicXML", "Download MIDI", "hits.json" | `<song name>.musicxml` (opens in MuseScore/Sibelius/etc.), `<song name>.mid` (drums on channel 10, tempo map follows the song), and the raw hit list. |

Errors to try: a `.txt` renamed to `.mp3` → "Processing failed: Could not decode audio"; a `.pdf` → rejected on the upload page.

## 3. Without the web stack (M1)

```bash
python3.11 -m venv .venv && . .venv/bin/activate
pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r ml_worker/requirements.txt mir_eval pytest && pip install --no-deps -e .
# needs ffmpeg on PATH

transcribe eval/fixtures/rock_120.mp3 -o out/        # -> out/hits.json, score.musicxml, score.mid (+ mix.flac, drums.flac)
transcribe out/hits.json                             # re-derive MusicXML + MIDI after editing hits.json by hand
pytest                                               # 11 fast unit tests for the grid / MusicXML / MIDI layer
```

## 4. Accuracy (M2)

`python eval/score.py` — onset F-measure, ±50 ms, one-to-one matching (mir_eval). "Pooled" = all classes' hits summed.
Classes are ADTOF's five: kick, snare, tom (all toms), hi-hat (open + closed), cymbal (crash + ride).

**Synthetic fixtures** — 4 songs, 695 hits, FluidSynth GM kit + bass + electric piano (`eval/make_fixture.py`):

| drum | ref | est | TP | P | R | F1 |
|---|---|---|---|---|---|---|
| kick | 123 | 123 | 123 | 1.000 | 1.000 | 1.000 |
| snare | 106 | 105 | 105 | 1.000 | 0.991 | 0.995 |
| tom | 48 | 48 | 48 | 1.000 | 1.000 | 1.000 |
| hi-hat | 329 | 316 | 314 | 0.994 | 0.954 | 0.974 |
| cymbal | 89 | 86 | 86 | 1.000 | 0.966 | 0.983 |
| **pooled** | 695 | 678 | 676 | 0.997 | 0.973 | **0.985** |

This is the easy case (clean samples, sparse mix). It proves the plumbing, not real-world accuracy.

**MDB Drums** — 23 real tracks, full mixes, 7 924 annotated hits (`python eval/score.py --mdb "<clone of github.com/CarlSouthall/MDBDrums>/MDB Drums"`):

| drum | ref | est | TP | P | R | F1 |
|---|---|---|---|---|---|---|
| kick | 1539 | 1550 | 1431 | 0.923 | 0.930 | 0.927 |
| snare | 2654 | 1956 | 1763 | 0.901 | 0.664 | 0.765 |
| tom | 90 | 102 | 42 | 0.412 | 0.467 | 0.437 |
| hi-hat | 2639 | 2646 | 2270 | 0.858 | 0.860 | 0.859 |
| cymbal | 1002 | 1059 | 875 | 0.826 | 0.873 | 0.849 |
| **pooled** | 7924 | 7313 | 6381 | 0.873 | 0.805 | **0.838** |

- **Where we land vs. Paradiddle's claimed ~0.86 pooled: 0.838** on MDB Drums. Not apples to apples (their test set and class list are not public), but the same ballpark.
- By genre it is lopsided: rock/pop/funk/metal tracks score 0.86–1.00; the jazz tracks (brushes, ghost notes, ride patterns) score 0.52–0.80 and pull the average down. Snare recall (0.66) is the biggest single loss — mostly ghost notes and brushes.
- Demucs earns its keep: the same model on the un-separated mix scores **0.792** pooled (`--no-separation`).
- Hit timing vs. ground truth on the fixtures: mean −3 ms, 90 % within −9…+4 ms.
- **ENST-Drums**: it is openly downloadable now (Zenodo record 21506051, CC BY-NC-ND), but it is a single 9.6 GB `.tar.zst`; the build sandbox was getting ~1 MB/s and had less free disk than the unpacked set needs, so it is **not in the eval**. `eval/score.py` has no ENST loader yet.

Raw numbers: `eval/results/*.json`.

## 5. What was checked automatically, and how

- `pytest` — grid, quantization, MusicXML structure (every measure full, beams/tuplets balanced), MIDI tempo map.
- `tests/e2e/ui.cjs` (Playwright, headless Chromium, against the Compose stack built from a clean clone with fresh volumes): upload → stages → chart rendered → cursor advances at 1.00× then 0.50× song-seconds per second → drums toggle keeps position → click track emits beats → loop 3–4 with count-in stays in bars 3–4 → bar click seeks → drag sets a loop → both downloads arrive. Run on three fixtures, one real MDB track and a 4 min 22 s file (117 bars).
- `tests/e2e/engine.cjs` — pulls samples straight out of the player: 100 % speed is bit-identical to the source for mix and drums; loop wrap is sample-exact; at 50 % and 75 % the output is exactly 1/speed long with unchanged pitch and all 18/18 strong drum hits in the test window land once, where expected; click positions are within 0.03 ms of the beat times at 100 % and 50 %; the count-in lasts exactly one bar and the music starts on the loop's first sample.

**Not checked:** nobody has *listened* to it. Audio was verified numerically in a headless browser with no sound device. Firefox and Safari were not run. In the build sandbox the Docker base images had the sandbox's TLS-inspection CA added so `pip`/`npm` could reach the network; the Dockerfiles and compose file in the repo were used unchanged.

## 6. Known weak spots

1. **Toms and anything subtle.** Five classes only: all toms are one line, crash and ride are one "cymbal", open/closed hi-hat are not distinguished. Tom F1 on real music is 0.44, ghost notes and brushes are mostly missed, and there are no flams, drags, rolls or dynamics marks. Velocity is a loudness guess.
2. **Notation is a readable sketch, not an engraving.** One time signature for the whole song, every beat a quarter note (6/8 shows up as triplets or 3/4), each beat is either 16ths or 8th-triplets (32nds and sextuplets snap to the nearest slot), single voice with all stems up, no repeats. If the beat tracker puts beat 1 in the wrong place or halves/doubles the tempo, the whole chart is shifted or re-barred — and there is no way to fix that in the UI yet.
3. **Slowed-down audio is practice-grade and unheard.** The stretcher protects detected drum hits but stretches everything between them with plain overlap-add: sustained bass/vocals will sound grainy at 50–70 %, and a drum hit the model *missed* can smear or double. It runs on the main thread (ScriptProcessorNode), so a heavy page can glitch the audio.

Smaller things: bar 1 can begin slightly before 0:00 (grid is extrapolated back to cover early hits); the click is silent before the first tracked beat; the % shown while isolating drums is an estimate; whole decoded song is held in browser memory twice (mix + drums, ~200 MB for 5 minutes); one job at a time, a job interrupted by a worker restart stays "processing"; uploads are never cleaned up; no auth.
