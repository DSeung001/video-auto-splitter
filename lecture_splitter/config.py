from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AudioConfig:
    sample_rate: int
    window_sec: float
    hop_sec: float
    absolute_quiet_db: float
    absolute_margin_db: float
    relative_drop_db: float
    quiet_score_threshold: float
    merge_gap_sec: float


@dataclass(frozen=True)
class VideoConfig:
    sample_interval_sec: float
    static_diff_threshold: float
    static_score_threshold: float
    min_static_duration_sec: float


@dataclass(frozen=True)
class BreakDetectionConfig:
    min_break_duration_sec: float
    max_break_duration_sec: float
    min_lesson_duration_sec: float
    ignore_break_before_sec: float
    trim_margin_before_break_sec: float
    trim_margin_after_break_sec: float
    merge_break_gap_sec: float
    max_point_gap_sec: float


@dataclass(frozen=True)
class ScoringConfig:
    audio_weight: float
    video_weight: float
    break_score_threshold: float


@dataclass(frozen=True)
class SplitConfig:
    default_copy_mode: bool
    verify_output_with_ffprobe: bool
    verify_decode_with_ffmpeg: bool
    min_valid_duration_sec: float


@dataclass(frozen=True)
class AppConfig:
    audio: AudioConfig
    video: VideoConfig
    break_detection: BreakDetectionConfig
    scoring: ScoringConfig
    split: SplitConfig


DEFAULT_CONFIG: dict[str, Any] = {
    "audio": {
        "sample_rate": 16000,
        "window_sec": 2.0,
        "hop_sec": 1.0,
        "absolute_quiet_db": -38.0,
        "absolute_margin_db": 8.0,
        "relative_drop_db": 12.0,
        "quiet_score_threshold": 0.65,
        "merge_gap_sec": 20.0,
    },
    "video": {
        "sample_interval_sec": 2.0,
        "static_diff_threshold": 4.0,
        "static_score_threshold": 0.65,
        "min_static_duration_sec": 120.0,
    },
    "break_detection": {
        "min_break_duration_sec": 180.0,
        "max_break_duration_sec": 1800.0,
        "min_lesson_duration_sec": 900.0,
        "ignore_break_before_sec": 600.0,
        "trim_margin_before_break_sec": 5.0,
        "trim_margin_after_break_sec": 5.0,
        "merge_break_gap_sec": 20.0,
        "max_point_gap_sec": 3.0,
    },
    "scoring": {
        "audio_weight": 0.7,
        "video_weight": 0.3,
        "break_score_threshold": 0.65,
    },
    "split": {
        "default_copy_mode": False,
        "verify_output_with_ffprobe": True,
        "verify_decode_with_ffmpeg": True,
        "min_valid_duration_sec": 1.0,
    },
}

PRESET_OVERRIDES: dict[str, dict[str, Any]] = {
    "balanced": {},
    "sensitive": {
        "audio": {
            "absolute_quiet_db": -35.0,
            "relative_drop_db": 9.0,
            "quiet_score_threshold": 0.58,
        },
        "video": {
            "static_diff_threshold": 6.0,
            "static_score_threshold": 0.55,
        },
        "scoring": {
            "break_score_threshold": 0.58,
        },
        "break_detection": {
            "min_break_duration_sec": 120.0,
        },
    },
    "strict": {
        "audio": {
            "absolute_quiet_db": -42.0,
            "relative_drop_db": 14.0,
            "quiet_score_threshold": 0.72,
        },
        "video": {
            "static_diff_threshold": 3.0,
            "static_score_threshold": 0.72,
        },
        "scoring": {
            "break_score_threshold": 0.72,
        },
        "break_detection": {
            "min_break_duration_sec": 240.0,
        },
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        base_value = result.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            result[key] = _deep_merge(base_value, value)
        else:
            result[key] = value
    return result


def _build_config_object(loaded: dict[str, Any]) -> AppConfig:
    merged = _deep_merge(DEFAULT_CONFIG, loaded)
    return AppConfig(
        audio=AudioConfig(**merged["audio"]),
        video=VideoConfig(**merged["video"]),
        break_detection=BreakDetectionConfig(**merged["break_detection"]),
        scoring=ScoringConfig(**merged["scoring"]),
        split=SplitConfig(**merged["split"]),
    )


def load_config(path: str | None) -> AppConfig:
    if path is None:
        return _build_config_object({})

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Config root must be a mapping: {config_path}")

    return _build_config_object(loaded)


def write_config_template(path: str, *, preset: str = "balanced", overwrite: bool = False) -> Path:
    if preset not in PRESET_OVERRIDES:
        available = ", ".join(sorted(PRESET_OVERRIDES))
        raise ValueError(f"Unsupported preset '{preset}'. Available presets: {available}")

    output_path = Path(path)
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Config already exists: {output_path}. Use --force to overwrite.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _deep_merge(DEFAULT_CONFIG, PRESET_OVERRIDES[preset])
    output_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return output_path
