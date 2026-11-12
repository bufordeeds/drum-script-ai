"""Build synthetic test songs with known drum hits.

Each fixture is a programmatic drum groove (General MIDI kit) plus a bass line and
a synth/keys part, rendered with FluidSynth + a GM soundfont. The exact onset time
of every drum hit is written next to the audio as <name>.ref.json.

    python eval/make_fixture.py            # writes eval/fixtures/*.mp3 + *.ref.json

Needs: fluidsynth, ffmpeg, a GM soundfont (default /usr/share/sounds/sf2/FluidR3_GM.sf2,
override with --soundfont or $SOUNDFONT).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import tempfile
from pathlib import Path

import mido

HERE = Path(__file__).parent
PPQ = 480

# GM drum note -> evaluation class (5-class ADTOF vocabulary)
CLASS_OF = {35: "kick", 36: "kick", 38: "snare", 40: "snare", 37: "snare",
            42: "hihat", 44: "hihat", 46: "hihat",
            41: "tom", 43: "tom", 45: "tom", 47: "tom", 48: "tom", 50: "tom",
            49: "cymbal", 57: "cymbal", 51: "cymbal", 53: "cymbal", 55: "cymbal", 52: "cymbal"}

K, S, HH, OH, CR, RD, T1, T2, T3 = 36, 38, 42, 46, 49, 51, 50, 47, 43


def _bar_rock(bar: int, fill: bool) -> list[tuple[float, int, int]]:
    """8th-note hats, kick 1 & 3(+), snare 2 & 4. (beat, note, velocity)"""
    ev = []
    for i in range(8):
        ev.append((i * 0.5, HH, 95 if i % 2 == 0 else 70))
    ev += [(0, K, 110), (2, K, 105), (1, S, 110), (3, S, 112)]
    if bar % 2 == 1:
        ev.append((2.5, K, 95))
    if bar % 4 == 0:
        ev = [e for e in ev if not (e[0] == 0 and e[1] == HH)] + [(0, CR, 115)]
    if fill:
        ev = [e for e in ev if e[0] < 2]
        ev += [(2, S, 100), (2.25, S, 85), (2.5, T1, 100), (2.75, T1, 90),
               (3, T2, 105), (3.25, T2, 92), (3.5, T3, 108), (3.75, T3, 100)]
    return ev


def _bar_sixteenth(bar: int, fill: bool) -> list[tuple[float, int, int]]:
    """16th-note hats with an open hat, syncopated kick, ghosted snare."""
    ev = []
    for i in range(16):
        if i == 14:
            ev.append((i * 0.25, OH, 90))
        else:
            ev.append((i * 0.25, HH, 92 if i % 4 == 0 else (72 if i % 2 == 0 else 58)))
    ev += [(0, K, 112), (0.75, K, 90), (2, K, 105), (2.5, K, 98), (1, S, 112), (3, S, 114), (1.75, S, 45)]
    if bar % 4 == 0:
        ev.append((0, CR, 112))
    if fill:
        ev = [e for e in ev if e[0] < 3]
        ev += [(3, T1, 105), (3.25, T1, 95), (3.5, T2, 105), (3.75, T3, 108)]
    return ev


def _bar_shuffle(bar: int, fill: bool) -> list[tuple[float, int, int]]:
    """12/8-feel shuffle on the ride: triplet grid."""
    t = 1 / 3
    ev = []
    for b in range(4):
        ev.append((b, RD, 95))
        ev.append((b + 2 * t, RD, 75))
    ev += [(0, K, 110), (2, K, 108), (1 + 2 * t, K, 90), (1, S, 110), (3, S, 112)]
    if bar % 4 == 0:
        ev.append((0, CR, 112))
    if fill:
        ev = [e for e in ev if e[0] < 3]
        ev += [(3, S, 105), (3 + t, T1, 100), (3 + 2 * t, T3, 108)]
    return ev


SONGS = {
    # name: (bar function, bpm, bars, root notes per bar, tempo drift per bar in bpm)
    "rock_120":      (_bar_rock, 120, 12, [40, 40, 45, 43], 0.0),
    "sixteenth_96":  (_bar_sixteenth, 96, 10, [38, 41, 36, 43], 0.0),
    "shuffle_108":   (_bar_shuffle, 108, 10, [45, 45, 50, 52], 0.0),
    "rock_drift":    (_bar_rock, 104, 14, [43, 43, 48, 50], 1.5),   # speeds up 104 -> ~124 BPM
}


def build(name: str, seed: int = 7) -> tuple[mido.MidiFile, list[dict], list[float]]:
    """Returns (midi, reference hits, bar start times)."""
    fn, bpm, n_bars, roots, drift = SONGS[name]
    rng = random.Random(seed + sum(map(ord, name)))
    mid = mido.MidiFile(ticks_per_beat=PPQ)
    tempo_tr, drum_tr, bass_tr, keys_tr = (mido.MidiTrack() for _ in range(4))
    mid.tracks.extend([tempo_tr, drum_tr, bass_tr, keys_tr])

    lead_in = 1  # one bar of bass/keys only, so the song does not start on a hit at t=0
    total_bars = lead_in + n_bars
    bar_bpm = [bpm + drift * max(0, b - lead_in) for b in range(total_bars)]
    bar_len = [4 * 60.0 / x for x in bar_bpm]
    bar_start = [sum(bar_len[:b]) for b in range(total_bars + 1)]

    prev = 0
    for b in range(total_bars):
        tempo_tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bar_bpm[b]), time=b * 4 * PPQ - prev))
        prev = b * 4 * PPQ

    def sec(bar: int, beat: float, jitter_s: float = 0.0) -> float:
        return bar_start[bar] + beat * 60.0 / bar_bpm[bar] + jitter_s

    def tick(bar: int, beat: float, jitter_s: float = 0.0) -> int:
        return int(round((bar * 4 + beat + jitter_s * bar_bpm[bar] / 60.0) * PPQ))

    abs_events = {id(drum_tr): [], id(bass_tr): [], id(keys_tr): []}
    ref = []
    for b in range(lead_in, total_bars):
        k = b - lead_in
        fill = (k % 4 == 3)
        for beat, note, vel in fn(k, fill):
            j = rng.uniform(-0.006, 0.006)           # human-ish timing
            v = max(20, min(127, vel + rng.randint(-8, 8)))
            t = tick(b, beat, j)
            abs_events[id(drum_tr)].append((t, "note_on", 9, note, v))
            abs_events[id(drum_tr)].append((t + 40, "note_off", 9, note, 0))
            ref.append({"time_s": round(t / PPQ / 4 * 0 + _tick_to_sec(t, bar_start, bar_bpm), 4),
                        "drum": CLASS_OF[note], "note": note, "velocity": v})
    for b in range(total_bars):
        root = roots[(b // 2) % len(roots)]
        for i in range(8):                            # 8th-note bass
            t = tick(b, i * 0.5)
            n = root if i % 4 != 3 else root + 7
            abs_events[id(bass_tr)].append((t, "note_on", 0, n, 96))
            abs_events[id(bass_tr)].append((t + 200, "note_off", 0, n, 0))
        for n in (root + 24, root + 28 if root % 2 else root + 27, root + 31):   # sustained chord
            abs_events[id(keys_tr)].append((tick(b, 0), "note_on", 1, n, 70))
            abs_events[id(keys_tr)].append((tick(b, 3.9), "note_off", 1, n, 0))

    bass_tr.append(mido.Message("program_change", channel=0, program=33, time=0))   # fingered bass
    keys_tr.append(mido.Message("program_change", channel=1, program=4, time=0))    # electric piano
    for tr in (drum_tr, bass_tr, keys_tr):
        now = 0
        for t, kind, ch, note, vel in sorted(abs_events[id(tr)], key=lambda e: (e[0], e[1] == "note_on")):
            tr.append(mido.Message(kind, channel=ch, note=note, velocity=vel, time=max(0, t - now)))
            now = max(now, t)
    ref.sort(key=lambda h: h["time_s"])
    return mid, ref, bar_start[lead_in:]


def _tick_to_sec(t: int, bar_start: list[float], bar_bpm: list[float]) -> float:
    bar = min(t // (4 * PPQ), len(bar_bpm) - 1)
    return bar_start[bar] + (t - bar * 4 * PPQ) / PPQ * 60.0 / bar_bpm[bar]


def render(mid: mido.MidiFile, out: Path, soundfont: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        m, w = Path(tmp) / "x.mid", Path(tmp) / "x.wav"
        mid.save(str(m))
        subprocess.run(["fluidsynth", "-ni", "-g", "0.8", "-r", "44100", "-F", str(w), soundfont, str(m)],
                       check=True, capture_output=True)
        codec = ["-codec:a", "libmp3lame", "-q:a", "2"] if out.suffix == ".mp3" else []
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(w), *codec, str(out)], check=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(HERE / "fixtures"))
    p.add_argument("--soundfont", default=os.environ.get("SOUNDFONT", "/usr/share/sounds/sf2/FluidR3_GM.sf2"))
    p.add_argument("--format", default="mp3", choices=["mp3", "wav", "flac"])
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in SONGS:
        mid, ref, bars = build(name)
        audio = out / f"{name}.{a.format}"
        render(mid, audio, a.soundfont)
        (out / f"{name}.ref.json").write_text(json.dumps(
            {"audio": audio.name, "bpm": SONGS[name][1], "bar_starts_s": [round(b, 4) for b in bars], "hits": ref}, indent=1))
        mid.save(str(out / f"{name}.mid"))
        print(f"{audio}  ({len(ref)} hits)")


if __name__ == "__main__":
    main()
