# DrumScript

Upload a song, get the drum part back as notation you can read in the browser, play along with, and download.

```
mp3 / wav ─► Demucs (htdemucs) ─► ADTOF drum transcription ─► Beat This! beats + downbeats ─► bar grid
                                                                        │
                                                     hits.json  (source of truth)
                                                     ├─► MusicXML  ─► Verovio chart with moving cursor
                                                     └─► MIDI
```

## Run it

```bash
docker compose up --build        # then open http://localhost:3000
```

CPU only, no accounts, no API keys. **[TESTING.md](TESTING.md)** has the step-by-step test script, what to expect, accuracy numbers and known weak spots.

## What's where

| Path | What |
|---|---|
| `drumscript/` | The pipeline as a plain Python package. `transcribe <audio>` → `hits.json`, `score.musicxml`, `score.mid`. |
| `eval/` | Test-song generator (`make_fixture.py`), scorer (`score.py`), committed fixtures and results. |
| `backend/` | FastAPI: upload → job row (Postgres) → Celery task (Redis) → status → result files on a shared volume. |
| `ml_worker/` | Celery worker that runs `drumscript.pipeline` and reports progress. |
| `frontend/` | React + TypeScript + Tailwind. Verovio renders the chart; `src/lib/player.ts` is the synced mix/drums player (speed, loop, count-in, click). |
| `tests/` | `pytest` unit tests; `tests/e2e/` browser checks. |

## Project notes

- [PLAN.md](PLAN.md) — audit of the old repo and the milestone plan.
- [DECISIONS.md](DECISIONS.md) — every judgment call, including **model licenses** (ADTOF is non-commercial).
- [PROGRESS.md](PROGRESS.md) — status and the NEEDS BUFORD list.
- `docs/`, `DEPLOYMENT.md`, `CHANGELOG.md` describe the earlier placeholder version and are out of date.

Out of scope for now: note editing, review queue, auth, billing, YouTube input, a 7-class model, deployment.
