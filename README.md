# Skills — 코드 역기획 문서 생성 스킬 모음

완성된 프론트엔드 코드(HTML/JS/TS/Vue/React)를 **정적 분석**해서, 거꾸로 기획 문서를
재구성(역기획)하는 [Claude Code](https://code.claude.com/docs) 스킬 모음이다.

| 스킬 | 산출물 | 핵심 질문 | 주요 독자 |
|------|--------|-----------|-----------|
| [`reverse-spec`](reverse-spec/SKILL.md) | 역기획 **정책서** (규칙/정책 중심) | "어떻게 동작하는가" | 개발 · QA |
| [`reverse-prd`](reverse-prd/SKILL.md) | 역기획 **PRD** (요구사항/목표 중심) | "무엇을 왜 만들었는가" | PM · 기획 · 디자인 |

두 스킬은 동일한 코드 파싱 엔진([`reference.md`](reverse-prd/reference.md))과
문서 렌더러([`scripts/render.py`](reverse-prd/scripts/render.py))를 공유한다.
한 코드베이스에 둘 다 돌리면 **PRD(왜/무엇) + 정책서(어떻게)** 세트를 얻는다.

---

## 설치

스킬은 디렉토리 단위로 동작하며, 디렉토리명이 곧 커맨드명(`/reverse-prd`)이 된다.

```bash
# 개인 스킬 (모든 프로젝트에서 사용)
cp -r reverse-prd reverse-spec ~/.claude/skills/

# 또는 특정 프로젝트에서만
mkdir -p .claude/skills
cp -r reverse-prd reverse-spec .claude/skills/
```

설치 후 Claude Code에서 `/reverse-prd`, `/reverse-spec` 으로 호출하거나,
"역기획 PRD 만들어줘" 처럼 자연어로 요청하면 자동 실행된다.

### 의존성 (문서 렌더링용)

```bash
pip install weasyprint markdown python-docx
```

`--format html` 미리보기는 `markdown`만으로 가능하다. PDF는 `weasyprint`,
DOCX는 `python-docx`가 필요하다.

---

## 사용법

```bash
/reverse-prd                          # 현재 디렉토리 분석, PDF 출력
/reverse-prd src/index.html           # 특정 파일
/reverse-prd src/ --format docx       # 디렉토리 전체 + Word 출력
/reverse-spec . --format pdf --lang en
```

출력은 `./reverse-prd-output/` (또는 `reverse-spec-output/`)에
`reverse_prd_YYYYMMDD_HHMMSS.[pdf|docx|html]` 형식으로 생성된다.

---

## 동작 단계

1. **Phase 1 — 코드 파싱**: nav/route, 컴포넌트, 조건·검증·권한·API, 화면 전환 추출
   (규칙: [`reference.md`](reverse-prd/reference.md))
2. **Phase 2 — 의미 분석**: 화면 흐름 / 목적 / 정책·요구사항 추론
3. **Phase 3 — 문서 구조 구성**: 정책서 또는 PRD 목차에 배치
4. **Phase 4 — 출력**: `scripts/render.py`로 Markdown → PDF/DOCX/HTML 렌더링

### 정확성 원칙

정적 분석의 한계를 문서가 정직하게 드러내도록 다음을 항상 적용한다.

- `[추정]` — 코드에 근거 없는 의도/목표/배경/페르소나
- `[정보 없음 — 별도 확인 필요]` — 코드에 단서가 없는 항목, **import만 되고 소스가 없는 화면**
- 민감 정보(API key/password)는 문서에 포함하지 않고 별도 경고로만 표시

---

## 저장소 구조

```
.
├── reverse-spec/          # 역기획 정책서 스킬
│   ├── SKILL.md
│   ├── reference.md       # 공통 코드 파싱 규칙
│   └── scripts/render.py  # Markdown → PDF/DOCX/HTML 렌더러
├── reverse-prd/           # 역기획 PRD 스킬 (구조 동일)
│   ├── SKILL.md
│   ├── reference.md
│   └── scripts/render.py
├── docs/
│   └── skill-mcp-review.md   # 공식 문서 기반 Skill/MCP 리뷰 리포트
└── examples/
    ├── mock-shop/            # 데모용 목 e-커머스 앱 (React Router)
    ├── reverse-prd-output/   # mock-shop 분석 PRD 샘플 (HTML)
    └── review-output/        # 리뷰 리포트 HTML 샘플
```

> `reference.md`와 `scripts/render.py`는 두 스킬에서 **동일 사본**으로 유지된다
> (스킬은 자기 디렉토리 내부 파일만 `${CLAUDE_SKILL_DIR}`로 참조하므로).
> 한쪽을 수정하면 다른 쪽에도 복사할 것.

---

## 참고

- 공식 문서 기반 스펙 준수 리뷰: [`docs/skill-mcp-review.md`](docs/skill-mcp-review.md)
- 샘플 출력 미리보기: `examples/reverse-prd-output/reverse_prd_mock-shop_sample.html`
