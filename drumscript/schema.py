"""The hit-list document (hits.json) and the drum vocabulary.

hits.json is the single source of truth for a transcription. MusicXML, MIDI and
the browser chart are all derived from it (see grid.py / musicxml.py / midi.py).

    {
      "schema_version": 1,
      "source":   {"filename", "duration_s", "sample_rate"},
      "models":   {"separation", "transcription", "beats"},
      "beats":      [t, ...]       # detected beat times, seconds (INPUT to the grid)
      "downbeats":  [t, ...]       # detected downbeat times, seconds (INPUT to the grid)
      "hits": [
        {"time_s", "drum", "velocity" (1-127), "confidence" (0-1),
         # derived by grid.apply_grid(), rewritten on every export:
         "bar" (1-based), "beat" (1-based float, quarter notes), "div" (3|4), "slot"}
      ],
      # derived from beats/downbeats by grid.apply_grid():
      "time_signature": [beats_per_bar, 4],
      "tempo_bpm": median tempo,
      "tempo_map": [{"time_s", "bar", "bpm"}, ...]   # one entry per bar
      "bars": [{"number", "start_s", "end_s", "beats": [t per beat]}]
    }
"""

SCHEMA_VERSION = 1

# Order matters: it is the order of ADTOF's 5 output classes.
DRUMS = ["kick", "snare", "tom", "hihat", "cymbal"]

# ADTOF label (MIDI pitch it emits) -> our class name
ADTOF_LABELS = {35: "kick", 38: "snare", 47: "tom", 42: "hihat", 49: "cymbal"}

# General MIDI percussion notes used for export
GM_NOTE = {"kick": 36, "snare": 38, "tom": 47, "hihat": 42, "cymbal": 49,
           # reserved for a future 7-class model
           "crash": 49, "ride": 51, "tom_high": 48, "tom_mid": 47, "tom_floor": 43}

# Staff position (as if treble clef) + notehead, standard drum-kit notation
NOTATION = {
    "kick":   {"step": "F", "octave": 4, "notehead": None, "name": "Kick"},
    "snare":  {"step": "C", "octave": 5, "notehead": None, "name": "Snare"},
    "tom":    {"step": "D", "octave": 5, "notehead": None, "name": "Tom"},
    "hihat":  {"step": "G", "octave": 5, "notehead": "x", "name": "Hi-Hat"},
    "cymbal": {"step": "A", "octave": 5, "notehead": "x", "name": "Cymbal"},
    "crash":  {"step": "A", "octave": 5, "notehead": "x", "name": "Crash"},
    "ride":   {"step": "F", "octave": 5, "notehead": "x", "name": "Ride"},
    "tom_high":  {"step": "E", "octave": 5, "notehead": None, "name": "High Tom"},
    "tom_mid":   {"step": "D", "octave": 5, "notehead": None, "name": "Mid Tom"},
    "tom_floor": {"step": "A", "octave": 4, "notehead": None, "name": "Floor Tom"},
}

# low -> high on the staff, used to order chord notes
STAFF_ORDER = ["kick", "tom_floor", "snare", "tom", "tom_mid", "tom_high", "ride", "hihat", "cymbal", "crash"]
