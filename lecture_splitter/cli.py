from __future__ import annotations

import argparse
import sys

from lecture_splitter.audio_analyzer import analyze_audio
from lecture_splitter.config import AppConfig, load_config, write_config_template
from lecture_splitter.detector import build_lesson_segments, detect_breaks
from lecture_splitter.ffmpeg import ensure_supported_input, get_video_duration
from lecture_splitter.report import write_segments_csv, write_segments_json
from lecture_splitter.splitter import split_lessons
from lecture_splitter.utils import ensure_dir, sec_to_timestamp
from lecture_splitter.video_analyzer import analyze_video


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auto_split.py",
        description="Detect lecture break intervals and split lecture-only MP4 parts.",
    )
    parser.add_argument("input_path", nargs="?", help="Input lecture file (.mp4 or .webm)")
    parser.add_argument("--config", default=None, help="Path to YAML config file (optional)")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only; do not split output files")
    parser.add_argument("--output", help="Output directory (default: output/<input_stem>)")
    parser.add_argument(
        "--init-config",
        nargs="?",
        const="config.yaml",
        help="Write a config template and exit (default path: ./config.yaml)",
    )
    parser.add_argument(
        "--config-preset",
        choices=["balanced", "sensitive", "strict"],
        default="balanced",
        help="Preset to use with --init-config",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing config with --init-config")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--copy", action="store_true", help="Split with stream copy mode")
    mode_group.add_argument("--accurate", action="store_true", help="Split with re-encode mode")
    return parser


def _resolve_copy_mode(input_path: str, args: argparse.Namespace, config: AppConfig) -> bool:
    if args.copy:
        return True
    elif args.accurate:
        return False
    return config.split.default_copy_mode


def _print_summary(duration_sec: float, breaks, lessons) -> None:
    print(f"Video duration: {sec_to_timestamp(duration_sec)} ({duration_sec:.1f}s)")
    print("Detected breaks:")
    if not breaks:
        print("  (none)")
    for idx, brk in enumerate(breaks, start=1):
        print(f"  {idx}. {sec_to_timestamp(brk.start_sec)} ~ {sec_to_timestamp(brk.end_sec)}")
    print("Lesson segments:")
    for lesson in lessons:
        print(
            f"  part{lesson.index:02d}: "
            f"{sec_to_timestamp(lesson.start_sec)} ~ {sec_to_timestamp(lesson.end_sec)}"
        )


def run_pipeline(args: argparse.Namespace) -> int:
    if args.init_config:
        written_path = write_config_template(args.init_config, preset=args.config_preset, overwrite=args.force)
        print(f"Wrote config template: {written_path}")
        return 0

    if not args.input_path:
        raise ValueError("input_path is required unless --init-config is used.")

    ensure_supported_input(args.input_path)
    config = load_config(args.config)
    copy_mode = _resolve_copy_mode(args.input_path, args, config)

    duration_sec = get_video_duration(args.input_path)
    audio_points = analyze_audio(args.input_path, config.audio)
    video_points = analyze_video(args.input_path, config.video)
    breaks = detect_breaks(audio_points, video_points, config.break_detection, config.scoring)
    lessons = build_lesson_segments(duration_sec, breaks, config.break_detection)

    _print_summary(duration_sec, breaks, lessons)
    if args.dry_run:
        return 0

    default_output = Path("output") / Path(args.input_path).stem
    output_dir = ensure_dir(args.output or default_output)

    split_lessons(
        input_path=args.input_path,
        lessons=lessons,
        output_dir=str(output_dir),
        copy_mode=copy_mode,
        verify_output_with_ffprobe=config.split.verify_output_with_ffprobe,
        verify_decode_with_ffmpeg=config.split.verify_decode_with_ffmpeg,
        min_valid_duration_sec=config.split.min_valid_duration_sec,
    )
    write_segments_csv(str(output_dir / "segments.csv"), breaks, lessons)
    write_segments_json(str(output_dir / "segments.json"), breaks, lessons)
    print(f"Wrote outputs to: {output_dir}")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        return run_pipeline(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
