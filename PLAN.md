# PLAN — DrumScript testable MVP

Written after auditing the repo at `f9e5366` (2025 state). Branch: `autonomous/testable-mvp`.

## Audit: what exists

| Area | State | Notes |
|---|---|---|
| `docker-compose.yml` | Structure OK, **does not work from a clean checkout** | 6 services (frontend, backend, backend_worker, ml_worker, postgres, redis). |
| `backend/` FastAPI | **Broken** | Imports `app.models` (`User`, `TranscriptionJob`), but `backend/app/models/` was never committed — `.gitignore` has a blanket `models/` rule. API cannot start from a clean clone. |
| Upload / job status / result endpoints | Reasonable shape, kept | Result payload was base64 blobs inside a Postgres JSONB column. |
| `backend_worker` (Celery, `backend` queue) | Works in principle, pointless | Only re-sends the task to the ML queue. Removed. |
| S3 service + export endpoints (PDF/MSCX/MSCZ via MuseScore) | Placeholder-grade, out of scope | Needs AWS creds / a MuseScore install in the image. Removed from the hot path. |
| `ml_worker/pipeline/transcription.py` | **Placeholder** | Demucs/ADTLib imports commented out. "Separation" = librosa HPSS; "transcription" = onset detection + spectral-centroid thresholds mapped to kick/snare/hat; tempo = one global `librosa.beat_track` number; MusicXML from music21 with hardcoded durations. `EnhancedTranscriptionPipeline` references models that are never installed. |
| `frontend/` React + Vite + Tailwind | Upload + status UI works against the API shape; **notation is a placeholder** ("VexFlow integration coming soon") | No player at all. |
| `database/init.sql` | Duplicates the (missing) ORM models, uses PG enums | Replaced by SQLAlchemy `create_all`. |
| Tests (`test_*.py` at root) | Ad-hoc scripts against a running stack | Replaced by `tests/` (pytest) + `eval/`. |
| `audio/*.logicx`, `worker_logs.txt` | Stray files | Left alone. |

Nothing in the ML path is real. The web scaffolding (FastAPI + Celery + Redis + Postgres + React/TS + Compose) is sound, so **the stack stays**; the pipeline is rebuilt as a standalone package and the web pieces are repaired around it.

## Target architecture

```
audio (mp3/wav/m4a)
  └─ ffmpeg → 44.1 kHz stereo
       ├─ Demucs htdemucs ──► drums stem ──► ADTOF (pytorch) ──► raw hits (time, class, confidence)
       └─ Beat This! ──► beats + downbeats                         │
                              └────────── bar grid ◄───────────────┘ quantize (16ths / 8th-triplets per beat)
                                             │
                                   hits.json  (SOURCE OF TRUTH)
                                   ├─► score.musicxml  (own writer, percussion clef)
                                   ├─► score.mid       (tempo map follows detected beats)
                                   └─► browser chart   (Verovio renders the MusicXML; cursor/click/loops use hits.json grid)
```

- `drumscript/` — pip-installable package, no web deps. CLI: `transcribe <audio>`.
- `eval/` — fixture synthesis + mir_eval scoring.
- `backend/` — FastAPI: upload → Postgres job row → Celery task on the `transcription` queue → status → result files on a shared volume.
- `ml_worker/` — Celery worker that calls `drumscript.pipeline.run`.
- `frontend/` — upload page with progress, chart page (Verovio + cursor), player (SoundTouchJS time-stretch, mix/drums toggle, loop, count-in, click).

`hits.json` schema (v1): see `drumscript/schema.py`. All browser timing (cursor, click, loop points) comes from its `beats` / `bars` arrays — never from the MusicXML's nominal tempo — so it follows tempo drift.

## Milestones

- **M1** Pipeline CLI → `hits.json`, `.musicxml`, `.mid` (+ `mix.flac`, `drums.flac` for the player).
- **M2** `eval/`: synthesized fixture (drum MIDI → audio + bass/synth), mir_eval onset F1 @50 ms per class; public datasets if downloadable without registration.
- **M3** Backend job queue: upload → job → status → stored results.
- **M4** Frontend: upload/progress, chart + cursor, synced player, speed, loop + count-in, click, downloads.
- **M5** `docker compose up` from clean checkout; `TESTING.md`.

Details of every judgment call are in `DECISIONS.md`; live status in `PROGRESS.md`.
