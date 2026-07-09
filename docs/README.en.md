# Lecture Auto Splitter (English)

[한국어 문서 보기](README.ko.md)

Lecture Auto Splitter automatically detects break segments in long lecture recordings and exports clean lecture-only parts with review metadata.

## Product overview

Manual timeline editing does not scale for repeated class recordings. This tool combines audio quietness and screen activity signals to detect likely break windows and split files with repeatable rules.

## Core capabilities

- Automatic break detection with audio + visual heuristics
- Safe output workflow with validation before replacing final files
- Two split modes:
  - `--copy` (default): fast stream copy
  - `--accurate`: re-encode for cleaner cut boundaries
- GUI launcher for non-CLI users
- CI pipeline with latest Windows release assets

## Download

Stable links from the latest release:

- Windows CLI: [lecture-auto-splitter-Windows.exe](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/lecture-auto-splitter-Windows.exe)
- Windows GUI: [lecture-auto-splitter-gui-Windows.exe](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/lecture-auto-splitter-gui-Windows.exe)
- Config template: [config.example.yaml](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/config.example.yaml)

## Requirements

- Python 3.11+
- `ffmpeg` and `ffprobe` in `PATH`

## Quick start (source)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Generate config:

```bash
python auto_split.py --init-config
```

Dry run:

```bash
python auto_split.py input/class_recording.webm --config config.yaml --dry-run
```

Run split:

```bash
python auto_split.py input/class_recording.mp4 --config config.yaml --output output/class_recording
```

## GUI mode

```bash
python auto_split.py --gui
```

Or launch GUI with no arguments:

```bash
python auto_split.py
```

## Configuration presets

```bash
python auto_split.py --init-config
python auto_split.py --init-config settings/academy-a.yaml
python auto_split.py --init-config config.yaml --config-preset sensitive
python auto_split.py --init-config config.yaml --force
```

- `balanced`: recommended default
- `sensitive`: catches more break candidates
- `strict`: reduces false positives

## Local binary build

```bash
./scripts/build_binary.sh
```

Outputs:

- macOS/Linux CLI: `dist/lecture-auto-splitter`
- macOS/Linux GUI: `dist/lecture-auto-splitter-gui`
- Windows CLI (CI): `dist/lecture-auto-splitter.exe`
- Windows GUI (CI): `dist/lecture-auto-splitter-gui.exe`

## CI and release delivery

`Build Binaries` workflow runs on:

- Push to `main` (including merged PR commits)
- Tag push (`v*`)
- Manual dispatch

Windows artifacts are published to the `latest` release so README links stay fixed.

## CLI options

- `--dry-run`: analysis only
- `--copy`: fast split mode (default)
- `--accurate`: re-encode split mode
- `--config`: YAML config path
- `--output`: output directory
- `--gui`: launch GUI

## Testing

```bash
pytest -q
```
