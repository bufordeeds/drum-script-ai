"""Score the pipeline against known answers with mir_eval (onset F-measure, 50 ms window).

    python eval/score.py                     # synthetic fixtures in eval/fixtures
    python eval/score.py --mdb /path/to/MDBDrums   # + MDB Drums (full mixes), if you have it
    python eval/score.py --no-separation     # ablation: ADTOF on the full mix, no Demucs

Prints a per-drum table and writes eval/results/<set>.json. "Pooled" = all classes'
true/false positives summed (micro average), the usual headline number for ADT.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import mir_eval
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

from drumscript.schema import DRUMS  # noqa: E402

WINDOW = 0.05

# MDB Drums "class" annotation labels -> 5 classes
MDB_CLASS = {"KD": "kick", "SD": "snare", "HH": "hihat", "TT": "tom", "CY": "cymbal"}


def counts(ref: np.ndarray, est: np.ndarray) -> tuple[int, int, int]:
    """(true positives, false positives, false negatives) with one-to-one matching."""
    if len(ref) == 0 or len(est) == 0:
        return 0, len(est), len(ref)
    tp = len(mir_eval.util.match_events(ref, est, WINDOW))
    return tp, len(est) - tp, len(ref) - tp


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def by_class(hits: list[dict]) -> dict[str, np.ndarray]:
    return {d: np.sort(np.array([h["time_s"] for h in hits if h["drum"] == d], dtype=float)) for d in DRUMS}


def table(title: str, totals: dict[str, list[int]]) -> dict:
    print(f"\n{title}")
    print(f"{'drum':<8}{'ref':>6}{'est':>6}{'TP':>6}{'P':>8}{'R':>8}{'F1':>8}")
    out = {}
    pooled = [0, 0, 0]
    for d in DRUMS:
        tp, fp, fn = totals[d]
        pooled = [pooled[0] + tp, pooled[1] + fp, pooled[2] + fn]
        p, r, f = prf(tp, fp, fn)
        out[d] = {"ref": tp + fn, "est": tp + fp, "tp": tp, "precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3)}
        print(f"{d:<8}{tp + fn:>6}{tp + fp:>6}{tp:>6}{p:>8.3f}{r:>8.3f}{f:>8.3f}")
    p, r, f = prf(*pooled)
    out["pooled"] = {"ref": pooled[0] + pooled[2], "est": pooled[0] + pooled[1], "tp": pooled[0],
                     "precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3)}
    print(f"{'POOLED':<8}{pooled[0] + pooled[2]:>6}{pooled[0] + pooled[1]:>6}{pooled[0]:>6}{p:>8.3f}{r:>8.3f}{f:>8.3f}")
    return out


def run_set(name: str, items: list[tuple[str, Path, list[dict]]], work: Path, separation: bool, force: bool) -> dict:
    from drumscript.pipeline import run

    totals = {d: [0, 0, 0] for d in DRUMS}
    per_track = {}
    for track, audio, ref_hits in items:
        out = work / name / track
        hits_file = out / "hits.json"
        if force or not hits_file.exists():
            t = time.time()
            run(audio, out, separation=separation)
            print(f"  transcribed {track} in {time.time() - t:.0f}s", file=sys.stderr)
        est = by_class(json.loads(hits_file.read_text())["hits"])
        ref = by_class(ref_hits)
        tt = [0, 0, 0]
        for d in DRUMS:
            c = counts(ref[d], est[d])
            totals[d] = [a + b for a, b in zip(totals[d], c)]
            tt = [a + b for a, b in zip(tt, c)]
        per_track[track] = round(prf(*tt)[2], 3)
    res = table(f"== {name}  ({len(items)} tracks, onset F1 @ {int(WINDOW * 1000)} ms, "
                f"{'Demucs drums stem' if separation else 'full mix, no separation'})", totals)
    print("per-track pooled F1: " + ", ".join(f"{k} {v:.3f}" for k, v in per_track.items()))
    res["per_track_pooled_f1"] = per_track
    return res


def fixtures() -> list[tuple[str, Path, list[dict]]]:
    items = []
    for ref in sorted((HERE / "fixtures").glob("*.ref.json")):
        data = json.loads(ref.read_text())
        items.append((ref.name.replace(".ref.json", ""), ref.parent / data["audio"], data["hits"]))
    return items


def mdb(root: Path) -> list[tuple[str, Path, list[dict]]]:
    items = []
    for ann in sorted((root / "annotations" / "class").glob("*_class.txt")):
        track = ann.name.replace("_class.txt", "")
        audio = root / "audio" / "full_mix" / f"{track}_MIX.wav"
        if not audio.exists():
            continue
        hits = []
        for line in ann.read_text().split("\n"):
            parts = line.split()
            if len(parts) >= 2 and parts[1] in MDB_CLASS:
                hits.append({"time_s": float(parts[0]), "drum": MDB_CLASS[parts[1]]})
        items.append((track, audio, hits))
    return items


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mdb", help="path to a checkout of github.com/CarlSouthall/MDBDrums (MDB Drums)")
    p.add_argument("--no-separation", action="store_true", help="feed the full mix to ADTOF (skip Demucs)")
    p.add_argument("--skip-fixtures", action="store_true")
    p.add_argument("--work", default=str(HERE / "work"), help="where transcriptions are cached")
    p.add_argument("--force", action="store_true", help="re-transcribe even if cached")
    a = p.parse_args()

    sep = not a.no_separation
    suffix = "" if sep else "_nosep"
    work = Path(a.work)
    results = {}
    if not a.skip_fixtures:
        results["synthetic" + suffix] = run_set("synthetic" + suffix, fixtures(), work, sep, a.force)
    if a.mdb:
        results["mdb_drums" + suffix] = run_set("mdb_drums" + suffix, mdb(Path(a.mdb)), work, sep, a.force)
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    for k, v in results.items():
        (out / f"{k}.json").write_text(json.dumps(v, indent=1))


if __name__ == "__main__":
    main()
