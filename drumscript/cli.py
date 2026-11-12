"""`transcribe <audio>` -> hits.json + score.musicxml + score.mid (+ mix/drums audio)."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="transcribe",
        description="Transcribe the drum part of an audio file to hits.json, MusicXML and MIDI. "
                    "Pass a hits.json instead of audio to re-export after editing it.")
    p.add_argument("input", help="audio file (mp3/wav/m4a/flac) or an existing hits.json")
    p.add_argument("-o", "--out", help="output directory (default: <input name>_transcription next to the input)")
    p.add_argument("--no-separation", action="store_true", help="skip Demucs (input is already drums only)")
    p.add_argument("--midi-quantized", action="store_true", help="snap MIDI notes to the notated grid")
    p.add_argument("--title", help="title printed on the chart")
    p.add_argument("-q", "--quiet", action="store_true")
    a = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING if a.quiet else logging.INFO, format="%(message)s", stream=sys.stderr)
    src = Path(a.input)
    if not src.exists():
        print(f"error: {src} does not exist", file=sys.stderr)
        return 2

    from .audio import AudioError
    from .pipeline import HITS_JSON, MIDI, MUSICXML, run, write_exports

    try:
        if src.suffix.lower() == ".json":
            out = Path(a.out) if a.out else src.parent
            doc = write_exports(json.loads(src.read_text()), out, title=a.title, midi_quantized=a.midi_quantized)
        else:
            out = Path(a.out) if a.out else src.with_name(src.stem + "_transcription")
            doc = run(src, out, separation=not a.no_separation, title=a.title, midi_quantized=a.midi_quantized)
    except AudioError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    counts = Counter(h["drum"] for h in doc["hits"])
    print(f"{len(doc['hits'])} hits in {len(doc['bars'])} bars, {doc['time_signature'][0]}/4 at ~{doc['tempo_bpm']} BPM"
          f"  ({', '.join(f'{k} {v}' for k, v in sorted(counts.items()))})")
    for name in (HITS_JSON, MUSICXML, MIDI):
        print(out / name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
