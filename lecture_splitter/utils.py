from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Interval:
    start_sec: float
    end_sec: float

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


@dataclass(frozen=True)
class AudioPoint:
    time_sec: float
    db: float
    quiet_score: float


@dataclass(frozen=True)
class VideoPoint:
    time_sec: float
    diff: float
    static_score: float


@dataclass(frozen=True)
class BreakCandidate:
    start_sec: float
    end_sec: float
    audio_score_avg: float
    video_score_avg: float
    break_score_avg: float
    reason: str

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


@dataclass(frozen=True)
class LessonSegment:
    index: int
    start_sec: float
    end_sec: float
    output_file: str

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def sec_to_timestamp(total_sec: float) -> str:
    if total_sec < 0:
        total_sec = 0
    hours = int(total_sec // 3600)
    minutes = int((total_sec % 3600) // 60)
    seconds = int(total_sec % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target

