# 공식 문서 기반 Skill / MCP 리뷰

> 대상: `reverse-spec/SKILL.md`, `reverse-prd/SKILL.md`
> 기준 문서(공식): `code.claude.com/docs/en/skills.md`, `.../commands.md`, `.../mcp.md`
> 작성일: 2026-06-23 · **최신화: 2026-07-02** (8장 "현행 구조 스냅샷"에 이후 변경 반영)

/ 검토 범위: SKILL.md 프론트매터 스펙 준수 여부, 디렉토리 구조, `allowed-tools` 포맷,
MCP 도구 사용/표기 규칙. 공식 프론트매터 필드 표를 기준선으로 사용했다.

---

## 1. 요약 (Verdict)

| 항목 | 판정 |
|------|------|
| 프론트매터 필드 유효성 | ✅ 통과 — 사용된 필드(`name`, `description`, `argument-hint`, `allowed-tools`) 모두 공식 스펙에 존재 |
| 잘못된/비공식 필드 | ✅ 없음 — `allowedTools`(camelCase), `license`, `metadata` 등 비공식 필드 미사용 |
| 디렉토리 구조 | ✅ 통과 — `skill-name/SKILL.md` 규칙 준수 |
| `allowed-tools` 포맷 | ✅ 통과 — 콤마 구분 문자열 + `Bash(pattern)`는 공식 지원 포맷 |
| `$ARGUMENTS` 사용 | ✅ 통과 — 공식 치환 변수 |
| MCP 도구 표기 | ✅ 해당 없음 — MCP 도구를 쓰지 않으며, 현 기능상 불필요 (아래 5장 참조) |

**결론: 두 스킬은 공식 SKILL.md 스펙을 준수한다.** 차단성 결함(blocking)은 없고,
아래는 개선 권고(권장/정보성) 항목이다.

---

## 2. 필드별 검증 (공식 프론트매터 표 대조)

공식 문서: *"All fields are optional. Only `description` is recommended so Claude knows when to use the skill."*

| 필드 | 현재 값 | 공식 스펙 | 판정 |
|------|---------|-----------|------|
| `name` | `reverse-spec` / `reverse-prd` | 선택. **디렉토리 기반 스킬에서는 커맨드명이 디렉토리명에서 결정**되고, `name`은 plugin-root SKILL.md에서만 권위를 가짐 | ⚠️ 동작상 무시됨(장식용). 디렉토리명과 일치하므로 무해 |
| `description` | 트리거 문구 포함 한국어 설명 | **권장 필드.** 평문, listing에서 1,536자에서 잘림. 핵심 use case를 앞에 | ✅ 양호 (분량 충분히 짧음, 트리거 포함) |
| `argument-hint` | `<파일_또는_디렉토리_경로> [--format ...]` | 선택. 자동완성 시 표시되는 평문 힌트 | ✅ 유효 |
| `allowed-tools` | (최초 리뷰 시) `Bash(python *)` 등 광범위 → (현행) 스크립트 경로 한정 패턴, 8장 참조 | 선택. 공백/콤마 구분 문자열 또는 YAML 리스트. `Bash(git add *)` 형태 패턴 허용 | ✅ 포맷 유효 (보안 권고 R-2 적용 완료) |

YAML folded scalar(`>`)로 작성된 `description`/`allowed-tools`는 단일 문자열로 접히며,
콤마 구분 문자열은 공식이 허용하는 포맷이라 문제없다.

---

## 3. 디렉토리 / 활성화 위치

- 현재: `reverse-spec/SKILL.md`, `reverse-prd/SKILL.md` (저장소 루트)
- 공식 프로젝트 스킬 경로: `.claude/skills/<dir>/SKILL.md`,
  개인 스킬 경로: `~/.claude/skills/<dir>/SKILL.md`

**권고 (R-1) — ✅ 적용됨:** 이 저장소는 스킬을 **배포/수집**하는 컬렉션 성격이라 루트 배치는 합리적이다.
다만 이 스킬을 **실제로 활성화**하려면 `.claude/skills/` 아래에 있어야 자동 로드된다.
README에 설치 경로(예: `cp -r reverse-prd ~/.claude/skills/`)를 명시하거나,
프로젝트 내 활성화가 목적이면 `.claude/skills/`로 이동할 것.

---

## 4. `allowed-tools` 보안 관점

공식 정의: *"Tools Claude can use **without per-use approval** while skill is active."*
즉 `allowed-tools`에 올린 도구는 스킬 활성 동안 **개별 승인 프롬프트 없이** 실행된다.

- `Bash(pip install *)`, `Bash(python *)`는 사실상 **임의 코드 실행을 사전 승인**하는 셈이다.
- PDF/docx 생성을 위해 기능상 필요하긴 하나, 광범위한 권한이다.

**권고 (R-2) — ✅ 적용됨:**
- 의도된 동작임을 SKILL.md 또는 README에 명시 (사용자가 권한 범위를 인지하도록).
- 가능하면 범위를 좁힌다. 예: 생성 스크립트를 `scripts/`로 분리하고
  `Bash(python */scripts/render.py *)` 형태로 한정 (아래 R-3 참조).
  **주의:** `${CLAUDE_SKILL_DIR}` 치환은 스킬 **본문에서만** 동작하며 프론트매터
  `allowed-tools`에서는 확장되지 않는다(리터럴 문자열로 취급되어 어떤 명령과도 매칭 안 됨).
  따라서 허가 패턴에는 경로 와일드카드를 사용해야 한다.
- `pip install`은 사전 설치를 전제하면 제거 가능 (런타임 설치 회피).

---

## 5. MCP 리뷰

**현황: 두 스킬 모두 MCP 도구를 참조하지 않는다. 그리고 현 기능 범위에서는 그게 맞다.**
역기획 문서 생성은 로컬 파일 읽기 + 로컬 PDF/docx 생성으로 완결되므로 외부 MCP 서버가 불필요하다.

향후 산출물을 외부 시스템에 게시(예: Confluence/Notion/Jira/Slack)하도록 확장한다면,
공식 MCP 도구 표기 규칙을 따라야 한다:

- 표준 MCP 서버: `mcp__<server-name>__<tool-name>` (예: `mcp__github__create_pr`)
- 플러그인 번들 MCP 서버: `mcp__plugin_<plugin-name>_<server-name>__<tool-name>`
  (`A-Z a-z 0-9 _ -` 외 문자는 `_`로 치환)

이때 해당 도구를 `allowed-tools`에 풀네임으로 추가한다. 예:

```yaml
allowed-tools: >
  Read, Glob, Bash(python *),
  mcp__notion__create_page, mcp__confluence__create_content
```

**권고 (R-4):** 지금은 MCP 미사용이 적절. 외부 게시 기능을 넣을 때만 위 표기를 도입.

---

## 6. 구조 개선 권고 (선택)

**권고 (R-3) — ✅ 적용됨:** (이전) PDF/docx 생성 Python 코드가 SKILL.md 본문에 인라인으로 있었다.
공식 문서는 실행 스크립트를 `scripts/`에 두고 `${CLAUDE_SKILL_DIR}`로 참조하는
"supporting files" 구조를 권장한다. 분리 시 이점:

- SKILL.md가 가벼워져 모델이 지침을 더 잘 따른다.
- `allowed-tools`를 `Bash(python */scripts/render.py *)`로 좁혀 R-2 보안 권고도 충족.
  (프론트매터는 `${CLAUDE_SKILL_DIR}`를 확장하지 않으므로 경로 와일드카드 패턴 사용.)

현행 구조 (적용 결과):

```
reverse-prd/                 # reverse-spec도 동일 구조
├── SKILL.md
├── reference.md             # 1-A~1-H 공통 파싱 규칙 (reverse-spec과 동일 사본)
└── scripts/
    ├── extract.py           # 결정적 사실 추출기 (1-A~1-H 구현, --emit-flow)
    ├── flowgen.py           # 유저플로우 SVG 생성기 (HTML·PDF 겸용)
    └── render.py            # Markdown → PDF+HTML(기본 쌍) / DOCX 렌더러
```

**권고 (R-5) — ✅ 적용됨:** (이전) `reverse-spec`과 `reverse-prd`의 Step 1(코드 파싱) 로직이 중복이었다.
공통 `reference.md`로 분리하고 양쪽 SKILL.md에서 참조하면 유지보수성이 오른다.

---

## 7. 액션 아이템 정리

| ID | 구분 | 내용 | 우선순위 |
|----|------|------|----------|
| R-1 | ✅ 적용됨 | README에 설치 경로(`~/.claude/skills/` · `.claude/skills/`)·사용법·구조 명시 | 중 |
| R-2 | ✅ 적용됨 | `allowed-tools`를 `Bash(python */scripts/render.py *)` 로 축소, `pip install`도 패키지 한정 | 중 |
| R-3 | ✅ 적용됨 | 인라인 Python을 `scripts/render.py`로 분리, `${CLAUDE_SKILL_DIR}` 참조로 호출 | 중 |
| R-4 | 정보 | MCP는 외부 게시 확장 시에만 `mcp__server__tool` 표기로 도입 | 하 |
| R-5 | ✅ 적용됨 | Step 1 공통 파싱 로직을 `reference.md`로 분리, 양쪽 SKILL.md에서 `${CLAUDE_SKILL_DIR}/reference.md` 참조 | 하 |
| — | 정보 | `name` 필드는 장식용(무해). 제거해도 됨 | 하 |

> **적용 이력 (2026-06-26):** R-2·R-3·R-5는 리팩터링으로 반영됨 — 두 스킬이
> `reference.md`(공통 파싱)와 `scripts/render.py`(공통 렌더러)를 공유하고,
> `allowed-tools`는 스크립트 경로로 한정됨. R-1은 저장소 `README.md`로 충족.
> R-4(MCP)는 현 기능상 불필요하여 정보성으로 유지.
>
> **정정 (2026-07-02):** 최초 R-2 적용 시 사용한 `Bash(python ${CLAUDE_SKILL_DIR}/scripts/*)`
> 패턴은 프론트매터에서 변수가 확장되지 않아 **어떤 명령과도 매칭되지 않는 사문**이었다
> (fail-closed — 보안 문제는 아니나 사전 승인 효과 없음). 공식 permissions 문서의
> 와일드카드 시맨틱(`*`는 공백 포함 임의 문자열 매칭)에 따라
> `Bash(python */scripts/render.py *)` 로 교체하여 실제로 매칭되는 최소 패턴으로 정정함.

---

## 8. 현행 구조 스냅샷 (2026-07-02 기준)

최초 리뷰(6장까지) 이후 반영된 변경 사항의 요약. 상세 이력은 git log 참조.

**하이브리드 파이프라인 (파서 우선)**

| 단계 | 담당 | 스크립트 | 성질 |
|------|------|----------|------|
| 사실 추출 (1-A~1-H) | 파서 | `scripts/extract.py` | 결정적 — 같은 코드 → 같은 사실 표 (SHA-256 검증) |
| 유저플로우 다이어그램 | 파서+LLM | `scripts/flowgen.py` | 스켈레톤은 파서, 라벨·`[추정]` 점선은 LLM 보강 |
| 해석·서술 (Step 2~3) | LLM | — | 사실 표 밖 내용 도입 금지 원칙 |
| 렌더링 | 파서 | `scripts/render.py` | **PDF+HTML 쌍 기본** (`--format pdf,html`), DOCX 옵션 |

**현행 `allowed-tools` (두 스킬 공통)**

```
Read, Glob, Write, Bash(find *), Bash(ls *),
Bash(pip install weasyprint *), Bash(pip install markdown *), Bash(pip install python-docx *),
Bash(python */scripts/render.py *), Bash(python */scripts/flowgen.py *), Bash(python */scripts/extract.py *),
Bash(python3 */scripts/render.py *), Bash(python3 */scripts/flowgen.py *), Bash(python3 */scripts/extract.py *),
Bash(pip3 install weasyprint *), Bash(pip3 install markdown *), Bash(pip3 install python-docx *)
```

- `python3`/`pip3` 변형은 macOS(스톡 환경에 `python` 부재) 대응.
- 여전히 임의 Python 실행은 사전 승인되지 않음 — 동봉 스크립트 3종만 허용.

**대형 코드베이스 분할 모드**

- Step 0에서 소스 30개 초과 판정 시, 모듈 단위로 서브에이전트에 extract.py 실행을
  위임(격리 컨텍스트, 사실 표만 회수) 후 병합. 공식 sub-agents/large-codebases 패턴.

**문서 목차 확장**

- 에러/메시지 카탈로그(문구 원문 보존), 상태 관리 & 데이터 흐름, 외부 연동 인벤토리,
  이벤트/트래킹 명세(KPI 근거 연결), As-Is 스냅샷(커밋 해시 기준선), 추적성 매트릭스.

**플랫폼 안내 (README·SKILL.md 4-C)**

- Windows PDF: MSYS2 + `pacman -S mingw-w64-ucrt-x86_64-pango` (WeasyPrint 공식 권장),
  실패 시 `--format docx,html` 폴백. macOS: `brew install weasyprint`.

**공유 사본 관리**

- `reference.md` + `scripts/` 3종은 두 스킬에 동일 사본 — `tools/check-sync.sh`로 검증.

---

## 9. 검증 상태 — 무엇이 실제로 증명됐고 무엇이 아직인가 (2026-07-02)

과대평가를 막기 위해, "구현됨"과 "실전 검증됨"을 구분해 명시한다.

| 항목 | 증명된 것 | 아직 증명 안 된 것 |
|------|-----------|---------------------|
| `extract.py` 결정성 | mock-shop(6파일)에서 2회 실행 SHA-256 동일 | **실전 코드베이스에서의 커버리지** — 정규식 기반이라 Next.js 파일 라우팅, Vue `<script setup>`, CSS-in-JS, 비표준 상태관리 패턴은 놓칠 수 있음 (`reference.md` 1-I) |
| 분할 모드(대형 코드베이스) | SKILL.md에 절차로 명문화, 공식 sub-agents 패턴 근거 | **30개 초과 실제 프로젝트에서 실행된 적 없음** — 모듈 분할 기준, 병합 로직의 실전 판단 미검증 |
| 전체 파이프라인(extract→flowgen→render) | 개별 스크립트 3종 각각 CLI로 직접 실행해 동작 확인 | **Claude Code가 SKILL.md를 읽고 실제로 이 순서를 트리거하는 end-to-end 실행은 미실행** — 스크립트는 맞아도 스킬 지침이 의도대로 유도하는지는 별개 |

**권고**: 조직 표준 도구로 채택하기 전에, 실제 사내 코드베이스 1~2건에 그대로 실행해
`extract.py`의 추출 통계가 합리적인지(라우트/컴포넌트 수가 코드 규모와 맞는지) 확인할 것.
비정상적으로 낮으면 1-I의 파서 커버리지 경고 절차가 트리거되는지도 함께 확인한다.

---

## 10. 코드 감사 결과 및 수정 이력 (2026-07-05)

`reverse-spec`/`reverse-prd`(및 자매 스킬 `reverse-backend`)의 실전 검증 과정에서
발견된 코드/구조 문제를 감사하고 수정했다. 모든 수정은 mock-shop 2회 실행 SHA-256
동일(결정성 유지) + 전체 렌더 파이프라인(PDF/HTML/DOCX) 재검증을 거쳤다.

| # | 문제 | 심각도 | 수정 내용 |
|---|------|--------|-----------|
| 1 | DOCX 테이블에서 `\|` 이스케이프 처리가 HTML/PDF와 DOCX 경로에서 서로 달라, 조건문에 `\|\|`(JS 논리 OR)가 있으면 DOCX 테이블의 뒤 컬럼(근거 파일 등)이 통째로 사라짐 | 높음 (데이터 유실) | `extract.py`에 `_escape_cell()`(백틱 값은 이스케이프 생략), `render.py`에 백틱·이스케이프 인식 `_split_table_row()` 도입. HTML의 백슬래시 노출 버그도 함께 해소 |
| 2 | `reverse-backend`에서 발견한 "주석 처리된 죽은 코드를 활성 정책으로 오탐" 버그가 프론트엔드용 `extract.py`에는 이식되지 않은 채 남아있었음 | 높음 (오탐) | `_blank_full_line_comments()` 추가 (`//`, 한 줄 HTML 주석 제외) 후 `read_sources()`에 적용 |
| 3 | `fetch(...)`와 `if (...)` 정규식이 중첩 괄호(예: `.test(email)`, `JSON.stringify({...})`)에서 조기 매칭 종료 — 실제로 mock-shop의 이메일 정규식 검증 규칙이 이 버그로 누락되고 있었음 | 중간 (실측 정확도) | `_find_matching_paren()`(괄호 카운팅)으로 두 곳 모두 교체. 부수효과로 `extract_rules`/`extract_messages`의 중복 로직을 `_find_if_return_pairs()`로 통합(#6 해소) |
| 4 | `flowgen.py`의 SVG `viewBox` 높이가 역방향(복귀) 엣지의 우회 경로 좌표와 별개 공식으로 계산돼, 노드가 많으면 엣지가 캔버스 밖으로 잘릴 수 있었음 | 낮음 | 엣지 지오메트리를 먼저 계산해 실제 필요 높이를 구한 뒤 viewBox를 확정하도록 재구성 |
| 5 | `reference.md`가 "민감 정보는 경고로 표시"라고 선언하지만 프론트엔드 `extract.py`에는 이를 강제하는 스캔 로직이 없었음 (원칙과 구현의 불일치) | 중간 | `reverse-backend`의 검증된 시크릿 스캔 로직(`extract_secret_findings`)을 이식 — `reference.md` 1-J로 등록, 값은 절대 출력하지 않고 파일 경로·패턴 종류·git 추적 여부만 보고 |
| 6 | `extract_rules`/`extract_messages`가 동일 정규식을 독립 구현해 한쪽만 고치면 drift 발생 | 낮음 (구조) | #3 수정 과정에서 `_find_if_return_pairs()`로 통합해 해소 |
| 7 | `flowgen.py`에 노드 수 상한이 없어 대형 코드베이스에서 거대한 SVG가 만들어질 수 있었음 | 낮음 | `MAX_NODES = 60` 상한 추가, 초과 시 잘라내고 stderr 경고 |

모든 항목은 `reverse-prd/scripts/`에서 수정 후 `reverse-spec/scripts/`로 동기화,
`tools/check-sync.sh` 통과 확인. 저장소에 커밋된 샘플(mock-shop PRD, flow SVG)은
수정 전후 바이트 단위로 동일함을 확인해 재생성하지 않았다(회귀 없음의 증거).

---

## 11. 재점검 결과 — 트레일링 주석 사각지대 발견·수정 (2026-07-07)

10장의 #2(주석 처리된 죽은 코드 오탐 방지) 수정을 재점검하는 과정에서, 그 수정
자체의 사각지대를 추가로 발견해 수정했다.

**발견**: `_blank_full_line_comments()`는 한 줄 전체가 `//`로 시작하는 경우만
다뤘다. 실제로는 `코드; // 주석` 형태의 **트레일링(줄 끝) 주석**이 통째로 주석인
경우보다 훨씬 흔한데, 이 경우 주석 안에 쓰인 가짜 코드가 여전히 오탐될 수 있었다.
재현: `doRealThing(); // fetch("/api/fake-endpoint") 참고용 예시` 같은 줄에서
주석 안의 `/api/fake-endpoint`가 실제 API 호출처럼 추출됨.

**1차 수정**: 공백 뒤에 오는 `//`를 트레일링 주석 시작으로 보고 그 지점에서
라인을 잘라내도록 추가 (공백 없는 `https://`, `//cdn.example.com/...` 프로토콜
상대 URL은 보존).

**1차 수정의 회귀**: mock-shop 회귀 테스트에서 API 추출 수가 2→1로 감소.
원인 추적 결과, `await login(email, password); // POST /api/auth/login`처럼
**의도적으로 남겨둔 API 문서화 주석**(코드가 헬퍼 함수로 추상화돼 있어 실제
엔드포인트가 주석으로만 남아있는 경우)까지 트레일링 주석으로 오인해 함께
잘라내고 있었다. `extract_api_calls`의 전용 패턴은 원래 이런 주석 안의 API
표기를 **의도적으로** 찾도록 설계된 것이었다.

**최종 수정**: 죽은 코드(실제 JS 문법)와 `// GET|POST|PUT|PATCH|DELETE /path`
형태의 의도적 문서화 표기(유효한 JS 문법이 아닌 순수 주석 규칙)를 구분하는
`_API_ANNOTATION` 정규식을 추가해, 후자는 전체 줄/트레일링 주석 제거 대상에서
모두 예외 처리했다.

**검증**: mock-shop 재실행 결과 가짜 트레일링 API는 여전히 안 잡히고, 의도된
API 문서화 주석 2건(로그인·주문 엔드포인트)은 정상 복원, 2회 실행 해시 동일
(결정성 유지), PDF/HTML/DOCX 파이프라인 재검증 통과.

> 교훈: 오탐 방지 수정 자체가 새로운 종류의 오탐/누락을 만들 수 있다 — 특히
> "주석을 지운다"처럼 광범위한 전처리는 그 주석을 의도적으로 읽는 다른 기능과
> 충돌할 수 있으므로, 수정 후에도 다른 추출 항목에 회귀가 없는지 전체 통계를
> 반드시 재확인해야 한다.

---

## 12. 멀티에이전트 코드 감사 결과 및 수정 (2026-07-08)

5개 관점(정확성·보안·결정성·일관성·렌더링)의 에이전트가 병렬로 코드를 검토하고,
각 발견을 2인 독립 에이전트가 재검증(refute 투표)했다 — 총 83개 에이전트, 39건 발견
→ **36건 확정 / 3건 기각**. 확정 항목을 우선순위대로 전부 수정했다. 모든 수정은
mock-shop 2회 실행 SHA-256 동일(결정성 유지) + PDF/HTML/DOCX 파이프라인 재검증을 거쳤다.

**HIGH — 정확성 (extract.py)**
- `if (cond) { return "…" }` 중괄호 블록형 early-return 미매칭 → `_find_if_return_pairs`가
  `{` 블록·단따옴표·템플릿 리터럴까지 인식하도록 개선(extract_rules/extract_messages 공용).
- `useContext(ctx)`/`useSelector(fn)` 등 **인자 있는 훅 전량 누락** → 인자 유무·구조분해/
  단일변수 무관하게 포착.
- JSX `<Route element={<RequireAuth…}>` 가드 미스트리핑(컴포넌트를 RequireAuth로,
  보호를 public으로 오보고) → `_component_and_guard` 헬퍼로 createBrowserRouter 경로와
  통합, 래퍼(RequireAuth/Layout 등) 건너뛰고 실제 페이지 컴포넌트 선택.
- vue-router 정규식이 `meta:{…}` 중첩·lazy import에서 매칭 실패 → 개선.
- named export/import 컴포넌트(`export const Foo`, `import { Foo }`) 전량 누락 → 포착.

**HIGH — 보안**
- render.py 출력 HTML 미정제(저장형 XSS): 추출 문자열의 `<img onerror=…>`가 그대로
  실행될 수 있었음 → `_escape_cell`이 백틱 밖 텍스트의 `<>&`를 HTML 이스케이프,
  DOCX 경로는 `_clean_inline`이 리터럴로 복원.
- weasyprint가 `file://` 로컬 파일 fetch 허용(정보 노출) → `_pdf_url_fetcher`로 file: 차단.
- extract.py가 심볼릭 링크를 따라가 저장소 밖 파일 읽기 → `_walk_safe_files`로 심링크
  스킵 + resolve() 경로가 root 하위인지 검증.

**HIGH — 결정성/일관성/렌더링**
- 스냅샷 축약 해시 `%h` → 전체 해시 `%H` (clone/설정 무관 결정성).
- reference.md 1-A~1-G의 문서-코드 불일치 → ⚙️(파서 자동)/✍️(LLM 보완) 구분을
  전 항목에 표기해 정직하게 정합. 1-J를 1-I 뒤로 재배치.
- `_split_table_row` 이중 백틱(``code``) 오파싱으로 컬럼 소실 → 백틱 런 길이 매칭.
- DOCX 헤딩 `#{1,4}` → `#{1,6}` (H5/H6 강등 수정).

**MEDIUM/LOW (요약)**
- 트래킹 벤더+generic 이중매칭 제거(first-match-wins) · `disabled={}` 중첩 중괄호
  브레이스 매칭 · JSX 줄바꿈 텍스트/조건부 문자열 포착 · axios 인스턴스 호출 포착 ·
  음수 상수 · min/max 순서·인접 무관 · `.env*` 변형/`.vue` 시크릿 스캔 포함 ·
  번호목록/중첩리스트 스타일 · 링크/이미지/취소선 평문화 · `<br>` DOCX 개행 ·
  flowgen 고립 사이클 노드를 진입 컬럼과 분리 · 정렬 tie-break 키 보강 ·
  argument-hint에 `html` 추가.

**기각 3건**: git subprocess timeout 비결정성(발동 비현실적) · flowgen 복수 진입점
depth(문서화된 의도된 설계) · render.py argparse 기본값(항상 명시적 인자 전달로 무영향).

> 이번 감사의 핵심 패턴: "한 곳에서 고친 버그가 형제 코드 경로엔 미적용"(중첩괄호·
> 가드 스트리핑)이 반복 확인됨. 단일 헬퍼로 통합해 재발 방지.

---

## 13. 재점검 — 잔존 보안 리스크 수정 (2026-09-15)

§12에서 고친 HIGH급 XSS/LFI/심링크 탈출 외에, "신뢰 못 할(적대적일 수 있는) 코드를
분석한다"는 이 도구의 전제를 다시 짚어 남아 있던 리스크를 우선순위대로 수정했다.
전부 mock-shop 2회 실행 SHA-256 동일(결정성 유지) 확인 후 반영.

**MEDIUM — SSRF (render.py `_pdf_url_fetcher`)**
- §12 수정은 `file://`만 막고 `http(s)://`는 전부 허용해, 분석 대상 코드의 문구가
  본문 서술(표 밖)에 이스케이프 없이 섞이면 `<img src="http://169.254.169.254/...">`
  같은 태그로 클라우드 메타데이터/내부망 엔드포인트에 접근할 여지가 있었다.
  → 블랙리스트(`file:` 차단)를 화이트리스트(`https` + `fonts.googleapis.com` /
  `fonts.gstatic.com`만 허용, 그 외 스킴·호스트 전부 거부)로 교체.
  내부망 IP·임의 외부 도메인 모두 실제 차단 확인.

**MEDIUM — 표 밖 서술문 저장형 XSS (render.py `build_html`)**
- `_escape_cell`은 extract.py가 만드는 `facts.md`의 표 셀에만 적용돼, LLM이
  Step 2/3에서 메시지 원문을 표가 아닌 본문 서술로 옮겨 적으면 그 경로는
  이스케이프되지 않았다(프롬프트 지침에만 의존). → 렌더링 최종 단계에
  방어선을 추가: `<script>/<iframe>/<style>` 등 실행 가능한 태그 제거,
  실제 태그 안의 `on*=` 이벤트 속성 제거, `javascript:`/`data:text/html` 스킴
  무력화. **재검증 중 자체 발견**: 이벤트 속성 정규식을 문서 전체에 바로
  적용했더니 코드스팬 안의 이스케이프된 예시 문구(`&gt;` 등)까지 먹어치워
  원문이 훼손되는 회귀가 생겼음 — 실제 태그(`<...>`) 구간에서만 동작하도록
  범위를 좁혀 코드스팬 텍스트는 전혀 건드리지 않게 수정.

**LOW/MEDIUM — 경로 조작 (render.py `--name`)**
- `--outdir`/`--name`을 검증 없이 그대로 경로에 이어붙였다. 이 스크립트는
  에이전트가 분석 대상 코드/문서 내용을 바탕으로 다음 Bash 호출 인자를 스스로
  구성하는 흐름에서 호출되므로, 프롬프트 인젝션으로 `--name`에 `../../` 같은
  값이 흘러들 가능성을 전제로 방어. → `--name`에서 디렉터리 구성요소를 제거해
  순수 파일명만 남기고, 정규화됐으면 stderr에 경고.

**LOW — ReDoS/리소스 소모 (extract.py `read_sources`)**
- 정규식 기반 파서는 비정상적으로 거대한 단일 파일(실수로 포함된 번들, 또는
  의도적으로 심어진 파일)과 결합하면 CPU를 과도하게 소모할 수 있었다(파일
  크기 상한 없음). → 2MB 초과 파일은 분석에서 제외하고 stderr에 경고.

**보류 (코드로 강제하지 않음)**: 생성 HTML의 Google Fonts `@import`는 문서를 열
때마다 외부로 요청이 나가는 경미한 정보 흐름이나, 시각 디자인과 맞바꿀 만큼
심각하지 않다고 판단해 이번엔 손대지 않음.

### 13.1 PR 리뷰봇(codex) 재점검에서 발견된 §13 자체 버그 2건 (2026-09-15)

PR #1에 올린 §13 수정 직후 자동 리뷰봇이 그 수정 코드 자체에서 P1 2건을 찾아냈고,
둘 다 재현 후 확정해 수정했다.

- **`_DANGEROUS_TAGS`의 초선형(superlinear) 백트래킹**: 여는/닫는 태그를 `.*?`로
  통째 페어 매칭하던 방식이, 닫히지 않는 `<script>` 토큰이 반복되는 입력에서
  시작 위치마다 나머지 문서 전체를 훑어 극도로 느려졌다 — `<script>` 1,000회
  반복(~8KB)만으로 12초 이상 소요를 실측 재현(스크립트 실행 차단을 위해 추가한
  코드 자체가 새로운 CPU DoS 벡터가 된 아이러니한 사례). 여는/닫는 태그를
  각각 `[^>]*`로 개별적으로만 제거하도록 바꿔, 매 매치 폭이 다음 `>` 하나로
  고정되는 선형 시간 패턴으로 교체 — 1,000회 반복 0.0002초, 20,000회 반복도
  0.004초로 확인.
- **`_DANGEROUS_SCHEME_ATTR`의 따옴표 필수 조건 우회**: 속성값이 따옴표로
  감싸인 경우만 매칭해, `href=javascript:alert(1)`처럼 따옴표 없는 값은 그대로
  통과했다(python-markdown은 raw HTML을 그대로 두므로 브라우저에서 클릭 시
  실행됨) — 따옴표를 선택 사항으로 바꿔 양쪽 형태 모두 무력화하도록 수정.

두 수정 모두 코드스팬 텍스트 보존(§13 1차 수정의 회귀 방지책)과 mock-shop
결정성(2회 실행 해시 동일)을 재검증한 뒤 반영.

### 13.2 정규식 새니타이저 폐기 — HTMLParser 기반으로 재작성 (2026-09-15)

§13.1 수정을 올리자 같은 리뷰봇이 **같은 수정 코드에서 또 P1 3건**을 찾아냈다 —
정규식으로 태그 경계를 직접 흉내 내려는 접근 자체가 계속 우회를 만들어내는
패턴이 뚜렷해져, 패치를 더 쌓는 대신 구현을 표준 라이브러리의 실제 HTML
파서(`html.parser.HTMLParser`, 신규 의존성 없음)로 교체했다.

- **여전히 남은 이차식(quadratic) 시간**: §13.1에서 "태그를 개별적으로 다음 `>`
  까지만 지운다"로 바꿨지만, `>`가 아예 없는 `<script` 접두어가 대량 반복되면
  매 시작 위치마다 나머지 문서 끝까지 스캔하다 실패하는 패턴이 남아 있었다 —
  32,000회 반복(~224KB)에서 약 4.6초 재현.
- **따옴표 속성값 안의 `>`로 태그 경계 조작**: `<img src=x title=">" onerror=alert(1)>`
  처럼 따옴표 안에 `>`가 있으면 `[^<>]*` 기반 태그 경계 탐지가 거기서 끊겨
  `onerror`가 "태그 밖"으로 빠져나가 정리되지 않고 그대로 남았다.
- **HTML 문자 참조로 인코딩한 스킴 우회**: `href="jav&#x61;script:alert(1)"`는
  브라우저가 문자 참조를 디코딩한 뒤 스킴을 판정해 실행하지만, 리터럴 문자열
  `javascript:`만 찾는 정규식은 인코딩된 형태를 못 잡았다.

세 문제 모두 "정규식으로 태그 경계·인용부호·엔티티 디코딩을 직접 재구현하려
한 것"이 근본 원인이었다. `_sanitize_html_fragment`를 `HTMLParser` 서브클래스
(`_HtmlSanitizer`)로 전면 재작성: 위험 태그(`script/iframe/object/embed/style/link`)는
내용까지 통째로 버리고, 남는 태그는 `on*=` 속성 제거·URL 스킴 정규화(제어문자
제거 후 접두어 비교 — HTMLParser가 속성값의 문자 참조를 파싱 시점에 이미
디코딩해 넘겨준다) 후 재직렬화한다. `convert_charrefs=False`로 두어 일반
텍스트(코드스팬 등)는 엔티티 표기 그대로 보존해 원문 훼손을 방지했다.

재검증: 위 3건의 재현 케이스 모두 해결(1,000/32,000회 `<script>` 반복 각각
0.0001초/0.003초, 따옴표 우회·엔티티 우회 케이스 모두 무력화됨을 확인) +
기존 코드스팬 보존 회귀 테스트 + mock-shop 결정성(2회 해시 동일) + 전체
extract→render HTML 파이프라인 재실행으로 정상 렌더링 확인.

### 13.3 HTMLParser 전환 직후 발견된 P1 1건 + P2 1건 (2026-09-15)

§13.2를 올리자 같은 리뷰봇이 새 구현에서 다시 2건을 찾았다 — 하나는 보안(URL
속성 커버리지 부족), 하나는 심각한 데이터 유실 회귀(void 요소 처리 누락).

- **P1 — href/src 외 내비게이션 속성 미검사**: `<form action="javascript:...">`,
  `formaction`, SVG `xlink:href`처럼 URL을 담는 다른 속성은 스킴 검사 대상이
  아니어서 그대로 통과했다 — 재현 확인 후 `_URL_ATTRS`에
  `action/formaction/xlink:href/poster/background`를 추가.
- **P2 — void 요소가 skip_depth를 영구히 올려 이후 문서 전체가 사라짐**:
  `link`/`embed`는 HTML의 "빈 요소"(void element)라 애초에 닫는 태그가 없는데,
  이 구현은 명시적 `/>` 없이 온 `<link href=x>`를 "닫힘을 기다리는 위험 태그"로
  취급해 `_skip_depth`가 영원히 0으로 안 돌아왔다 — `before<link href=x>after`가
  `before`만 남기고 `after`를 통째로 삼켜버리는 실측 재현(보안 문제가 아니라
  치명적인 문서 유실 버그). HTML 표준 void 요소 목록(`area/base/br/col/embed/
  hr/img/input/link/meta/param/source/track/wbr`)을 두고, 이 목록에 속하면
  명시적 슬래시 유무와 무관하게 항상 self-closing으로 취급하도록 수정. 종료
  태그 쪽도 대칭적으로 방어(void 위험 태그의 `</...>`가 와도 무관한 depth를
  잘못 줄이지 않음).

재검증: 두 재현 케이스 모두 해결 + §13.1/13.2에서 확정한 모든 재현 케이스
재통과(ReDoS 2종·따옴표 우회·엔티티 우회·코드스팬 보존) + mock-shop 결정성
+ 전체 파이프라인 재실행.

### 13.4 파일 크기 상한 안에서도 남아있던 ReDoS + SVG 간접 속성 주입 (2026-09-15)

리뷰봇이 처음으로 **render.py가 아닌 extract.py**에서, 그리고 render.py에서는
`_URL_ATTRS` 확장 직후 다시 하나를 더 찾았다.

- **P1 — extract.py `extract_routes`의 JSX 라우트 정규식**: `element=\{(.*?)\}`의
  무경계 lazy 매칭이, MAX_FILE_BYTES(2MB) 상한 *안에 드는* 파일에서도 여전히
  이차식으로 느렸다 — 닫히지 않는 `<Route path="x" element={` 접두어를 반복한
  200KB 파일에서 12초 이상 실측(파일 크기 상한만으로는 이 특정 정규식의 최악
  케이스를 못 막는다는 지적). `element={...}` 내용 캡처를 4000자로 상한을 둔
  `(.{0,4000}?)`로 교체 — 실제 route JSX 블록은 보통 수백 자 이내라 정상 추출에는
  영향이 없고, 200KB 입력이 8.76초 → 0.32초로, 파일 크기 상한 한계치인 2MB
  입력도 3.2초로 줄어듦을 확인(정상 라우트 추출 결과는 동일함을 별도 검증).
- **P1 — render.py: SVG 애니메이션 요소를 통한 간접 속성 주입**: `_URL_ATTRS`
  확장 직후, `<animate attributeName="href" values="javascript:...">`처럼
  SVG SMIL 애니메이션으로 href 값을 *간접* 주입하는 경로가 남아 있었다 — 속성
  이름이 `href`/`src`가 아니라서 §13.3의 확장으로도 못 잡았다. 속성 이름/값
  조합을 추가로 흉내 내는 대신, `<animate>/<set>/<animateMotion>/
  <animateTransform>` 자체를 위험 태그 목록에 추가해 통째로 제거하는 쪽을
  택했다(SVG 스펙상 이 요소들은 빈 콘텐츠 모델이라 `_VOID_ELEMENTS`에도 함께
  추가해, §13.3에서 고친 것과 같은 "닫는 태그를 영원히 기다리는" 문제가 재발하지
  않도록 함).

재검증: 두 재현 케이스 모두 해결 + `<svg><set attributeName="href" to="javascript:...">`
같은 형제 케이스 + 슬래시 없이 닫힌 `<animate>`가 뒤 문서를 삼키지 않는지
(§13.3 회귀 방지) + 정상 라우트 추출 결과 불변 + mock-shop 결정성(2회 해시
동일) + 전체 extract→render 파이프라인 재실행.

### 13.5 "상한을 곱한 값"의 함정 + meta-refresh 리다이렉트 (2026-09-15)

§13.4를 올리자 리뷰봇이 다시 2건을 찾았다 — 하나는 §13.4 자체 수정이 근본
해결이 아니라 상수를 하나 더 곱한 것뿐이었다는 지적, 하나는 완전히 새로운
태그(`meta`)를 통한 공격.

- **P1 — extract.py: "발견당 4000자 상한"은 발견 횟수만큼 누적된다**: §13.4의
  수정은 각 `<Route ... element={` 발견을 독립적으로(최대 4000자까지) 재스캔하는
  구조를 유지한 채 상한만 걸었을 뿐이라, 접두어 반복 횟수가 늘면 "발견 횟수 ×
  4000"으로 비용이 계속 누적됐다 — 2MB 근처 입력에서 여전히 3초+, 그런 파일
  100개면 리뷰봇 추산으로 수 분. 이번엔 상한을 더 키우는 대신 **파일 전체를
  한 번만 좌→우로 훑는 단일 패스**로 바꿨다: 각 발견 지점에서 `_find_matching`
  (다른 추출기에서 이미 쓰는 괄호 깊이 카운팅 헬퍼)으로 대응하는 `}`를 찾고,
  다음 탐색은 그 지점부터 이어간다(이미 지나온 구간은 다시 훑지 않음). 닫는
  `}`를 못 찾으면(적대적으로 깨진 JSX) 그 지점에서 전체 탐색을 즉시 종료해
  재시도 스캔을 하지 않는다 — 정상적으로 닫힌 파일은 총 비용이 파일 길이에
  선형이고, 안 닫히는 접두어가 아무리 반복돼도 "한 번 훑고 포기"로 비용이
  고정된다. 2MB 입력 3.05초 → 0.11초, 같은 파일 10회 연속 처리도 1.1초로
  확인(100개 파일이면 수 분이 아니라 수 초대).
- **P1 — render.py: `<meta http-equiv="refresh" content="0;url=…">`로 즉시
  리다이렉트**: 이 태그는 `href`/`src` 류 속성이 아예 없이 `content` 값 하나로
  리더를 공격자 페이지로 강제 이동시킨다 — URL 속성 이름을 검사하는 방식으론
  원천적으로 못 잡는 패턴이라, `meta` 자체를 위험 태그 목록에 추가해 통째로
  제거했다(HTML 표준 void 요소라 이미 `_VOID_ELEMENTS`에도 있어 §13.3의 문서
  유실 문제도 재발하지 않음).

재검증: 두 재현 케이스 모두 해결(정상 다중 라우트 추출 결과 불변 확인 포함,
mock-shop 실제 라우트 추출도 재확인) + `<meta refresh>`가 뒤 문서를 삼키지
않는지 + mock-shop 결정성(2회 해시 동일) + 전체 파이프라인 재실행.

### 13.6 단일 패스 스캐너의 정확성 버그 — 문자열 안 리터럴 중괄호 (2026-09-15)

§13.5에서 만든 단일 패스 라우트 스캐너(`_iter_jsx_route_blocks` +
`_find_matching`)에 리뷰봇이 **보안이 아닌 정확성(P2)** 버그를 하나 더
찾았다 — 처음으로 이 시리즈에서 "익스플로잇"이 아니라 "멀쩡한 코드를 잘못
분석함"을 지적한 케이스다.

- 순수 괄호 카운팅은 JSX 속성값 문자열 안의 리터럴 `{`/`}` (예:
  `<Page label="{" />`)까지 깊이로 세어버린다. 재현해보니 이 경우 깊이가
  0으로 안 돌아와 `_find_matching`이 -1을 반환했고, §13.5에서 정한 "닫는 `}`를
  못 찾으면 전체 탐색 종료" 규칙 때문에 **이 파일의 라우트가 전부(뒤에 오는
  멀쩡한 라우트까지) 통째로 안 잡히는** 것을 확인했다 — 보안 문제는 아니지만
  추출 결과가 조용히 비어버리는 정확성 회귀.
- `_find_matching_skip_strings`를 새로 만들어, 큰따옴표/작은따옴표 문자열
  리터럴 안(백슬래시 이스케이프 포함)의 문자는 깊이 계산에서 제외하도록 했다.
  여전히 단일 좌→우 패스(문자당 O(1) 상태 추가)라 §13.4/13.5에서 잡은 이차식
  비용 문제는 재발하지 않는다. (템플릿 리터럴의 `${...}`나 정규식 리터럴 등
  더 복잡한 경우까지 완벽히 다루진 않음 — reference.md 1-I에 이미 문서화된
  파서 한계와 같은 성격.)

재검증: 재현 케이스(문자열 안 리터럴 `{`) 수정 후 두 라우트 모두 정상 추출 +
§13.4/13.5의 ReDoS 재현 케이스가 여전히 빠른지(2MB 근처 입력 ~0.2초) + 정상
다중 라우트 추출 + mock-shop 실제 라우트 8개 불변 + mock-shop 결정성(2회
해시 동일).

### 13.7 "무조건 따옴표=문자열"의 함정 — JSX 텍스트 안 아포스트로피 (2026-09-15)

§13.6 수정 직후 리뷰봇이 예상대로 그 수정의 반대쪽 빈틈을 찾았다: "따옴표는
무조건 문자열 구분자"로 바꾼 탓에, `<div>Don't stop</div>` 같은 **JSX 텍스트**
안의 아포스트로피까지 문자열 시작으로 오인해 §13.6과 똑같은 증상(닫는 `}`를
못 찾아 파일의 라우트가 전부 사라짐)이 재발함을 재현으로 확인했다.

JSX 텍스트는 JS 문자열이 아니라 따옴표에 아무 구분자 의미가 없다 — "따옴표가
나오면 무조건"이 아니라 **"`attr=` 바로 뒤(공백 허용)에 오는 따옴표만"** 문자열
시작으로 봐야 두 사례(§13.6의 속성값 안 리터럴 중괄호, §13.7의 텍스트 안
아포스트로피)를 동시에 만족한다 — JSX 속성 할당 문법과 실제로 일치하는 신호라
오탐이 훨씬 적다. `_find_matching_skip_strings`의 따옴표 판정에 "직전의 공백
아닌 문자가 `=`인가"를 추가 조건으로 넣어 수정.

재검증: §13.6/13.7 두 재현 케이스가 **같은 파일 안에 함께** 있어도(텍스트 안
아포스트로피 + 따옴표, 속성값 안 리터럴 중괄호가 섞인 3-라우트 케이스) 전부
정상 추출 + ReDoS 재현 케이스 여전히 빠름(~0.18초) + mock-shop 실제 라우트
8개 불변 + mock-shop 결정성(2회 해시 동일). 여전히 `=` 없이 오는 JS 문자열
리터럴(단순 `return 'x'` 등)이나 템플릿 리터럴까진 다루지 않는 잔여 한계가
있음을 PR 코멘트에 명시.

---

### 출처

- https://code.claude.com/docs/en/skills.md (프론트매터 필드 표, 디렉토리 구조, `${CLAUDE_SKILL_DIR}`)
- https://code.claude.com/docs/en/commands.md (커맨드↔스킬 통합, `$ARGUMENTS`)
- https://code.claude.com/docs/en/mcp.md (MCP 도구 네이밍 `mcp__server__tool`)
