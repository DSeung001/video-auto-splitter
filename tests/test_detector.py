from __future__ import annotations

from lecture_splitter.config import BreakDetectionConfig, ScoringConfig
from lecture_splitter.detector import build_lesson_segments, detect_breaks
from lecture_splitter.utils import AudioPoint, VideoPoint


def test_detect_breaks_and_build_lessons() -> None:
    audio_points: list[AudioPoint] = []
    video_points: list[VideoPoint] = []

    for t in range(0, 2401, 10):
        is_break_window = 1000 <= t <= 1300
        audio_points.append(
            AudioPoint(
                time_sec=float(t),
                db=-50.0 if is_break_window else -25.0,
                quiet_score=0.95 if is_break_window else 0.10,
            )
        )
        video_points.append(
            VideoPoint(
                time_sec=float(t),
                diff=0.5 if is_break_window else 12.0,
                static_score=0.90 if is_break_window else 0.10,
            )
        )

    break_config = BreakDetectionConfig(
        min_break_duration_sec=120.0,
        max_break_duration_sec=1000.0,
        min_lesson_duration_sec=300.0,
        ignore_break_before_sec=0.0,
        trim_margin_before_break_sec=5.0,
        trim_margin_after_break_sec=5.0,
        merge_break_gap_sec=20.0,
        max_point_gap_sec=20.0,
    )
    scoring = ScoringConfig(audio_weight=0.7, video_weight=0.3, break_score_threshold=0.65)

    breaks = detect_breaks(audio_points, video_points, break_config, scoring)
    assert len(breaks) == 1
    assert breaks[0].start_sec <= 1010
    assert breaks[0].end_sec >= 1290

    lessons = build_lesson_segments(2400.0, breaks, break_config)
    assert len(lessons) == 2
    assert lessons[0].start_sec == 0.0
    assert lessons[0].end_sec < lessons[1].start_sec
    assert lessons[1].end_sec == 2400.0

