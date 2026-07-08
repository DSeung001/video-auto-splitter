#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m pip install -r requirements.txt -r requirements-build.txt
python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name lecture-auto-splitter \
  auto_split.py

echo "Built executable: $ROOT_DIR/dist/lecture-auto-splitter"
