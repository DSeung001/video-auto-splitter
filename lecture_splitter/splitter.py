from __future__ import annotations

from pathlib import Path

from lecture_splitter.ffmpeg import split_video, validate_media_file
from lecture_splitter.utils import LessonSegment, ensure_dir


def split_lessons(
    input_path: str,
    lessons: list[LessonSegment],
    output_dir: str,
    *,
    copy_mode: bool,
    verify_output_with_ffprobe: bool,
    verify_decode_with_ffmpeg: bool,
    min_valid_duration_sec: float,
) -> list[LessonSegment]:
    ensure_dir(output_dir)
    output_path = Path(output_dir)

    created: list[LessonSegment] = []
    for lesson in lessons:
        final_file = output_path / lesson.output_file
        temp_file = output_path / f".{final_file.stem}.tmp{final_file.suffix}"
        if temp_file.exists():
            temp_file.unlink()

        split_video(
            input_path=input_path,
            output_path=str(temp_file),
            start_sec=lesson.start_sec,
            end_sec=lesson.end_sec,
            copy_mode=copy_mode,
        )

        if verify_output_with_ffprobe:
            validate_media_file(
                str(temp_file),
                min_duration_sec=min_valid_duration_sec,
                verify_decode_with_ffmpeg=verify_decode_with_ffmpeg,
            )

        temp_file.replace(final_file)
        created.append(lesson)

    return created
