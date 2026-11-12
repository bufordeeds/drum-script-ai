"""hits.json -> MusicXML (percussion clef, single voice, stems up).

Written by hand rather than through music21: unpitched percussion needs exact
control over display positions, noteheads, tuplets and beams, and the measure
layout must line up 1:1 with the bar grid so the browser cursor can map
quarter-note positions back to audio time.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

from .schema import GM_NOTE, NOTATION, STAFF_ORDER

DIVISIONS = 12  # per quarter: 16th = 3, triplet 8th = 4

# (type, dots) for a duration in 16ths within a straight beat
_STRAIGHT = {1: ("16th", 0), 2: ("eighth", 0), 3: ("eighth", 1), 4: ("quarter", 0)}


def _inst_id(drum: str) -> str:
    return f"P1-I{GM_NOTE[drum] + 1}"


def _note(drums: list[str] | None, dur: int, typ: str, dots: int = 0, *, triplet: bool = False,
          beam: str | None = None, tuplet: str | None = None) -> str:
    """One rest (drums=None) or chord. Returns XML for all notes of the chord."""
    out = []
    tm = "<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>" if triplet else ""
    nt = f'<notations><tuplet type="{tuplet}" bracket="yes"/></notations>' if tuplet else ""
    if drums is None:
        out.append(f"<note><rest/><duration>{dur}</duration><voice>1</voice><type>{typ}</type>"
                   f"{'<dot/>' * dots}{tm}{nt}</note>")
        return "".join(out)
    ordered = sorted(drums, key=STAFF_ORDER.index)
    for i, d in enumerate(ordered):
        n = NOTATION[d]
        head = f"<notehead>{n['notehead']}</notehead>" if n["notehead"] else ""
        bm = f'<beam number="1">{beam}</beam>' if beam and i == 0 else ""
        out.append(
            "<note>" + ("<chord/>" if i else "") +
            f"<unpitched><display-step>{n['step']}</display-step><display-octave>{n['octave']}</display-octave></unpitched>"
            f"<duration>{dur}</duration><instrument id=\"{_inst_id(d)}\"/><voice>1</voice><type>{typ}</type>"
            f"{'<dot/>' * dots}{tm}<stem>up</stem>{head}{bm}{nt if i == 0 else ''}</note>")
    return "".join(out)


def _beat_xml(div: int, slots: dict[int, set[str]]) -> str:
    """XML for one quarter-note beat. slots: slot index -> drums."""
    if not slots:
        return _note(None, DIVISIONS, "quarter")
    unit = DIVISIONS // div
    onsets = sorted(slots)
    events: list[tuple[list[str] | None, int]] = []  # (drums | None, length in slots)
    if onsets[0] > 0:
        events.append((None, onsets[0]))
    for i, s in enumerate(onsets):
        end = onsets[i + 1] if i + 1 < len(onsets) else div
        events.append((sorted(slots[s]), end - s))

    parts = []
    n_notes = sum(1 for d, _ in events if d is not None)
    seen = 0
    if div == 3:
        # expand a 2-slot rest into two triplet-8th rests to keep the tuplet simple
        flat = []
        for d, ln in events:
            flat.extend([(None, 1)] * ln if d is None else [(d, ln)])
        for i, (d, ln) in enumerate(flat):
            tup = "start" if i == 0 else ("stop" if i == len(flat) - 1 else None)
            beam = None
            if d is not None:
                seen += 1
                if n_notes >= 2 and ln == 1:
                    beam = "begin" if seen == 1 else ("end" if seen == n_notes else "continue")
            parts.append(_note(d, ln * unit, "eighth" if ln == 1 else "quarter", triplet=True, beam=beam, tuplet=tup))
        return _fix_beams(parts)
    for d, ln in events:
        if d is None:
            if ln == 3:  # 8th rest + 16th rest reads better than a dotted rest
                parts.append(_note(None, 2 * unit, "eighth"))
                parts.append(_note(None, unit, "16th"))
            else:
                parts.append(_note(None, ln * unit, *_STRAIGHT[ln]))
            continue
        seen += 1
        typ, dots = _STRAIGHT[ln]
        beam = None
        if n_notes >= 2 and typ != "quarter":
            beam = "begin" if seen == 1 else ("end" if seen == n_notes else "continue")
        parts.append(_note(d, ln * unit, typ, dots, beam=beam))
    return "".join(parts)


def _fix_beams(parts: list[str]) -> str:
    """Triplet beats can mix beamable 8ths with a quarter; make begin/end tags consistent."""
    idx = [i for i, p in enumerate(parts) if '<beam number="1">' in p]
    if len(idx) < 2:
        return "".join(p.replace('<beam number="1">begin</beam>', "").replace('<beam number="1">continue</beam>', "")
                       .replace('<beam number="1">end</beam>', "") for p in parts)
    for n, i in enumerate(idx):
        want = "begin" if n == 0 else ("end" if n == len(idx) - 1 else "continue")
        for have in ("begin", "continue", "end"):
            parts[i] = parts[i].replace(f'<beam number="1">{have}</beam>', f'<beam number="1">{want}</beam>')
    return "".join(parts)


def to_musicxml(doc: dict, title: str | None = None) -> str:
    """Render a gridded doc (see grid.apply_grid) as a MusicXML string."""
    bars = doc["bars"]
    per_bar = doc["time_signature"][0]
    title = title or doc.get("source", {}).get("filename") or "Drum transcription"
    used = sorted({h["drum"] for h in doc["hits"]} or {"snare"}, key=STAFF_ORDER.index)

    # (bar, beat index) -> {"div", "slots": {slot: {drums}}}
    cells: dict[tuple[int, int], dict] = {}
    for h in doc["hits"]:
        if h["drum"] not in NOTATION or "bar" not in h:
            continue
        key = (h["bar"], int(h["beat"] - 1 + 1e-9))
        cell = cells.setdefault(key, {"div": h["div"], "slots": {}})
        cell["slots"].setdefault(h["slot"], set()).add(h["drum"])

    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">',
         '<score-partwise version="4.0">',
         f"<work><work-title>{escape(title)}</work-title></work>",
         "<identification><encoding><software>DrumScript</software></encoding></identification>",
         '<part-list><score-part id="P1"><part-name>Drums</part-name>']
    for d in used:
        x.append(f'<score-instrument id="{_inst_id(d)}"><instrument-name>{NOTATION[d]["name"]}</instrument-name></score-instrument>')
    for d in used:
        x.append(f'<midi-instrument id="{_inst_id(d)}"><midi-channel>10</midi-channel><midi-program>1</midi-program>'
                 f"<midi-unpitched>{GM_NOTE[d] + 1}</midi-unpitched></midi-instrument>")
    x.append('</score-part></part-list><part id="P1">')

    for bar in bars:
        n = bar["number"]
        x.append(f'<measure number="{n}">')
        if n == 1:
            bpm = int(round(doc.get("tempo_bpm", 120)))
            x.append(f"<attributes><divisions>{DIVISIONS}</divisions><key><fifths>0</fifths></key>"
                     f"<time><beats>{per_bar}</beats><beat-type>4</beat-type></time>"
                     "<clef><sign>percussion</sign><line>2</line></clef></attributes>"
                     '<direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit>'
                     f"<per-minute>{bpm}</per-minute></metronome></direction-type><sound tempo=\"{bpm}\"/></direction>")
        if not any((n, b) in cells for b in range(per_bar)):
            x.append(f'<note><rest measure="yes"/><duration>{DIVISIONS * per_bar}</duration><voice>1</voice></note>')
        else:
            for b in range(per_bar):
                cell = cells.get((n, b))
                x.append(_beat_xml(cell["div"], cell["slots"]) if cell else _beat_xml(4, {}))
        if n == len(bars):
            x.append('<barline location="right"><bar-style>light-heavy</bar-style></barline>')
        x.append("</measure>")
    x.append("</part></score-partwise>")
    return "\n".join(x) + "\n"
