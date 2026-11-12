"""End-to-end pipeline: audio file -> out_dir/{hits.json, score.musicxml, score.mid, mix.flac, drums.flac}."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Callable

from . import __version__
from .audio import SAMPLE_RATE, AudioError, load_audio, write_audio
from .grid import apply_grid
from .midi import write_midi
from .musicxml import to_musicxml
from .schema import SCHEMA_VERSION

log = logging.getLogger(__name__)

MAX_DURATION_S = 12 * 60
MIN_DURATION_S = 2

HITS_JSON = "hits.json"
MUSICXML = "score.musicxml"
MIDI = "score.mid"
MIX_AUDIO = "mix.flac"
DRUMS_AUDIO = "drums.flac"

Progress = Callable[[str, int], None]


def write_exports(doc: dict, out_dir: str | Path, title: str | None = None, midi_quantized: bool = False) -> dict:
    """(Re)derive everything from the hit list. Call this after editing hits.json too."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    apply_grid(doc)
    (out / HITS_JSON).write_text(json.dumps(doc, indent=1))
    (out / MUSICXML).write_text(to_musicxml(doc, title), encoding="utf-8")
    write_midi(doc, out / MIDI, quantized=midi_quantized)
    return doc


def run(audio_path: str | Path, out_dir: str | Path, *, progress: Progress | None = None,
        separation: bool = True, title: str | None = None, midi_quantized: bool = False) -> dict:
    """Transcribe one file. `progress(stage, percent)` is called as stages start."""
    from . import beats as beats_mod
    from . import separate as sep_mod
    from . import transcribe as tr_mod

    def step(stage: str, pct: int) -> None:
        log.info("%3d%% %s", pct, stage)
        if progress:
            progress(stage, pct)

    audio_path, out = Path(audio_path), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    timings: dict[str, float] = {}
    t0 = time.time()

    step("decoding", 2)
    mix = load_audio(audio_path)
    duration = mix.shape[1] / SAMPLE_RATE
    if duration < MIN_DURATION_S:
        raise AudioError(f"Audio too short ({duration:.1f}s, minimum {MIN_DURATION_S}s)")
    if duration > MAX_DURATION_S:
        raise AudioError(f"Audio too long ({duration / 60:.1f} min, maximum {MAX_DURATION_S // 60} min)")
    write_audio(out / MIX_AUDIO, mix)
    timings["decode"] = time.time() - t0

    t = time.time()
    if separation:
        step("separating_drums", 8)
        drums = sep_mod.separate_drums(mix, SAMPLE_RATE)
    else:
        drums = mix
    write_audio(out / DRUMS_AUDIO, drums)
    timings["separation"] = time.time() - t

    t = time.time()
    step("transcribing", 65)
    hits = tr_mod.detect_hits(drums, SAMPLE_RATE)
    timings["transcription"] = time.time() - t

    t = time.time()
    step("tracking_beats", 78)
    beats, downbeats, beat_backend = beats_mod.track_beats(mix, SAMPLE_RATE)
    timings["beats"] = time.time() - t

    step("writing_notation", 92)
    doc = {
        "schema_version": SCHEMA_VERSION,
        "source": {"filename": audio_path.name, "duration_s": round(duration, 3), "sample_rate": SAMPLE_RATE},
        "models": {"pipeline": __version__,
                   "separation": sep_mod.MODEL_NAME if separation else None,
                   "transcription": tr_mod.MODEL_NAME, "beats": beat_backend},
        "beats": beats,
        "downbeats": downbeats,
        "hits": hits,
    }
    write_exports(doc, out, title=title or audio_path.stem, midi_quantized=midi_quantized)
    timings["total"] = time.time() - t0
    doc["timings_s"] = {k: round(v, 2) for k, v in timings.items()}
    (out / HITS_JSON).write_text(json.dumps(doc, indent=1))
    step("done", 100)
    return doc
