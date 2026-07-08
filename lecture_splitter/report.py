from __future__ import annotations

import csv
import json
from pathlib import Path

from lecture_splitter.utils import BreakCandidate, LessonSegment, sec_to_timestamp


def write_segments_csv(path: str, breaks: list[BreakCandidate], lessons: list[LessonSegment]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["type", "index", "start_sec", "end_sec", "duration_sec", "start_hms", "end_hms"])
        for idx, brk in enumerate(breaks, start=1):
            writer.writerow(
                [
                    "break",
                    idx,
                    f"{brk.start_sec:.3f}",
                    f"{brk.end_sec:.3f}",
                    f"{brk.duration_sec:.3f}",
                    sec_to_timestamp(brk.start_sec),
                    sec_to_timestamp(brk.end_sec),
                ]
            )
        for lesson in lessons:
            writer.writerow(
                [
                    "lesson",
                    lesson.index,
                    f"{lesson.start_sec:.3f}",
                    f"{lesson.end_sec:.3f}",
                    f"{lesson.duration_sec:.3f}",
                    sec_to_timestamp(lesson.start_sec),
                    sec_to_timestamp(lesson.end_sec),
                ]
            )


def write_segments_json(path: str, breaks: list[BreakCandidate], lessons: list[LessonSegment]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "breaks": [
            {
                "start_sec": b.start_sec,
                "end_sec": b.end_sec,
                "duration_sec": b.duration_sec,
                "audio_score_avg": b.audio_score_avg,
                "video_score_avg": b.video_score_avg,
                "break_score_avg": b.break_score_avg,
                "reason": b.reason,
            }
            for b in breaks
        ],
        "lessons": [
            {
                "index": l.index,
                "start_sec": l.start_sec,
                "end_sec": l.end_sec,
                "duration_sec": l.duration_sec,
                "output_file": l.output_file,
                "start_hms": sec_to_timestamp(l.start_sec),
                "end_hms": sec_to_timestamp(l.end_sec),
            }
            for l in lessons
        ],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

