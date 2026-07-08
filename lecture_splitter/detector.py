from __future__ import annotations

from dataclasses import dataclass

from lecture_splitter.config import BreakDetectionConfig, ScoringConfig
from lecture_splitter.utils import AudioPoint, BreakCandidate, LessonSegment, VideoPoint, clamp


@dataclass(frozen=True)
class _CombinedPoint:
    time_sec: float
    audio_score: float
    video_score: float
    break_score: float


def _closest_video_score(audio_time: float, video_points: list[VideoPoint], video_index_hint: int) -> tuple[float, int]:
    if not video_points:
        return 0.0, 0

    index = max(0, min(video_index_hint, len(video_points) - 1))
    while index + 1 < len(video_points):
        current_delta = abs(video_points[index].time_sec - audio_time)
        next_delta = abs(video_points[index + 1].time_sec - audio_time)
        if next_delta <= current_delta:
            index += 1
        else:
            break
    return video_points[index].static_score, index


def _merge_breaks(candidates: list[BreakCandidate], merge_gap_sec: float) -> list[BreakCandidate]:
    if not candidates:
        return []

    merged = [candidates[0]]
    for item in candidates[1:]:
        prev = merged[-1]
        if item.start_sec - prev.end_sec <= merge_gap_sec:
            merged[-1] = BreakCandidate(
                start_sec=prev.start_sec,
                end_sec=max(prev.end_sec, item.end_sec),
                audio_score_avg=(prev.audio_score_avg + item.audio_score_avg) / 2.0,
                video_score_avg=(prev.video_score_avg + item.video_score_avg) / 2.0,
                break_score_avg=(prev.break_score_avg + item.break_score_avg) / 2.0,
                reason=f"{prev.reason}+merged",
            )
        else:
            merged.append(item)
    return merged


def detect_breaks(
    audio_points: list[AudioPoint],
    video_points: list[VideoPoint],
    config: BreakDetectionConfig,
    scoring: ScoringConfig,
) -> list[BreakCandidate]:
    if not audio_points:
        return []

    total_weight = scoring.audio_weight + scoring.video_weight
    if total_weight <= 0:
        raise ValueError("Audio/video weights must be positive.")

    combined: list[_CombinedPoint] = []
    video_index = 0
    for audio_point in audio_points:
        video_score, video_index = _closest_video_score(audio_point.time_sec, video_points, video_index)
        break_score = (
            scoring.audio_weight * audio_point.quiet_score + scoring.video_weight * video_score
        ) / total_weight
        combined.append(
            _CombinedPoint(
                time_sec=audio_point.time_sec,
                audio_score=audio_point.quiet_score,
                video_score=video_score,
                break_score=clamp(break_score),
            )
        )

    raw: list[BreakCandidate] = []
    current_start_index: int | None = None
    current_end_index = 0
    for idx, point in enumerate(combined):
        is_break_like = point.break_score >= scoring.break_score_threshold
        if is_break_like and current_start_index is None:
            current_start_index = idx
            current_end_index = idx
            continue
        if is_break_like and current_start_index is not None:
            if point.time_sec - combined[current_end_index].time_sec <= config.max_point_gap_sec:
                current_end_index = idx
            else:
                raw.append(_build_break_candidate(combined, current_start_index, current_end_index))
                current_start_index = idx
                current_end_index = idx
            continue
        if not is_break_like and current_start_index is not None:
            raw.append(_build_break_candidate(combined, current_start_index, current_end_index))
            current_start_index = None

    if current_start_index is not None:
        raw.append(_build_break_candidate(combined, current_start_index, current_end_index))

    filtered = []
    for candidate in raw:
        if candidate.start_sec < config.ignore_break_before_sec:
            continue
        if candidate.duration_sec < config.min_break_duration_sec:
            continue
        if candidate.duration_sec > config.max_break_duration_sec:
            continue
        filtered.append(candidate)

    return _merge_breaks(filtered, config.merge_break_gap_sec)


def _build_break_candidate(points: list[_CombinedPoint], start_index: int, end_index: int) -> BreakCandidate:
    selected = points[start_index : end_index + 1]
    audio_avg = sum(item.audio_score for item in selected) / len(selected)
    video_avg = sum(item.video_score for item in selected) / len(selected)
    break_avg = sum(item.break_score for item in selected) / len(selected)
    return BreakCandidate(
        start_sec=selected[0].time_sec,
        end_sec=selected[-1].time_sec,
        audio_score_avg=audio_avg,
        video_score_avg=video_avg,
        break_score_avg=break_avg,
        reason="score-threshold",
    )


def build_lesson_segments(
    video_duration_sec: float,
    breaks: list[BreakCandidate],
    config: BreakDetectionConfig,
) -> list[LessonSegment]:
    if video_duration_sec <= 0:
        raise ValueError(f"video_duration_sec must be positive: {video_duration_sec}")

    sorted_breaks = sorted(breaks, key=lambda b: b.start_sec)
    lessons: list[tuple[float, float]] = []
    cursor = 0.0

    for break_item in sorted_breaks:
        lesson_end = max(cursor, break_item.start_sec - config.trim_margin_before_break_sec)
        if lesson_end - cursor > 0.5:
            lessons.append((cursor, lesson_end))
        cursor = min(video_duration_sec, break_item.end_sec + config.trim_margin_after_break_sec)

    if video_duration_sec - cursor > 0.5:
        lessons.append((cursor, video_duration_sec))

    if not lessons:
        lessons = [(0.0, video_duration_sec)]

    merged: list[tuple[float, float]] = []
    for start, end in lessons:
        if not merged:
            merged.append((start, end))
            continue
        if end - start < config.min_lesson_duration_sec:
            prev_start, _ = merged[-1]
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))

    if len(merged) > 1:
        first_start, first_end = merged[0]
        if first_end - first_start < config.min_lesson_duration_sec:
            second_start, second_end = merged[1]
            merged[1] = (first_start, second_end)
            merged = merged[1:]

    results: list[LessonSegment] = []
    for idx, (start, end) in enumerate(merged, start=1):
        results.append(
            LessonSegment(
                index=idx,
                start_sec=max(0.0, start),
                end_sec=min(video_duration_sec, end),
                output_file=f"part{idx:02d}.mp4",
            )
        )
    return results

