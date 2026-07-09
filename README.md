# Lecture Auto Splitter

Lecture Auto Splitter detects break segments in long class recordings and exports clean lecture-only video parts with review metadata.
It is designed for instructors and operations teams who need repeatable, low-touch post-processing for recorded sessions.

## Why this tool

Manual timeline cutting is slow, error-prone, and hard to scale.
This tool combines audio quietness and screen activity signals to find likely break windows and split recordings automatically.

## Key features

- Automatic break detection using audio + visual heuristics
- Safe output workflow with validation before final file replacement
- Two execution modes:
  - `--copy` (default): fast stream copy
  - `--accurate`: re-encode for cleaner cut boundaries
- GUI launcher for non-CLI users
- Build-ready binaries for Windows/macOS/Linux

## Download (recommended)

When changes are merged into `main`, GitHub Actions updates the latest release assets.
Use the stable links below from this README:

- Windows CLI: [lecture-auto-splitter-Windows.exe](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/lecture-auto-splitter-Windows.exe)
- Windows GUI: [lecture-auto-splitter-gui-Windows.exe](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/lecture-auto-splitter-gui-Windows.exe)
- Default config template: [config.example.yaml](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/config.example.yaml)

> Note: Release assets may take a few minutes to refresh after `main` is updated.

## Requirements

- Python 3.11+
- `ffmpeg` and `ffprobe` available in `PATH`

## Quick start (source)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Generate config template:

```bash
python auto_split.py --init-config
```

Dry run (analysis only):

```bash
python auto_split.py input/class_recording.webm --config config.yaml --dry-run
```

Actual split:

```bash
python auto_split.py input/class_recording.mp4 --config config.yaml --output output/class_recording
```

## GUI mode

Run with GUI explicitly:

```bash
python auto_split.py --gui
```

Or run with no arguments (GUI opens automatically):

```bash
python auto_split.py
```

GUI supports:

- Input/output/config file selection via file dialogs
- Preset selection (`balanced`, `sensitive`, `strict`)
- Main threshold tuning from the UI
- Background execution with live logs

## Configuration bootstrapping

```bash
# Create balanced preset config at default path (config.yaml)
python auto_split.py --init-config

# Create at a custom path
python auto_split.py --init-config settings/academy-a.yaml

# Create with preset
python auto_split.py --init-config config.yaml --config-preset sensitive

# Overwrite existing config
python auto_split.py --init-config config.yaml --force
```

Preset behavior:

- `balanced`: recommended default for general lecture content
- `sensitive`: catches more break candidates
- `strict`: reduces false positives

## Build binaries locally

```bash
./scripts/build_binary.sh
```

Build outputs:

- macOS/Linux CLI: `dist/lecture-auto-splitter`
- macOS/Linux GUI: `dist/lecture-auto-splitter-gui`
- Windows CLI (CI): `dist/lecture-auto-splitter.exe`
- Windows GUI (CI): `dist/lecture-auto-splitter-gui.exe`

## CI build and delivery

`Build Binaries` workflow:

- Trigger: push to `main` (including merged PR commits), tag push (`v*`), or manual run
- Output: OS-specific artifacts in Actions
- Windows release delivery: updates `latest` release assets used by the stable links above

## CLI options

- `--dry-run`: analyze only, do not split files
- `--copy`: fast stream copy mode (default)
- `--accurate`: re-encode mode for stronger cut compatibility
- `--config`: YAML config file path
- `--output`: output directory
- `--gui`: launch GUI

## Testing

```bash
pytest -q
```

---

## 한국어 안내 (Korean)

Lecture Auto Splitter는 강의 녹화본에서 쉬는 시간 구간을 자동으로 탐지해, 실제 강의 파트만 분리 저장하는 도구입니다.

### 빠른 다운로드 (권장)

`main` 브랜치에 머지될 때마다 최신 릴리즈 자산이 갱신됩니다.
아래 고정 링크로 항상 최신 파일을 받을 수 있습니다.

- Windows CLI: [lecture-auto-splitter-Windows.exe](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/lecture-auto-splitter-Windows.exe)
- Windows GUI: [lecture-auto-splitter-gui-Windows.exe](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/lecture-auto-splitter-gui-Windows.exe)
- 기본 설정 파일: [config.example.yaml](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/config.example.yaml)

### 핵심 기능

- 오디오 무음 + 화면 정적 신호 결합 기반 break 후보 탐지
- 결과 파일 검증 후 교체하는 안전한 출력 파이프라인
- CLI / GUI 모두 지원
- `copy`(빠름) / `accurate`(정확) 모드 지원

### 기본 사용 예시

```bash
python auto_split.py --init-config
python auto_split.py input/sample.webm --config config.yaml --dry-run
python auto_split.py input/sample.mp4 --config config.yaml --output output/run1
```

Windows 실행 예시:

```powershell
.\lecture-auto-splitter-Windows.exe --init-config
.\lecture-auto-splitter-Windows.exe input\sample.webm --config config.yaml --dry-run
.\lecture-auto-splitter-gui-Windows.exe
```
