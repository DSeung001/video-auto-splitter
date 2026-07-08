from __future__ import annotations

import cv2
import numpy as np

from lecture_splitter.config import VideoConfig
from lecture_splitter.utils import Interval, VideoPoint, clamp


def analyze_video(input_path: str, config: VideoConfig) -> list[VideoPoint]:
    capture = cv2.VideoCapture(input_path)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video for analysis: {input_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    if fps <= 0 or frame_count <= 0:
        capture.release()
        raise RuntimeError(f"Unable to read FPS/frame count from video: {input_path}")

    duration_sec = frame_count / fps
    sample_interval = max(config.sample_interval_sec, 0.25)

    points: list[VideoPoint] = []
    prev_gray: np.ndarray | None = None
    cursor = 0.0
    while cursor < duration_sec:
        capture.set(cv2.CAP_PROP_POS_MSEC, cursor * 1000.0)
        ok, frame = capture.read()
        if not ok or frame is None:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_gray is None:
            diff_value = 0.0
        else:
            abs_diff = cv2.absdiff(gray, prev_gray)
            diff_value = float(np.mean(abs_diff))
        prev_gray = gray

        if diff_value <= config.static_diff_threshold:
            static_score = 1.0
        else:
            static_score = clamp(config.static_diff_threshold / max(diff_value, 1e-6))

        points.append(VideoPoint(time_sec=cursor, diff=diff_value, static_score=static_score))
        cursor += sample_interval

    capture.release()
    if not points:
        raise RuntimeError("Unable to generate video timeline points.")
    return points


def detect_static_intervals(points: list[VideoPoint], config: VideoConfig) -> list[Interval]:
    if not points:
        return []

    intervals: list[Interval] = []
    start: float | None = None
    previous_time = points[0].time_sec
    for point in points:
        is_static = point.static_score >= config.static_score_threshold
        if is_static and start is None:
            start = point.time_sec
        if not is_static and start is not None:
            intervals.append(Interval(start_sec=start, end_sec=previous_time))
            start = None
        previous_time = point.time_sec

    if start is not None:
        intervals.append(Interval(start_sec=start, end_sec=previous_time))

    return [i for i in intervals if i.duration_sec >= config.min_static_duration_sec]

