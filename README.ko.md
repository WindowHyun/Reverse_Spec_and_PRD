# Skills — 코드 역기획 문서 생성 스킬 모음

[English](README.md) · **한국어**

완성된 프론트엔드 코드(HTML/JS/TS/Vue/React)를 **정적 분석**해서, 거꾸로 기획 문서를
재구성(역기획)하는 [Claude Code](https://code.claude.com/docs) 스킬 모음이다.

| 스킬 | 산출물 | 핵심 질문 | 주요 독자 |
|------|--------|-----------|-----------|
| [`reverse-spec`](reverse-spec/SKILL.md) | 역기획 **정책서** (규칙/정책 중심) | "어떻게 동작하는가" | 개발 · QA |
| [`reverse-prd`](reverse-prd/SKILL.md) | 역기획 **PRD** (요구사항/목표 중심) | "무엇을 왜 만들었는가" | PM · 기획 · 디자인 |

두 스킬은 동일한 코드 파싱 규칙([`reference.md`](reverse-prd/reference.md))과
문서 렌더러([`scripts/render.py`](reverse-prd/scripts/render.py))를 공유한다.
한 코드베이스에 둘 다 돌리면 **PRD(왜/무엇) + 정책서(어떻게)** 세트를 얻는다.

---

## 여기서 "스킬"이란 (그리고 왜 이식 가능한가)

각 스킬은 `SKILL.md` 지침 파일과 순수 로컬 Python 스크립트 3종으로 구성된다.

1. **`SKILL.md`** — 절차 (YAML 프론트매터 + Markdown). *사실은 파서가 추출하고,
   LLM은 해석만 쓴다*는 하이브리드 원칙을 따른다.
2. **`scripts/extract.py`** — 결정적 사실 추출기 (라우트·API·문구·상태·연동·스냅샷 —
   같은 코드면 항상 같은 사실 표).
3. **`scripts/flowgen.py`** — 유저플로우 SVG 생성기 (HTML·PDF 모두에서 렌더링).
4. **`scripts/render.py`** — Markdown → PDF+HTML 쌍(또는 DOCX) 렌더러.

즉 이 스킬은 **기본적으로** Claude Code Agent Skill이지만, 같은 `SKILL.md` 본문을 다른 AI
도구의 *커스텀 프롬프트 / 커스텀 커맨드 / 규칙 파일* 로 그대로 쓸 수 있고, 스크립트들은 어떤
셸에서든 실행된다. 아래 도구별 설정법을 참고하라.

### 의존성 (문서 렌더링용)

```bash
pip install weasyprint markdown python-docx
```

**Python 3.9 이상이 필요하다** (렌더러가 최신 타입 표기를 사용하며, 현행 WeasyPrint도
3.9+를 요구한다). HTML 출력은 `markdown`만, PDF는 `weasyprint`, DOCX는 `python-docx`가
필요하다. macOS에서 `python`/`pip`이 없으면 `python3`/`pip3`를 사용한다.

스킬은 산출물(`reverse-spec-output/`, `reverse-prd-output/` — `_facts.md`/`_flow.json`
중간 파일 포함)을 **분석 대상 프로젝트의 작업 디렉토리에** 생성한다. 커밋을 원치
않으면 해당 프로젝트의 `.gitignore`에 이 디렉토리들을 추가한다.

**PDF 플랫폼 안내 (WeasyPrint는 네이티브 Pango 라이브러리가 필요 — pip만으로는 부족):**

- **Windows**: [MSYS2](https://www.msys2.org/) 설치 후 MSYS2 UCRT64 셸에서
  `pacman -S mingw-w64-ucrt-x86_64-pango` 실행. (WeasyPrint 공식 권장 —
  [설치 문서](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) 참조.)
  어려우면 PDF 대신 `--format docx,html` 사용.
- **macOS**: `brew install weasyprint` 한 줄 (Pango 자동 포함).
- **Linux**: 대개 `pip install`만으로 동작. 안 되면 패키지 매니저로 `pango` 설치.

---

## 도구별 설정 방법

> 아래 예시는 `reverse-prd` 기준이며, `reverse-spec`도 동일하게 반복하면 된다.

### 1. Claude Code (터미널 CLI) — 네이티브 Agent Skill ✅

```bash
# 개인용 (모든 프로젝트에서 사용)
cp -r reverse-prd reverse-spec ~/.claude/skills/
# …또는 프로젝트 한정 (팀 공유, 저장소에 커밋)
mkdir -p .claude/skills && cp -r reverse-prd reverse-spec .claude/skills/
```

`/reverse-prd` 로 호출하거나, "src/ 코드로 역기획 PRD 만들어줘"처럼 자연어로 요청하면
`description`이 매칭될 때 Claude가 자동 로드한다. 세션 중에도 즉시 인식된다(재시작 불필요).
디렉토리명이 곧 커맨드명이 된다.
문서: <https://code.claude.com/docs/en/skills>

### 2. Claude CLI — Claude Code와 동일

별도의 "Claude CLI" 제품은 없다. 터미널 도구는 **Claude Code**이고 `claude` 명령으로 실행한다.
1번 절차를 그대로 사용한다. (Anthropic API SDK와 혼동하지 말 것.)

### 3. Claude Desktop 앱 — ZIP 업로드

Claude 채팅 앱은 커스텀 Skill을 지원하지만, 디스크 폴더가 아니라 **업로드** 방식이다.

```bash
# macOS/Linux — 스킬 폴더를 zip으로 압축 (SKILL.md 포함되어야 함)
cd reverse-prd && zip -r ../reverse-prd.zip . && cd ..
# Windows (PowerShell)
Compress-Archive -Path reverse-prd\* -DestinationPath reverse-prd.zip
```

앱에서 **설정 → Capabilities → Skills → Upload skill** 로 ZIP을 선택한다. 코드 실행이
활성화된 유료 플랜이 필요하다. 데스크톱 ZIP 형식에서는 `name` 필드가 **필수**다(소문자
영숫자·하이픈, 64자 이하, "claude"/"anthropic" 단어 포함 불가). MCP 서버를 추가하려면
**설정 → Developer → Edit Config** (`claude_desktop_config.json`)를 사용한다.
문서: <https://support.claude.com/en/articles/12512180-use-skills-in-claude>

### 4. OpenAI Codex CLI — 커스텀 프롬프트 + 스크립트

Codex는 `~/.codex/prompts/` 안의 Markdown 파일을 슬래시 커맨드로 만든다.

```bash
mkdir -p ~/.codex/prompts
cp reverse-prd/SKILL.md ~/.codex/prompts/reverse-prd.md
```

Codex CLI 또는 IDE 확장에서 `/reverse-prd` 로 호출한다. 항상 적용되는 지침이 필요하면 저장소
루트의 `AGENTS.md`에 절차를 넣는다. 렌더러는 Codex 셸에서 직접 실행:
`python reverse-prd/scripts/render.py …`.
참고: OpenAI는 커스텀 프롬프트를 **deprecated**로 표시하고 Codex Skills를 권장한다(둘 다 현재
동작함). 문서: <https://developers.openai.com/codex/custom-prompts>

### 5. Gemini CLI (Google) — TOML 커스텀 커맨드

Gemini 커스텀 커맨드는 `prompt` 필드를 가진 TOML 파일이다.

```bash
mkdir -p ~/.gemini/commands
cat > ~/.gemini/commands/reverse-prd.toml <<'EOF'
description = "코드에서 PRD를 역기획하고 PDF/DOCX로 렌더링한다."
prompt = """
다음 절차에 따라 대상 코드로부터 역기획 PRD를 생성한다.
대상 경로: {{args}}

<여기에 reverse-prd/SKILL.md 본문을 붙여넣거나 단계 요약>
이후 렌더링: python reverse-prd/scripts/render.py --input <body.md> --format pdf
"""
EOF
```

`/reverse-prd src/` 로 호출한다. `{{args}}`는 커맨드 뒤에 입력한 텍스트로 치환된다. 항상
적용되는 컨텍스트는 `GEMINI.md`, MCP는 `~/.gemini/settings.json`을 사용한다.
문서: <https://geminicli.com/docs/cli/custom-commands/>

### 6. Google Antigravity (에이전트형 IDE) — Workflow (가장 근접)

슬래시 커맨드 스킬에 가장 가까운 것은 Antigravity의 **Workflow**다.

```bash
mkdir -p .agent/workflows
cp reverse-prd/SKILL.md .agent/workflows/reverse-prd.md
```

Agent 패널에서 `/reverse-prd` 로 호출한다. Antigravity에는 **Skills**(보통
`.agent/skills/<name>/SKILL.md`이지만 IDE/CLI·버전에 따라 경로가 달라지므로 설치본 기준으로
확인 필요), **Rules**(`GEMINI.md` / `AGENTS.md` / `.agent/rules/`), 그리고
`~/.gemini/config/mcp_config.json`의 MCP 설정도 있다.
문서: <https://antigravity.google/docs/rules-workflows>

### 한눈에 비교

| 도구 | 메커니즘 | 파일 위치 | 형식 | 호출 |
|------|----------|-----------|------|------|
| Claude Code | Agent Skill | `~/.claude/skills/<n>/SKILL.md` 또는 `.claude/skills/<n>/SKILL.md` | YAML+MD | `/<n>` 또는 자동 |
| Claude CLI | = Claude Code | 동일 | 동일 | 동일 |
| Claude Desktop | Skill (ZIP 업로드) | 설정 → Capabilities → Skills | YAML+MD (zip) | 자동 |
| Codex CLI | 커스텀 프롬프트 | `~/.codex/prompts/<n>.md` | MD | `/<n>` |
| Gemini CLI | 커스텀 커맨드 | `~/.gemini/commands/<n>.toml` | TOML | `/<n>` |
| Antigravity | Workflow / Skill | `.agent/workflows/<n>.md` | MD | `/<n>` |

> **주의.** Codex 커스텀 프롬프트는 deprecated다(향후 Codex Skills 권장). Antigravity 스킬
> 경로는 CLI/IDE·버전에 따라 다르니 설치본 기준 확인이 필요하다. Claude Desktop Skill은
> 사용자별 ZIP 업로드이며 Claude Code/API와 동기화되지 않는다. 비-Claude 도구에서는
> `SKILL.md` 본문을 해당 도구의 프롬프트/커맨드로 옮기고 `render.py`를 셸에서 실행하면 된다.

---

## 사용법 (Claude Code)

```bash
/reverse-prd                          # 현재 디렉토리 분석, PDF 출력
/reverse-prd src/index.html           # 특정 파일
/reverse-prd src/ --format docx       # 디렉토리 전체 + Word 출력
/reverse-spec . --format pdf --lang en
```

출력은 `./reverse-prd-output/` (또는 `reverse-spec-output/`)에 생성된다.
**기본적으로 매 실행마다 PDF + HTML 쌍**이 같은 타임스탬프로 함께 만들어진다
(예: `reverse_prd_….pdf` + `reverse_prd_….html`) — HTML은 브라우저 즉시 확인용,
PDF는 공유/인쇄용. `--format docx,html`을 지정하면 PDF 대신 Word로 생성된다.

---

## 동작 단계

1. **Phase 1 — 파싱 (결정적):** `scripts/extract.py`가 사실을 추출 — 라우트, 컴포넌트,
   API, 상수, 규칙, 화면 전환, 사용자 노출 문구, 상태 사용처, 연동/트래킹, As-Is 스냅샷
   (규칙: [`reference.md`](reverse-prd/reference.md)). 같은 코드 → 항상 같은 사실.
   소스 약 30개 초과 시 모듈로 나눠 서브에이전트가 병렬 추출.
2. **Phase 2 — 해석 (LLM):** 화면 흐름 / 목적 / 정책·요구사항 추론 —
   추출된 사실 표만을 근거로 수행.
3. **Phase 3 — 구성:** 정책서 또는 PRD 목차에 배치. `scripts/flowgen.py`가
   유저플로우 SVG 생성 (HTML·PDF 모두에서 보임).
4. **Phase 4 — 렌더링:** `scripts/render.py`로 Markdown → **PDF + HTML 쌍** (또는 DOCX).

### 정확성 원칙

정적 분석의 한계를 문서가 정직하게 드러낸다.

- `[추정]` — 코드에 직접 근거가 없는 의도/목표/배경/페르소나.
- `[정보 없음 — 별도 확인 필요]` — 코드에 단서가 없는 항목, 특히 **import만 되고 소스가 분석
  대상에 없는 컴포넌트**.
- 민감 정보(API key/password)는 문서에 절대 포함하지 않고 경고로만 표시한다.

---

## 저장소 구조

```
.
├── reverse-spec/            # 역기획 정책서 스킬
│   ├── SKILL.md
│   ├── reference.md         # 공통 코드 파싱 규칙
│   └── scripts/             # extract.py(사실 추출) · flowgen.py(흐름 SVG) · render.py(PDF/HTML/DOCX)
├── reverse-prd/             # 역기획 PRD 스킬 (구조 동일)
│   ├── SKILL.md
│   ├── reference.md
│   └── scripts/
├── docs/
│   └── skill-mcp-review.md  # 공식 문서 기반 Skill/MCP 준수 리뷰
├── tools/
│   ├── sync.sh              # 단방향 반영: 정본 reverse-prd → reverse-spec
│   └── check-sync.sh        # 공유 파일 사본 일치 검증 스크립트 (CI에서도 실행)
├── tests/                   # 동봉 스크립트 회귀 테스트 (CI에서 실행)
└── examples/
    ├── mock-shop/           # 데모용 목 e-커머스 앱 (React Router)
    ├── reverse-prd-output/  # mock-shop PRD 샘플 (PDF+HTML 쌍, 본문 md, flow JSON/SVG)
    ├── review-output/       # 리뷰 리포트 PDF+HTML 쌍
    └── hybrid-demo/         # 하이브리드 추출 개념 증명 (결정성 데모)
```

> `reference.md`와 `scripts/` 3종은 두 스킬에서 **동일 사본**으로 유지된다(스킬은
> `${CLAUDE_SKILL_DIR}`로 자기 디렉토리 내부 파일만 참조하므로). **정본은 `reverse-prd`
> 쪽이다** — 수정은 reverse-prd에서 하고 `bash tools/sync.sh`로 reverse-spec에 반영한다.
> 일치 여부는 커밋 전 `bash tools/check-sync.sh` 및 CI(`.github/workflows/`)가 검증하고,
> 회귀 테스트(`tests/`)도 CI에서 함께 돈다.

---

## 현재 검증 상태

`extract.py`의 결정성은 동봉된 mock-shop 예제(해시 검증)에서만 증명되었다. 정규식
기반이라 Next.js/Nuxt 파일 기반 라우팅, Vue `<script setup>`, CSS-in-JS, 비표준 상태관리
패턴은 놓칠 수 있다 — `reference.md` 1-I의 "추출 통계가 비정상적으로 낮을 때" 경고 절차
참조. 대형 코드베이스 분할 모드는 절차로만 작성되었고 실제 30개 초과 프로젝트에서
실행해본 적은 없다. 실제 코드베이스에 돌려보고 추출 통계가 합리적인지 먼저 확인한 뒤,
초안 이상의 용도로 신뢰하기 바란다.

## 참고

- 공식 문서 기반 준수 리뷰: [`docs/skill-mcp-review.md`](docs/skill-mcp-review.md)
- 샘플 출력 미리보기: `examples/reverse-prd-output/reverse_prd_mock-shop_sample.html`
