"""hits.json -> Standard MIDI file whose tempo map follows the detected beats.

Bar 1 of the MIDI file is bar 1 of the chart. By default notes keep their
performed timing (expressed against the per-beat tempo map, so they sit on the
DAW grid exactly as they sit against the detected beats); `quantized=True`
snaps them to the notated positions instead.
"""
from __future__ import annotations

from pathlib import Path

import mido
import numpy as np

from .grid import flat_beats
from .schema import GM_NOTE

PPQ = 480
NOTE_TICKS = 60


def to_midi(doc: dict, quantized: bool = False) -> mido.MidiFile:
    bars = doc["bars"]
    per_bar = doc["time_signature"][0]
    g = flat_beats(bars)

    mid = mido.MidiFile(ticks_per_beat=PPQ)
    meta = mido.MidiTrack()
    mid.tracks.append(meta)
    meta.append(mido.MetaMessage("track_name", name="Tempo", time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=per_bar, denominator=4, time=0))
    last = None
    pending = 0
    for k in range(len(g) - 1):
        tempo = int(np.clip(round((g[k + 1] - g[k]) * 1e6), 1, 0xFFFFFF))  # MIDI tempo is 24-bit
        if tempo != last:
            meta.append(mido.MetaMessage("set_tempo", tempo=tempo, time=pending))
            pending, last = 0, tempo
        pending += PPQ

    events = []  # (tick, order, message kwargs)
    for h in doc["hits"]:
        if h["drum"] not in GM_NOTE:
            continue
        if quantized and "bar" in h:
            tick = int(round(((h["bar"] - 1) * per_bar + (h["beat"] - 1)) * PPQ))
        else:
            k = int(np.clip(np.searchsorted(g, h["time_s"], side="right") - 1, 0, len(g) - 2))
            tick = int(round((k + (h["time_s"] - g[k]) / (g[k + 1] - g[k])) * PPQ))
        tick = max(0, tick)
        note = GM_NOTE[h["drum"]]
        events.append((tick, 1, "note_on", note, int(np.clip(h.get("velocity", 100), 1, 127))))
        events.append((tick + NOTE_TICKS, 0, "note_off", note, 0))
    events.sort(key=lambda e: (e[0], e[1]))

    drums = mido.MidiTrack()
    mid.tracks.append(drums)
    drums.append(mido.MetaMessage("track_name", name="Drums", time=0))
    now = 0
    for tick, _, kind, note, vel in events:
        drums.append(mido.Message(kind, channel=9, note=note, velocity=vel, time=tick - now))
        now = tick
    return mid


def write_midi(doc: dict, path: str | Path, quantized: bool = False) -> None:
    to_midi(doc, quantized).save(str(path))
