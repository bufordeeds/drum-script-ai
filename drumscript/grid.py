"""Bar grid + quantization.

Turns detected beats/downbeats into a regular bar grid (one time signature for
the whole piece, every beat = one quarter note) and annotates each hit with its
notated position. Nothing is ever dropped or moved in time here: `time_s` stays
the truth, `bar/beat/div/slot` are derived and recomputed on every export.
"""
from __future__ import annotations

from collections import Counter

import numpy as np

SUBDIVISIONS = (4, 3)  # 16th notes, or 8th-note triplets, chosen per beat
_ROLLOVER = 0.875      # hits later than this fraction of a beat belong to the next beat


def _clean_beats(beats, duration: float) -> np.ndarray:
    b = np.unique(np.asarray(beats, dtype=float))
    b = b[np.isfinite(b)]
    if len(b) >= 2:
        keep = np.concatenate([[True], np.diff(b) > 0.1])  # drop double detections
        b = b[keep]
    if len(b) < 2:
        # No usable beat tracking: fall back to a 120 BPM grid so the rest still works.
        return np.arange(0.0, max(duration, 2.0) + 0.5, 0.5)
    # Fill holes where the tracker skipped beats (interval ~ a multiple of the median).
    med = float(np.median(np.diff(b)))
    out = [b[0]]
    for nxt in b[1:]:
        prev = out[-1]
        n = int(round((nxt - prev) / med))
        if n >= 2:
            step = (nxt - prev) / n
            out.extend([prev + step * i for i in range(1, n)])
        out.append(nxt)
    return np.asarray(out)


def _meter(beats: np.ndarray, downbeats) -> tuple[int, int]:
    """(beats_per_bar, phase) — phase = index of the first beat that is a downbeat."""
    d = np.asarray(downbeats, dtype=float)
    if len(d) == 0:
        return 4, 0
    idx = np.array([int(np.argmin(np.abs(beats - t))) for t in d])
    spans = [int(s) for s in np.diff(idx) if 2 <= s <= 7]
    per_bar = Counter(spans).most_common(1)[0][0] if spans else 4
    phase = Counter(int(i % per_bar) for i in idx).most_common(1)[0][0]
    return per_bar, phase


def build_bars(beats, downbeats, duration: float, first_hit: float | None = None,
               last_hit: float | None = None) -> tuple[list[dict], int]:
    """Regular bars covering every hit. Returns (bars, beats_per_bar)."""
    g = list(_clean_beats(beats, duration))
    per_bar, phase = _meter(np.asarray(g), downbeats)

    t_min = min(g[0], first_hit) if first_hit is not None else g[0]
    t_max = max(g[-1], last_hit if last_hit is not None else g[-1])
    head = g[1] - g[0]
    tail = g[-1] - g[-2]
    # extend backwards to cover the first hit, then to the start of that bar
    while g[0] > t_min + 1e-6 or phase % per_bar != 0:
        g.insert(0, g[0] - head)
        phase = (phase + 1) % per_bar
    # extend forwards past the last hit, then to the end of that bar
    while g[-1] <= t_max + tail * (1 - _ROLLOVER) or (len(g) - 1) % per_bar != 0:
        g.append(g[-1] + tail)

    bars = []
    for i in range((len(g) - 1) // per_bar):
        seg = g[i * per_bar:(i + 1) * per_bar + 1]
        bars.append({"number": i + 1, "start_s": round(seg[0], 4), "end_s": round(seg[-1], 4),
                     "beats": [round(x, 4) for x in seg[:-1]]})
    return bars, per_bar


def flat_beats(bars: list[dict]) -> np.ndarray:
    """All beat times of the grid plus the closing boundary of the last bar."""
    return np.asarray([b for bar in bars for b in bar["beats"]] + [bars[-1]["end_s"]])


def _cost(fracs: list[float], div: int) -> float:
    return sum(min(abs(f - j / div) for j in range(div + 1)) for f in fracs)


def _choose_divs(per_beat: dict[int, list[float]], per_bar: int) -> dict[int, int]:
    """Pick 16ths (4) or 8th-triplets (3) for every beat.

    Timing noise (10 ms model frames, 20 ms beat frames) makes a single beat's
    evidence weak, so the feel is decided per bar first and a beat only deviates
    from its bar when its own evidence is strong.
    """
    bar_cost: dict[int, list[float]] = {}
    for k, fr in per_beat.items():
        c = bar_cost.setdefault(k // per_bar, [0.0, 0.0])
        c[0] += _cost(fr, 4)
        c[1] += _cost(fr, 3)
    out = {}
    for k, fr in per_beat.items():
        c4, c3 = bar_cost[k // per_bar]
        feel = 3 if c3 < 0.6 * c4 else 4
        own4, own3 = _cost(fr, 4), _cost(fr, 3)
        n_off = sum(1 for f in fr if f > 0.1)
        if feel == 4 and own3 + 0.02 * n_off < 0.5 * own4:
            feel = 3
        elif feel == 3 and own4 + 0.02 * n_off < 0.5 * own3:
            feel = 4
        out[k] = feel
    return out


def snap_beats(beats, hits: list[dict], tol: float = 0.035) -> list[float]:
    """Nudge each tracked beat onto the drum hits played on it.

    The beat tracker works at 20 ms resolution on the full mix; for notation what
    matters is where hits sit relative to the pulse the drummer actually played.
    """
    ts = np.sort(np.asarray([h["time_s"] for h in hits if h.get("confidence", 1.0) >= 0.4], dtype=float))
    out = []
    for b in beats:
        lo, hi = np.searchsorted(ts, [b - tol, b + tol])
        out.append(float(ts[lo:hi].mean()) if hi > lo else float(b))
    return out


def apply_grid(doc: dict) -> dict:
    """Compute bars / tempo map from doc['beats'|'downbeats'] and annotate doc['hits'] in place."""
    hits = doc.get("hits", [])
    duration = float(doc.get("source", {}).get("duration_s", 0.0))
    times = [h["time_s"] for h in hits]
    bars, per_bar = build_bars(snap_beats(doc.get("beats", []), hits), doc.get("downbeats", []), duration,
                               min(times) if times else None, max(times) if times else None)
    g = flat_beats(bars)

    per_beat: dict[int, list[tuple[dict, float]]] = {}
    for h in hits:
        k = int(np.clip(np.searchsorted(g, h["time_s"], side="right") - 1, 0, len(g) - 2))
        frac = (h["time_s"] - g[k]) / (g[k + 1] - g[k])
        if frac >= _ROLLOVER and k < len(g) - 2:
            k, frac = k + 1, 0.0
        per_beat.setdefault(k, []).append((h, float(np.clip(frac, 0.0, 0.999))))

    divs = _choose_divs({k: [f for _, f in items] for k, items in per_beat.items()}, per_bar)
    for k, items in per_beat.items():
        div = divs[k]
        slots = [min(int(round(frac * div)), div - 1) for _, frac in items]
        if div == 3 and not any(slots):
            div = 4  # only on-the-beat hits: no tuplet needed
        for (h, _), slot in zip(items, slots):
            h["bar"] = k // per_bar + 1
            h["beat"] = round(1 + (k % per_bar) + slot / div, 4)
            h["div"] = div
            h["slot"] = slot

    doc["time_signature"] = [per_bar, 4]
    intervals = np.diff(g)
    doc["tempo_bpm"] = round(float(60.0 / np.median(intervals)), 2)
    doc["tempo_map"] = [{"time_s": b["start_s"], "bar": b["number"],
                         "bpm": round(60.0 * per_bar / (b["end_s"] - b["start_s"]), 2)} for b in bars]
    doc["bars"] = bars
    return doc
