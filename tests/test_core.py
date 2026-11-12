"""Fast unit tests for the derived-from-hits layer (no ML models needed)."""
import json
import xml.etree.ElementTree as ET

import mido
import pytest

from drumscript.grid import apply_grid, build_bars
from drumscript.midi import to_midi
from drumscript.musicxml import DIVISIONS, to_musicxml
from drumscript.pipeline import write_exports


def make_doc(bpm=120.0, bars=4, hits=None, start=1.0):
    beat = 60.0 / bpm
    beats = [round(start + i * beat, 4) for i in range(bars * 4)]
    return {"source": {"filename": "t.wav", "duration_s": start + bars * 4 * beat},
            "beats": beats, "downbeats": beats[::4], "hits": hits or []}


def hit(t, drum="snare"):
    return {"time_s": t, "drum": drum, "velocity": 100, "confidence": 0.9}


def test_bars_follow_downbeats():
    doc = apply_grid(make_doc(hits=[hit(1.0, "kick"), hit(1.5)]))
    assert doc["time_signature"] == [4, 4]
    assert doc["tempo_bpm"] == pytest.approx(120, abs=0.1)
    assert doc["bars"][0]["start_s"] == pytest.approx(1.0)
    assert [h["bar"] for h in doc["hits"]] == [1, 1]
    assert [h["beat"] for h in doc["hits"]] == [1.0, 2.0]


def test_grid_extends_back_to_cover_pickup_hits():
    doc = apply_grid(make_doc(hits=[hit(0.52, "kick"), hit(1.0)]))
    first = doc["bars"][0]
    assert first["start_s"] < 0.52
    # the detected downbeat at 1.0 s must still be a bar start
    assert any(abs(b["start_s"] - 1.0) < 1e-6 for b in doc["bars"])
    assert doc["hits"][0]["bar"] == 1 and doc["hits"][1]["bar"] == 2


def test_three_four_detected():
    beats = [i * 0.5 for i in range(24)]
    bars, per_bar = build_bars(beats, beats[::3], 12.0)
    assert per_bar == 3 and len(bars) == 8


def test_sixteenths_vs_triplets():
    s = 1.0
    straight = [hit(s + x * 0.125, "hihat") for x in range(4)]           # 16ths in beat 1
    trip = [hit(s + 0.5 + x * (0.5 / 3), "hihat") for x in range(3)]     # triplet in beat 2
    doc = apply_grid(make_doc(hits=straight + trip))
    assert [h["div"] for h in doc["hits"]] == [4] * 4 + [3] * 3
    assert [h["slot"] for h in doc["hits"]] == [0, 1, 2, 3, 0, 1, 2]


def test_late_hit_rolls_to_next_beat_and_time_is_untouched():
    doc = apply_grid(make_doc(hits=[hit(1.49)]))
    h = doc["hits"][0]
    assert (h["bar"], h["beat"], h["time_s"]) == (1, 2.0, 1.49)


def test_missing_beats_are_filled():
    beats = [0.0, 0.5, 1.0, 2.0, 2.5, 3.0, 3.5, 4.0]  # 1.5 missing
    bars, _ = build_bars(beats, [0.0, 2.0, 4.0], 4.0)
    assert bars[0]["beats"] == [0.0, 0.5, 1.0, 1.5]


def test_no_beats_falls_back_to_120():
    doc = apply_grid({"source": {"duration_s": 4.0}, "beats": [], "downbeats": [], "hits": [hit(0.5)]})
    assert doc["tempo_bpm"] == 120 and doc["hits"][0]["beat"] == 2.0


def _measure_durations(xml: str):
    root = ET.fromstring(xml.split("\n", 2)[2])
    for m in root.iter("measure"):
        yield sum(int(n.find("duration").text) for n in m.findall("note") if n.find("chord") is None)


def test_musicxml_every_measure_is_full():
    hits = [hit(1.0, "kick"), hit(1.0, "hihat"), hit(1.125, "hihat"), hit(1.375, "snare"),
            hit(1.5 + 0.5 / 3, "tom"), hit(1.5 + 1.0 / 3, "tom"), hit(2.25, "cymbal"), hit(5.9, "kick")]
    doc = apply_grid(make_doc(hits=hits))
    xml = to_musicxml(doc, "T & <Test>")
    assert list(_measure_durations(xml)) == [4 * DIVISIONS] * len(doc["bars"])
    root = ET.fromstring(xml.split("\n", 2)[2])
    assert root.find("work/work-title").text == "T & <Test>"
    assert root.find(".//clef/sign").text == "percussion"
    assert len(root.findall(".//time-modification")) >= 2
    assert {n.text for n in root.iter("notehead")} == {"x"}
    # beams are balanced
    kinds = [b.text for b in root.iter("beam")]
    assert kinds.count("begin") == kinds.count("end")


def test_midi_tempo_map_and_notes():
    doc = apply_grid(make_doc(bpm=100, hits=[hit(1.0, "kick"), hit(1.6, "snare")]))
    mid = to_midi(doc)
    tempos = [m.tempo for m in mid.tracks[0] if m.type == "set_tempo"]
    assert tempos[0] == pytest.approx(600000, abs=200)
    notes = [m for m in mid.tracks[1] if m.type == "note_on"]
    assert [n.note for n in notes] == [36, 38] and all(n.channel == 9 for n in notes)
    assert notes[1].time + 0 == pytest.approx(480 - 60, abs=3)  # one beat after the kick's note_off


def test_write_exports_rederives_from_edited_hits(tmp_path):
    doc = make_doc(hits=[hit(1.0, "kick")])
    write_exports(doc, tmp_path)
    saved = json.loads((tmp_path / "hits.json").read_text())
    saved["hits"].append(hit(2.0, "snare"))          # "edit" the source of truth
    write_exports(saved, tmp_path)
    assert (tmp_path / "score.musicxml").read_text().count("<unpitched>") == 2
    assert len([m for m in mido.MidiFile(tmp_path / "score.mid").tracks[1] if m.type == "note_on"]) == 2
