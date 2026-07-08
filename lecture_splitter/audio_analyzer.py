from __future__ import annotations

import math
import tempfile
from pathlib import Path

import numpy as np

from lecture_splitter.config import AudioConfig
from lecture_splitter.ffmpeg import extract_audio_pcm
from lecture_splitter.utils import AudioPoint, Interval, clamp


def _rms_to_db(rms_value: float) -> float:
    if rms_value <= 1e-12:
        return -100.0
    return 20.0 * math.log10(rms_value)


def analyze_audio(input_path: str, config: AudioConfig) -> list[AudioPoint]:
    temp_pcm = tempfile.NamedTemporaryFile(prefix="lecture-splitter-", suffix=".pcm", delete=False)
    temp_pcm_path = Path(temp_pcm.name)
    temp_pcm.close()

    try:
        extract_audio_pcm(input_path, str(temp_pcm_path), sample_rate=config.sample_rate)
        pcm = np.fromfile(temp_pcm_path, dtype=np.int16)
        if pcm.size == 0:
            raise RuntimeError("Extracted PCM data is empty.")

        samples = pcm.astype(np.float32) / 32768.0
        window_samples = max(1, int(config.window_sec * config.sample_rate))
        hop_samples = max(1, int(config.hop_sec * config.sample_rate))

        points_raw: list[tuple[float, float]] = []
        for start in range(0, max(1, len(samples) - window_samples + 1), hop_samples):
            window = samples[start : start + window_samples]
            if window.size == 0:
                continue
            rms_value = float(np.sqrt(np.mean(window * window)))
            db_value = _rms_to_db(rms_value)
            time_sec = start / config.sample_rate
            points_raw.append((time_sec, db_value))

        if not points_raw:
            raise RuntimeError("Unable to build audio timeline points.")

        db_values = np.array([db for _, db in points_raw], dtype=np.float32)
        baseline_db = float(np.percentile(db_values, 70))

        analyzed: list[AudioPoint] = []
        for time_sec, db_value in points_raw:
            absolute_score = clamp(
                (config.absolute_quiet_db + config.absolute_margin_db - db_value) / max(config.absolute_margin_db, 1e-6)
            )
            relative_drop = baseline_db - db_value
            relative_score = clamp(relative_drop / max(config.relative_drop_db, 1e-6))
            quiet_score = max(absolute_score, relative_score)
            analyzed.append(AudioPoint(time_sec=time_sec, db=db_value, quiet_score=quiet_score))

        return analyzed
    finally:
        temp_pcm_path.unlink(missing_ok=True)


def detect_quiet_intervals(points: list[AudioPoint], config: AudioConfig) -> list[Interval]:
    if not points:
        return []

    intervals: list[Interval] = []
    start: float | None = None
    previous_time = points[0].time_sec

    for point in points:
        is_quiet = point.quiet_score >= config.quiet_score_threshold
        if is_quiet and start is None:
            start = point.time_sec
        if not is_quiet and start is not None:
            intervals.append(Interval(start_sec=start, end_sec=previous_time))
            start = None
        previous_time = point.time_sec

    if start is not None:
        intervals.append(Interval(start_sec=start, end_sec=previous_time))

    if not intervals:
        return []

    merged: list[Interval] = [intervals[0]]
    for interval in intervals[1:]:
        last = merged[-1]
        if interval.start_sec - last.end_sec <= config.merge_gap_sec:
            merged[-1] = Interval(start_sec=last.start_sec, end_sec=max(last.end_sec, interval.end_sec))
        else:
            merged.append(interval)
    return merged

