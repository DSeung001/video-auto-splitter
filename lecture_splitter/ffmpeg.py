from __future__ import annotations

import json
import subprocess
from pathlib import Path


SUPPORTED_INPUT_EXTENSIONS = {".mp4", ".webm"}


def _run_command(command: list[str], *, check_stderr: bool = False) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        raise RuntimeError(
            f"Command failed ({' '.join(command)}): {process.stderr.strip() or process.stdout.strip()}"
        )
    if check_stderr and process.stderr.strip():
        raise RuntimeError(f"Command reported media errors ({' '.join(command)}): {process.stderr.strip()}")
    return process


def ensure_supported_input(input_path: str) -> None:
    ext = Path(input_path).suffix.lower()
    if ext not in SUPPORTED_INPUT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_INPUT_EXTENSIONS))
        raise ValueError(f"Unsupported input extension '{ext}'. Supported extensions: {supported}")


def get_video_duration(input_path: str) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        input_path,
    ]
    process = _run_command(command)
    payload = json.loads(process.stdout or "{}")
    duration_text = payload.get("format", {}).get("duration")
    if duration_text is None:
        raise RuntimeError(f"Unable to read duration via ffprobe for {input_path}")
    duration = float(duration_text)
    if duration <= 0:
        raise RuntimeError(f"Invalid non-positive duration for {input_path}: {duration}")
    return duration


def extract_audio_pcm(input_path: str, output_path: str, sample_rate: int = 16000) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        input_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "s16le",
        output_path,
    ]
    _run_command(command)


def split_video(
    input_path: str,
    output_path: str,
    start_sec: float,
    end_sec: float,
    copy_mode: bool,
) -> None:
    duration_sec = end_sec - start_sec
    if duration_sec <= 0:
        raise ValueError(f"Split duration must be positive, got {duration_sec}")

    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-ss",
        f"{start_sec:.3f}",
        "-i",
        input_path,
        "-t",
        f"{duration_sec:.3f}",
    ]
    if copy_mode:
        command.extend(["-c", "copy", "-fflags", "+genpts", "-avoid_negative_ts", "1"])
    else:
        command.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
            ]
        )
    command.append(output_path)
    _run_command(command)


def validate_media_file(
    file_path: str,
    *,
    min_duration_sec: float = 0.2,
    verify_decode_with_ffmpeg: bool = False,
) -> float:
    probe_command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type",
        "-of",
        "json",
        file_path,
    ]
    process = _run_command(probe_command)
    payload = json.loads(process.stdout or "{}")

    streams = payload.get("streams") or []
    if not streams:
        raise RuntimeError(f"No streams found in output file: {file_path}")

    duration_text = payload.get("format", {}).get("duration")
    if duration_text is None:
        raise RuntimeError(f"Output duration missing in ffprobe response: {file_path}")

    duration = float(duration_text)
    if duration < min_duration_sec:
        raise RuntimeError(f"Output duration too short ({duration:.3f}s): {file_path}")

    if verify_decode_with_ffmpeg:
        decode_check = [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            file_path,
            "-f",
            "null",
            "-",
        ]
        _run_command(decode_check, check_stderr=True)

    return duration

