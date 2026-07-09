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

## 사용 방법 (2가지)

1. **코드 받아서 실행(개발/수정 가능)**: 저장소를 clone 후 Python 환경에서 실행
2. **실행파일 바로 다운로드(빠른 사용)**: GitHub Actions 아티팩트 다운로드 후 바로 실행

## 방법 1) 코드 받아서 실행

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

## GUI로 실행하기

CLI 인자를 몰라도 되도록 설정용 GUI(Tkinter, 표준 라이브러리)를 제공합니다.

```bash
# 명시적으로 GUI 실행
python auto_split.py --gui

# 아무 인자 없이 실행해도 자동으로 GUI가 뜹니다
python auto_split.py
```

GUI에서 할 수 있는 것:

- 입력 파일 / 출력 디렉터리 / config 파일 경로를 파일 다이얼로그로 선택
- 프리셋(balanced/sensitive/strict), 모드(copy/accurate), dry-run 여부 선택
- 무음/화면정지 임계값, 쉬는시간 길이, break 점수 임계값 등 주요 설정값을 화면에서 편집하고 "설정 저장"으로 config YAML에 반영
- "실행" 버튼으로 파이프라인을 백그라운드에서 실행하고, 진행 로그를 화면에서 확인

> Linux에서 `ModuleNotFoundError: No module named 'tkinter'` 오류가 나면 시스템 패키지
> `python3-tk`(Debian/Ubuntu) 또는 `python3-tkinter`(Fedora) 를 설치하세요.

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
- macOS/Linux (GUI 전용): `dist/lecture-auto-splitter-gui`
- Windows(워크플로우): `dist/lecture-auto-splitter.exe`
- Windows(워크플로우, GUI 전용): `dist/lecture-auto-splitter-gui.exe`

실행 예시:

```bash
./dist/lecture-auto-splitter --init-config
./dist/lecture-auto-splitter input/sample.webm --config config.yaml --dry-run
./dist/lecture-auto-splitter --gui
# GUI를 바로 실행하려면 (옵션 없이 실행)
./dist/lecture-auto-splitter-gui
```

## 방법 2) 실행파일 다운로드 후 바로 실행 (GitHub Actions 아티팩트)

`.github/workflows/build-binaries.yml`가 포함되어 있습니다.

1. GitHub 저장소에서 **Actions** 탭으로 이동
2. 왼쪽 워크플로우 목록에서 **Build Binaries** 선택
3. 최신 성공 실행(run) 클릭
4. 페이지 하단 **Artifacts**에서 OS에 맞는 파일 다운로드
5. 압축 해제 후 실행 파일과 `config.example.yaml` 확인

> 아티팩트가 없다면: PR이 `main`에 병합된 뒤 run을 확인하거나, **Run workflow** 버튼으로 수동 실행하세요.

실행 예시:

```bash
./lecture-auto-splitter --init-config
./lecture-auto-splitter input/sample.mp4 --config config.yaml --output output/run1
# GUI를 바로 실행하려면
./lecture-auto-splitter-gui
```

Windows:

```powershell
.\lecture-auto-splitter-Windows.exe --init-config
.\lecture-auto-splitter-Windows.exe input\sample.webm --config config.yaml --dry-run
# GUI를 바로 실행하려면
.\lecture-auto-splitter-gui-Windows.exe
```

## 주요 옵션

- `--dry-run`: 분석만 수행하고 파일 분리하지 않음
- `--copy`: 스트림 복사 모드 (빠름, 기본값)
- `--accurate`: 재인코딩 모드 (느리지만 컷 경계/호환성 유리)
- `--config`: YAML 설정 파일 경로
- `--output`: 출력 디렉터리
- `--gui`: 설정/실행용 GUI 실행

> WEBM 입력은 기본적으로 copy를 먼저 시도하고, 분리/검증 실패 시 해당 파트만 accurate로 자동 재시도합니다.

## 테스트

```bash
pytest -q
```
