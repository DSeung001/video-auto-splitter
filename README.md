# Lecture Auto Splitter

Jitsi 강의 녹화 파일(`.mp4`, `.webm`)을 입력받아 쉬는 시간 후보를 자동 감지하고, 강의 파트만 분리한 MP4와 검수용 메타데이터(CSV/JSON)를 생성하는 CLI 도구입니다.

## 컨셉

- 문제: 수동 컷 편집(LosslessCut 등) 반복 비용이 큼
- 접근: 오디오 quiet score + 화면 static score를 결합해 break 후보 탐지
- 결과: `part01.mp4`, `part02.mp4`, ..., `segments.csv`, `segments.json`
- 안전성: 분리 파일은 임시 파일 생성 후 ffprobe/ffmpeg 검증을 통과한 경우에만 최종 파일로 교체

## 요구사항

- Python 3.11+
- `ffmpeg`, `ffprobe` (PATH 등록)

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

분석만 실행(dry-run):

```bash
python auto_split.py input/class_recording.webm --config config.yaml --dry-run
```

실제 분리 실행:

```bash
python auto_split.py input/class_recording.mp4 --config config.yaml --output output/class_recording
```

## 설정파일 세팅 기능

CLI에서 설정 템플릿을 생성할 수 있습니다.

```bash
# 기본 경로(config.yaml)에 balanced 프리셋 생성
python auto_split.py --init-config

# 경로 지정
python auto_split.py --init-config settings/academy-a.yaml

# 프리셋 지정 (balanced | sensitive | strict)
python auto_split.py --init-config config.yaml --config-preset sensitive

# 기존 파일 덮어쓰기
python auto_split.py --init-config config.yaml --force
```

프리셋 의미:

- `balanced`: 기본값, 일반적인 강의에 권장
- `sensitive`: break를 더 잘 잡도록 민감하게 탐지
- `strict`: 오탐을 줄이기 위해 보수적으로 탐지

## 빌드해서 실행파일 만들기

```bash
./scripts/build_binary.sh
```

빌드 결과:

- macOS/Linux: `dist/lecture-auto-splitter`
- Windows(워크플로우): `dist/lecture-auto-splitter.exe`

실행 예시:

```bash
./dist/lecture-auto-splitter --init-config
./dist/lecture-auto-splitter input/sample.webm --config config.yaml --dry-run
```

## 다운로드해서 실행하기 (GitHub Actions 아티팩트)

`.github/workflows/build-binaries.yml`가 포함되어 있습니다.

1. GitHub에서 **Actions → Build Binaries** 실행(또는 `v*` 태그 푸시)
2. OS별 아티팩트 다운로드
3. 압축 해제 후 실행 파일과 `config.example.yaml` 확인

실행 예시:

```bash
./lecture-auto-splitter --init-config
./lecture-auto-splitter input/sample.mp4 --config config.yaml --output output/run1
```

Windows:

```powershell
.\lecture-auto-splitter-Windows.exe --init-config
.\lecture-auto-splitter-Windows.exe input\sample.webm --config config.yaml --dry-run
```

## 주요 옵션

- `--dry-run`: 분석만 수행하고 파일 분리하지 않음
- `--copy`: 스트림 복사 모드 (빠름, 컷 경계 정확도 낮을 수 있음)
- `--accurate`: 재인코딩 모드 (느리지만 안정적)
- `--config`: YAML 설정 파일 경로
- `--output`: 출력 디렉터리

> WEBM 입력에서 `--copy`를 강제해도 안정성을 위해 내부적으로 정확 모드로 전환됩니다.

## 테스트

```bash
pytest -q
```
