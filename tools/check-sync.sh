#!/usr/bin/env bash
# 두 스킬(reverse-spec / reverse-prd)이 공유하는 파일이 동일 사본인지 검증한다.
# 스킬은 ${CLAUDE_SKILL_DIR}로 자기 디렉토리 내부만 참조할 수 있어 사본을 둘 수밖에 없다.
# 커밋 전 또는 CI에서 실행: bash tools/check-sync.sh
set -u

cd "$(dirname "$0")/.."

SHARED_FILES=(
  "reference.md"
  "scripts/render.py"
)

status=0
for f in "${SHARED_FILES[@]}"; do
  a="reverse-spec/$f"
  b="reverse-prd/$f"
  if [[ ! -f "$a" || ! -f "$b" ]]; then
    echo "❌ 누락: $a 또는 $b 가 없음"
    status=1
  elif ! diff -q "$a" "$b" >/dev/null; then
    echo "❌ 불일치: $a ↔ $b"
    diff -u "$a" "$b" | head -20
    status=1
  else
    echo "✅ 동일: $f"
  fi
done

if [[ $status -ne 0 ]]; then
  echo ""
  echo "공유 파일이 어긋났습니다. 한쪽을 수정했다면 다른 쪽에도 복사하세요:"
  echo "  cp reverse-prd/reference.md reverse-spec/reference.md"
  echo "  cp reverse-prd/scripts/render.py reverse-spec/scripts/render.py"
fi
exit $status
