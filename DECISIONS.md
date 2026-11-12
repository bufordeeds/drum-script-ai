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
