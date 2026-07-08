from __future__ import annotations

from pathlib import Path

from lecture_splitter.splitter import split_lessons
from lecture_splitter.utils import LessonSegment


def test_webm_copy_fallback_to_accurate(monkeypatch, tmp_path: Path) -> None:
    calls: list[bool] = []

    def fake_split_video(*, input_path: str, output_path: str, start_sec: float, end_sec: float, copy_mode: bool) -> None:
        calls.append(copy_mode)
        if copy_mode:
            raise RuntimeError("copy failed")
        Path(output_path).write_bytes(b"ok")

    def fake_validate_media_file(file_path: str, *, min_duration_sec: float, verify_decode_with_ffmpeg: bool) -> float:
        return 10.0

    monkeypatch.setattr("lecture_splitter.splitter.split_video", fake_split_video)
    monkeypatch.setattr("lecture_splitter.splitter.validate_media_file", fake_validate_media_file)

    lessons = [LessonSegment(index=1, start_sec=0.0, end_sec=10.0, output_file="part01.mp4")]
    created = split_lessons(
        input_path="input.webm",
        lessons=lessons,
        output_dir=str(tmp_path),
        copy_mode=True,
        verify_output_with_ffprobe=True,
        verify_decode_with_ffmpeg=False,
        min_valid_duration_sec=1.0,
    )

    assert len(created) == 1
    assert calls == [True, False]
    assert (tmp_path / "part01.mp4").exists()


def test_non_webm_copy_failure_raises(monkeypatch, tmp_path: Path) -> None:
    def fake_split_video(*, input_path: str, output_path: str, start_sec: float, end_sec: float, copy_mode: bool) -> None:
        raise RuntimeError("copy failed")

    monkeypatch.setattr("lecture_splitter.splitter.split_video", fake_split_video)

    lessons = [LessonSegment(index=1, start_sec=0.0, end_sec=10.0, output_file="part01.mp4")]
    try:
        split_lessons(
            input_path="input.mp4",
            lessons=lessons,
            output_dir=str(tmp_path),
            copy_mode=True,
            verify_output_with_ffprobe=False,
            verify_decode_with_ffmpeg=False,
            min_valid_duration_sec=1.0,
        )
    except RuntimeError as exc:
        assert "copy failed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")

