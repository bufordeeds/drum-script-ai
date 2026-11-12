# PROGRESS

## Done
- Step 0 — audit, PLAN.md.
- M1 — `transcribe <audio>` → hits.json + MusicXML + MIDI, no web stack needed.
- M2 — `eval/`: synthetic fixtures (pooled F1 0.985) and MDB Drums (pooled F1 0.838; 0.792 without Demucs). Tables in TESTING.md.
- M3 — upload → Celery job → status/progress → result files, verified through the running stack.
- M4 — upload page with progress; chart page with Verovio, moving cursor, mix/drums toggle, 50–100 % speed, bar loop with count-in, click, MusicXML/MIDI downloads. Verified in headless Chromium.
- M5 — `docker compose up --build` from a clean clone with empty volumes: built in ~6.5 min, worker ready in ~35 s, full browser test passed, including a 4 min 22 s song (processed in 2 min 11 s). TESTING.md written.

## In progress
- nothing

## Next (not started, out of this brief)
- Fix-up tools for the things the models get wrong: move the downbeat, halve/double tempo, delete/add a hit (hits.json is already the source of truth for this).
- ENST-Drums loader for `eval/score.py`.
- Move the player from ScriptProcessorNode to an AudioWorklet.

## Blockers
- none

## NEEDS BUFORD
1. **License call on ADTOF before anything commercial.** ADTOF is CC BY-NC-SA 4.0 (non-commercial); ADTOF-pytorch has no license file and its weights are converted from ADTOF's. Fine for testing. To charge money you need the authors' permission or a model trained on data you have rights to. Details in DECISIONS.md.
2. **Listen to it.** All audio checks were numeric, in a headless browser. Ten minutes with headphones on a real song at 100 %, 75 % and 50 %, mix and drums, click on, will tell you more about the player than my tests can — especially how the slowed-down full mix sounds.
3. **Try your own songs and tell me what breaks first.** The MDB Drums numbers say rock/pop is solid and jazz is not; your SAMA lesson material will show which weak spot matters most to you.
4. Check Firefox/Safari if you use them (only Chromium was run).
5. Meta's Demucs download host served an expired TLS certificate from the build sandbox, so the worker falls back to a checksum-verified Hugging Face copy. If the first job on your machine fails with "Could not download Demucs htdemucs weights", set `DRUMSCRIPT_DEMUCS_MIRROR` (see `.env.example`) and tell me.
