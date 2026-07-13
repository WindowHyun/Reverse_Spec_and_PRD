#!/usr/bin/env bash
# 공유 파일 단방향 동기화: 정본(reverse-prd) → 사본(reverse-spec).
#
# 구조 원칙: 공유 파일 4종의 정본은 reverse-prd 쪽이다. 수정은 반드시
# reverse-prd에서 하고, 이 스크립트로 reverse-spec에 반영한다.
# (양쪽을 각각 수정하면 어느 쪽이 옳은지 판정할 수 없게 된다 —
#  check-sync.sh는 "동일한가"만 검사하는 최종 관문이고, 방향은 이 스크립트가 정한다.)
set -euo pipefail

cd "$(dirname "$0")/.."

SHARED_FILES=(
  "reference.md"
  "scripts/render.py"
  "scripts/flowgen.py"
  "scripts/extract.py"
)

for f in "${SHARED_FILES[@]}"; do
  cp "reverse-prd/$f" "reverse-spec/$f"
  echo "✅ 반영: reverse-prd/$f → reverse-spec/$f"
done

bash tools/check-sync.sh
