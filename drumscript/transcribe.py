"""Drum hit detection with ADTOF (Frame_RNN, PyTorch port). 5 classes."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path

import numpy as np

from .schema import ADTOF_LABELS

MODEL_NAME = "adtof-pytorch frame_rnn (5-class)"
FPS = 100

_model = None


def _get_model():
    global _model
    if _model is None:
        from adtof_pytorch import (calculate_n_bins, create_frame_rnn_model,
                                   get_default_weights_path, load_pytorch_weights)

        model = create_frame_rnn_model(calculate_n_bins())
        model.eval()
        weights = get_default_weights_path()
        if not weights or not Path(weights).exists():
            raise RuntimeError("ADTOF weights not found in the adtof_pytorch package")
        with contextlib.redirect_stdout(io.StringIO()):  # the loader print()s
            model = load_pytorch_weights(model, weights, strict=False)
        _model = model
    return _model


def activations(audio: np.ndarray, sr: int = 44100) -> np.ndarray:
    """Run ADTOF on (channels, n) audio. Returns activations, shape (frames, 5), 100 fps."""
    import torch
    from adtof_pytorch.audio import create_adtof_processor

    if sr != 44100:
        raise ValueError("ADTOF expects 44.1 kHz audio")
    model = _get_model()
    proc = create_adtof_processor()
    mono = (audio.mean(0) if audio.ndim == 2 else audio).astype(np.float32)
    spec = proc.apply_filterbank(proc.compute_stft(mono)).T  # (frames, bins)
    x = torch.from_numpy(np.ascontiguousarray(spec[None, :, :, None])).float()
    with torch.no_grad():
        return model(x).cpu().numpy()[0]


def _velocities(audio: np.ndarray, sr: int, times: np.ndarray) -> np.ndarray:
    """Crude loudness-based velocity (ADTOF does not predict one): RMS of the 50 ms after each onset."""
    mono = audio.mean(0) if audio.ndim == 2 else audio
    win = int(0.05 * sr)
    rms = np.zeros(len(times), dtype=np.float32)
    for i, t in enumerate(times):
        a = max(0, int(t * sr) - int(0.005 * sr))
        seg = mono[a:a + win]
        rms[i] = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
    return rms


def detect_hits(audio: np.ndarray, sr: int = 44100, thresholds=None) -> list[dict]:
    """Return [{time_s, drum, velocity, confidence}] sorted by time."""
    from adtof_pytorch import FRAME_RNN_THRESHOLDS, LABELS_5, PeakPicker

    act = activations(audio, sr)
    picker = PeakPicker(thresholds=list(thresholds or FRAME_RNN_THRESHOLDS), fps=FPS)
    peaks = picker.pick(act[None], labels=LABELS_5)[0]

    hits = []
    for col, label in enumerate(LABELS_5):
        drum = ADTOF_LABELS[label]
        times = np.asarray(peaks[label], dtype=np.float64)
        if len(times) == 0:
            continue
        frames = np.clip(np.round(times * FPS).astype(int), 0, len(act) - 1)
        conf = act[frames, col]
        rms = _velocities(audio, sr, times)
        ref = np.percentile(rms, 95) + 1e-9  # per-class reference so each drum uses the full range
        vel = np.clip(np.round(127 * np.sqrt(np.clip(rms / ref, 0, 1))), 20, 127)
        for t, c, v in zip(times, conf, vel):
            hits.append({"time_s": round(float(t), 4), "drum": drum,
                         "velocity": int(v), "confidence": round(float(c), 3)})
    hits.sort(key=lambda h: (h["time_s"], h["drum"]))
    return hits
