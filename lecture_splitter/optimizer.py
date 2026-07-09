"""Auto-tune audio thresholds from the input file's own loudness profile.

Fixed dB thresholds don't generalize well: some recordings have noisy
breaks (fans, hallway chatter, mic hiss) that sit well above "true"
silence, while others are near-silent during breaks. Instead of guessing a
single absolute dB cutoff, this module measures the input's actual loudness
distribution, splits it into a "quiet" (break-like) cluster and an "active"
(lecture/speech) cluster using Otsu's method, and derives config values from
the measured gap between the two clusters.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from lecture_splitter.audio_analyzer import extract_db_timeline
from lecture_splitter.config import AudioConfig
from lecture_splitter.utils import clamp


@dataclass(frozen=True)
class AudioOptimizationResult:
    config: AudioConfig
    quiet_mean_db: float
    active_mean_db: float
    threshold_db: float
    quiet_ratio: float
    sample_count: int


def _otsu_threshold(values: np.ndarray, bins: int = 256) -> float:
    """Find the dB value that best separates two loudness clusters.

    Standard Otsu's method (maximizing inter-class variance) applied to a
    1D histogram of dB values. Falls back to the median if the histogram is
    degenerate (e.g. a single unique value).
    """
    hist, bin_edges = np.histogram(values, bins=bins)
    hist = hist.astype(np.float64)
    total = hist.sum()
    if total <= 0:
        return float(np.median(values))

    centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    sum_all = float(np.sum(hist * centers))

    sum_bg = 0.0
    weight_bg = 0.0
    best_variance = -1.0
    best_threshold = float(np.median(values))

    for i in range(bins):
        weight_bg += hist[i]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg <= 0:
            break

        sum_bg += hist[i] * centers[i]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_all - sum_bg) / weight_fg
        between_variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if between_variance > best_variance:
            best_variance = between_variance
            best_threshold = float(centers[i])

    return best_threshold


def optimize_audio_config_from_db_values(db_values: np.ndarray, config: AudioConfig) -> AudioOptimizationResult:
    """Core optimization logic, operating on an already-extracted dB array.

    Separated from `optimize_audio_config` so it can be unit tested without
    needing ffmpeg/an actual media file.
    """
    if db_values.size == 0:
        raise RuntimeError("dB 값이 비어 있어 설정을 최적화할 수 없습니다.")

    threshold = _otsu_threshold(db_values)
    quiet_mask = db_values <= threshold
    active_mask = ~quiet_mask

    # Guard against a degenerate split (e.g. almost no break, or almost all
    # break) where one side of the Otsu split has too few samples to trust.
    if quiet_mask.sum() < 3 or active_mask.sum() < 3:
        quiet_mean = float(np.percentile(db_values, 10))
        active_mean = float(np.percentile(db_values, 70))
    else:
        quiet_mean = float(db_values[quiet_mask].mean())
        active_mean = float(db_values[active_mask].mean())

    gap = max(active_mean - quiet_mean, 1.0)
    quiet_ratio = float(quiet_mask.mean())

    # Breaks still carry ambient noise, so the absolute cutoff is placed a
    # bit above the quiet cluster's own average level (not at dead silence).
    # Margin/drop-off requirements are sized from the *measured* gap between
    # "quiet" and "speaking" loudness rather than fixed guesses.
    absolute_quiet_db = quiet_mean + gap * 0.25
    absolute_margin_db = max(gap * 0.5, 3.0)
    relative_drop_db = max(gap * 0.6, 4.0)

    # A wider separation between clusters means a more confident distinction
    # between break and lecture audio, so we can require a slightly higher
    # score before calling a stretch a break.
    confidence = clamp(gap / 20.0)
    quiet_score_threshold = 0.55 + 0.15 * confidence  # ranges 0.55 ~ 0.70

    optimized = replace(
        config,
        absolute_quiet_db=round(absolute_quiet_db, 2),
        absolute_margin_db=round(absolute_margin_db, 2),
        relative_drop_db=round(relative_drop_db, 2),
        quiet_score_threshold=round(quiet_score_threshold, 3),
    )

    return AudioOptimizationResult(
        config=optimized,
        quiet_mean_db=quiet_mean,
        active_mean_db=active_mean,
        threshold_db=threshold,
        quiet_ratio=quiet_ratio,
        sample_count=int(db_values.size),
    )


def optimize_audio_config(input_path: str, config: AudioConfig) -> AudioOptimizationResult:
    """Analyze `input_path`'s audio and return an auto-tuned AudioConfig."""
    timeline = extract_db_timeline(input_path, config)
    db_values = np.array([db for _, db in timeline], dtype=np.float64)
    return optimize_audio_config_from_db_values(db_values, config)
