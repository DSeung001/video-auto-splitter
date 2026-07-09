# Lecture Auto Splitter (한국어)

[English documentation](README.en.md)

Lecture Auto Splitter는 긴 강의 녹화본에서 쉬는 시간 구간을 자동으로 탐지하고, 강의 파트만 분리해 메타데이터와 함께 출력하는 도구입니다.

## 제품 개요

수동 타임라인 편집은 반복 작업에서 시간이 많이 들고 실수가 발생하기 쉽습니다. 이 도구는 오디오 무음 신호와 화면 정적 신호를 결합해 break 구간을 추정하고, 일관된 규칙으로 파일을 분리합니다.

## 핵심 기능

- 오디오 + 화면 기반 break 후보 자동 탐지
- 최종 파일 교체 전 검증을 수행하는 안전한 출력 파이프라인
- 두 가지 분리 모드:
  - `--copy` (기본): 빠른 스트림 복사
  - `--accurate`: 컷 경계 품질을 위한 재인코딩
- 비개발자 사용자를 위한 GUI 실행 지원
- 최신 Windows 릴리즈 자산 자동 갱신 CI

## 다운로드

최신 릴리즈 고정 링크:

- Windows CLI: [lecture-auto-splitter-Windows.exe](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/lecture-auto-splitter-Windows.exe)
- Windows GUI: [lecture-auto-splitter-gui-Windows.exe](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/lecture-auto-splitter-gui-Windows.exe)
- 설정 템플릿: [config.example.yaml](https://github.com/DSeung001/video-auto-splitter/releases/latest/download/config.example.yaml)

## 요구사항

- Python 3.11+
- `ffmpeg`, `ffprobe`가 `PATH`에 등록되어 있어야 함

## 빠른 시작 (소스 실행)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

설정 파일 생성:

```bash
python auto_split.py --init-config
```

분석만 실행:

```bash
python auto_split.py input/class_recording.webm --config config.yaml --dry-run
```

실제 분리 실행:

```bash
python auto_split.py input/class_recording.mp4 --config config.yaml --output output/class_recording
```

## GUI 모드

```bash
python auto_split.py --gui
```

인자 없이 실행하면 GUI가 열립니다:

```bash
python auto_split.py
```

## 설정 프리셋

```bash
python auto_split.py --init-config
python auto_split.py --init-config settings/academy-a.yaml
python auto_split.py --init-config config.yaml --config-preset sensitive
python auto_split.py --init-config config.yaml --force
```

- `balanced`: 일반 강의에 권장되는 기본값
- `sensitive`: break 후보를 더 많이 탐지
- `strict`: 오탐지 감소

## 로컬 바이너리 빌드

```bash
./scripts/build_binary.sh
```

결과물:

- macOS/Linux CLI: `dist/lecture-auto-splitter`
- macOS/Linux GUI: `dist/lecture-auto-splitter-gui`
- Windows CLI (CI): `dist/lecture-auto-splitter.exe`
- Windows GUI (CI): `dist/lecture-auto-splitter-gui.exe`

## CI / 릴리즈 배포

`Build Binaries` 워크플로는 아래에서 실행됩니다:

- `main` 푸시(머지 커밋 포함)
- 태그 푸시(`v*`)
- 수동 실행

Windows 결과물은 `latest` 릴리즈 자산으로 배포되어 README 링크가 고정 유지됩니다.

## CLI 옵션

- `--dry-run`: 분석만 수행
- `--copy`: 빠른 분리 모드 (기본)
- `--accurate`: 재인코딩 분리 모드
- `--config`: YAML 설정 파일 경로
- `--output`: 출력 디렉터리
- `--gui`: GUI 실행

## 테스트

```bash
pytest -q
```
