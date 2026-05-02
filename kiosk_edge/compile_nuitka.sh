#!/usr/bin/env bash
# Kiosk FastAPI kodunu Nuitka ile tek binary'e derler.
# Kullanım: ./compile_nuitka.sh
set -euo pipefail

cd "$(dirname "$0")/api"

python -m nuitka \
  --standalone \
  --onefile \
  --follow-imports \
  --output-filename=eisa_api.bin \
  --output-dir=../dist \
  --remove-output \
  main.py

echo "Build hazır: ../dist/eisa_api.bin"
