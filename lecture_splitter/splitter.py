from __future__ import annotations

from pathlib import Path
from typing import Callable

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
    progress_callback: Callable[[str], None] | None = None,
) -> list[LessonSegment]:
    def _emit(message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)

    ensure_dir(output_dir)
    output_path = Path(output_dir)
    total_lessons = len(lessons)

    created: list[LessonSegment] = []
    is_webm_input = Path(input_path).suffix.lower() == ".webm"
    for lesson_idx, lesson in enumerate(lessons, start=1):
        final_file = output_path / lesson.output_file
        temp_file = output_path / f".{final_file.stem}.tmp{final_file.suffix}"
        if temp_file.exists():
            temp_file.unlink()

        _emit(f"Splitting lesson {lesson_idx}/{total_lessons}: {lesson.output_file}")
        try:
            _split_and_validate(
                input_path=input_path,
                temp_file=temp_file,
                start_sec=lesson.start_sec,
                end_sec=lesson.end_sec,
                copy_mode=copy_mode,
                verify_output_with_ffprobe=verify_output_with_ffprobe,
                verify_decode_with_ffmpeg=verify_decode_with_ffmpeg,
                min_valid_duration_sec=min_valid_duration_sec,
            )
        except Exception:
            if temp_file.exists():
                temp_file.unlink()
            if not (is_webm_input and copy_mode):
                raise

            _emit(f"Copy split failed for lesson {lesson_idx}; retrying with accurate mode")
            try:
                _split_and_validate(
                    input_path=input_path,
                    temp_file=temp_file,
                    start_sec=lesson.start_sec,
                    end_sec=lesson.end_sec,
                    copy_mode=False,
                    verify_output_with_ffprobe=verify_output_with_ffprobe,
                    verify_decode_with_ffmpeg=verify_decode_with_ffmpeg,
                    min_valid_duration_sec=min_valid_duration_sec,
                )
            except Exception:
                if temp_file.exists():
                    temp_file.unlink()
                raise

        temp_file.replace(final_file)
        created.append(lesson)
        progress_percent = int((lesson_idx / total_lessons) * 100) if total_lessons > 0 else 100
        _emit(f"Split progress: {progress_percent}% ({lesson_idx}/{total_lessons})")

    return created


def _split_and_validate(
    *,
    input_path: str,
    temp_file: Path,
    start_sec: float,
    end_sec: float,
    copy_mode: bool,
    verify_output_with_ffprobe: bool,
    verify_decode_with_ffmpeg: bool,
    min_valid_duration_sec: float,
) -> None:
    split_video(
        input_path=input_path,
        output_path=str(temp_file),
        start_sec=start_sec,
        end_sec=end_sec,
        copy_mode=copy_mode,
    )
    if verify_output_with_ffprobe:
        validate_media_file(
            str(temp_file),
            min_duration_sec=min_valid_duration_sec,
            verify_decode_with_ffmpeg=verify_decode_with_ffmpeg,
        )
