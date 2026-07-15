---
name: reverse-prd
description: >
  코드(HTML/JS/TS/Vue/React)를 분석해서 역기획 PRD(제품 요구사항 문서, PDF 또는 docx)를
  자동 생성한다. 사용자가 "역기획 PRD", "PRD 만들어줘", "코드로 요구사항 문서",
  "기획 문서 역으로 뽑아줘" 등을 요청할 때 자동 실행. 인자로 파일 경로 또는 디렉토리를 받는다.
  정책 규칙 위주의 정책서가 필요하면 reverse-spec 스킬을 사용한다.
argument-hint: <파일_또는_디렉토리_경로> [--format pdf|docx|html] [--lang ko|en]
allowed-tools: >
  Read, Glob, Write,
  Bash(find *), Bash(ls *),
  Bash(pip install weasyprint *), Bash(pip install markdown *), Bash(pip install python-docx *),
  Bash(python */scripts/render.py *), Bash(python */scripts/flowgen.py *), Bash(python */scripts/extract.py *),
  Bash(python3 */scripts/render.py *), Bash(python3 */scripts/flowgen.py *), Bash(python3 */scripts/extract.py *),
  Bash(pip3 install weasyprint *), Bash(pip3 install markdown *), Bash(pip3 install python-docx *)
---

# reverse-prd — 코드 역기획 PRD 생성기

## 개요

완성된 코드를 거꾸로 분석해서, 그 코드가 구현하고 있는 **제품 요구사항(PRD)**을
재구성한다. `reverse-spec`(역기획 정책서)과 동일한 코드 분석 엔진을 사용하지만,
산출물은 "정책 규칙 명세"가 아니라 **"왜·누가·무엇을" 중심의 제품 기획 문서**다.

| 구분 | reverse-spec | reverse-prd (이 스킬) |
|------|--------------|------------------------|
| 산출물 | 역기획 정책서 (규칙/정책 중심) | 역기획 PRD (요구사항/목표 중심) |
| 핵심 질문 | "어떻게 동작하는가" | "무엇을 왜 만들었는가" |
| 주요 독자 | 개발/QA | PM/기획/디자인/이해관계자 |
| 핵심 산출 | 정책 규칙표, 화면 정책 | 목표·KPI, 페르소나, 사용자 스토리, 요구사항 |

분석 흐름은 4단계다.

- **Phase 1**: 코드 구조 파싱 (nav, route, component, function, class)
- **Phase 2**: 의미 분석 (사용자/목표 / 사용자 스토리 / 요구사항)
- **Phase 3**: PRD 문서 구조 자동 구성
- **Phase 4**: PDF 또는 docx 출력

## 실행 절차

### Step 0 — 입력 해석

```
인자: $ARGUMENTS
```

1. `$ARGUMENTS`에서 파일 경로 또는 디렉토리를 추출한다.
2. `--format` 플래그로 출력 형식 결정 (기본값: `pdf,html` 세트)
3. `--lang` 플래그로 문서 언어 결정 (기본값: `ko`)
4. 경로가 없으면 현재 디렉토리(`.`)를 대상으로 한다.
5. **규모 판정**: `find`로 대상 소스 파일 수를 센다. **30개 초과면 Step 1을
   "분할 모드"로 수행**한다 (Step 1의 분할 모드 절 참조).

파일 탐색 우선순위:

```
1순위: *.html (nav/routing 구조 포함 가능성 높음)
2순위: router.js / router.ts / routes.js / routes.ts
3순위: App.vue / App.tsx / index.js
4순위: src/ 하위 전체 컴포넌트
5순위: package.json / README (제품 의도·도메인 단서)
```

> README, package.json의 `description`, 폴더명, 커밋 메시지 등은 "제품 의도"를
> 추론하는 강력한 단서다. PRD의 배경/목표 섹션을 채울 때 우선 참고한다.

### Step 1 — 코드 파싱 & 구조 추출 (파서 우선)

사실 추출은 LLM이 아니라 동봉된 **결정적 추출기**가 담당한다 (같은 코드 → 항상 같은 사실).

```bash
python ${CLAUDE_SKILL_DIR}/scripts/extract.py <대상경로> --output reverse-prd-output/_facts.md --emit-flow reverse-prd-output/_flow.json
```

- `_facts.md`: 1-A~1-H 사실 표 (라우트/컴포넌트/API/상수/규칙/전환/문구/상태/연동/스냅샷).
  **문서의 사실 표(라우트 맵·API·메시지 카탈로그·컴포넌트 범위·As-Is 스냅샷)는
  이 출력을 그대로 사용**하고 임의로 고치지 않는다.
- `_flow.json`: 흐름도 스켈레톤 — Step 4-B에서 라벨·점선(`[추정]` 전환)을 보강해 사용.
- 추출 규칙 정의: `${CLAUDE_SKILL_DIR}/reference.md` (파서가 이 규칙을 구현).

**LLM 보완 원칙**: 파서가 놓친 항목(동적 라우트, 특수 프레임워크 패턴)은 직접 코드를
Read로 확인해 보완하되, 보완 항목에는 근거 파일을 명시하고 `[파서 미탐지 — 수동 확인]`
태그를 붙인다. **사실 표에 없는 화면·API·규칙을 지어내지 않는다.** `reference.md`의
범위·정확성 표기 규칙(소스 미포함 컴포넌트 → `[정보 없음]`, 민감정보 비포함, 추정 `[추정]`)을
항상 적용한다.

> **파서 커버리지 점검**: 추출 통계(라우트·컴포넌트 수)가 코드 규모에 비해 비정상적으로
> 낮으면(`reference.md` 1-I 참조 — Next.js 파일 라우팅, Vue `<script setup>` 등) 정규식이
> 해당 패턴을 못 잡은 것일 수 있다. 이 경우 사실 표를 그대로 신뢰하지 말고 Read로 직접
> 보완한 뒤, Step 5 완료 보고에 "파서 커버리지 경고"를 남긴다.

#### 분할 모드 (대형 코드베이스 — 소스 30개 초과)

**모듈별 순차 extract**로 처리한다. 사실 추출은 파서(extract.py)가 하고 LLM은 코드를
직접 읽지 않으므로, 서브에이전트(Task 도구) 없이 메인 컨텍스트에서 모듈마다 extract.py를
차례로 돌려도 컨텍스트가 오염되지 않는다(각 `_facts.md`는 코드가 아니라 압축된 사실 표다).
Task 도구가 필요 없어 `allowed-tools`만으로 무인 완주한다.

1. 대상을 디렉토리/도메인 단위 모듈로 나눈다 (예: `src/pages`, `src/admin`, `src/lib`).
2. 모듈마다 extract.py를 **모듈별 출력 경로로** 실행한다(이미 사전 승인된 명령):

   ```bash
   python ${CLAUDE_SKILL_DIR}/scripts/extract.py src/pages --output reverse-prd-output/_facts_pages.md
   python ${CLAUDE_SKILL_DIR}/scripts/extract.py src/admin --output reverse-prd-output/_facts_admin.md
   ```

3. 모듈별 `_facts_*.md`를 Read로 읽어 병합한다(추출기 출력은 결정적이라 병합 시 충돌 없음).
   흐름도가 필요하면 전체 대상에 대해 한 번 `--emit-flow`로 스켈레톤을 만든다.
   Step 2부터는 병합본으로 진행한다.
4. 문서 1장(Overview)에 **"모듈별 분석 범위" 표**를 기록한다: [모듈 | 파일 수 | 추출 통계].

> 파일 수가 아주 많아도 extract.py는 대상 디렉토리를 재귀 순회해 **하나의** 사실 표로
> 뽑으므로(코드가 아닌 압축 표), 단일 실행으로 충분한 경우가 많다. 분할은 산출 표 자체가
> 지나치게 커질 때 모듈 단위로 나눠 가독성/검토성을 높이기 위한 선택지다.

### Step 2 — 의미 분석 (3개 축 동시 수행)

Step 1 추출 결과를 PRD 관점으로 재해석한다.

#### 2-A. 사용자 & 목표 추론

- 권한/롤 분기, 화면 구성 → **타겟 사용자/페르소나** 추정
- 도메인 파악 (e-commerce, banking, admin, SaaS 등)
- 핵심 화면·퍼널 → **제품이 달성하려는 목표(Goal)** 추정
- 전환/완료 액션(결제 완료, 가입 완료 등) → **성공지표(KPI) 후보** 도출

#### 2-B. 사용자 스토리 재구성

- 화면 흐름 + 권한 → "~로서, ~하기 위해, ~할 수 있다" 형태의 **User Story**로 변환
- 진입점 → 핵심 흐름 → 완료점을 하나의 **사용자 여정(User Journey)**으로 묶음
- 각 스토리에 대응하는 화면/컴포넌트를 매핑

#### 2-C. 요구사항 도출

- 조건문/검증 → **기능 요구사항(FR)**: "시스템은 ~해야 한다"
- 성능/보안/접근성 관련 코드 흔적 → **비기능 요구사항(NFR)** [대개 추정]
- 화면별 입력·동작 → 화면 단위 요구사항 목록

### Step 3 — PRD 문서 구조 구성

아래 PRD 목차로 내용을 배치한다. 섹션별로 Step 1~2의 추출 결과를 채워 넣는다.

```
역기획 PRD 목차
─────────────────────────────────────
1. Overview (개요)
   1.1 제품/기능 한 줄 요약
   1.2 문서 목적 — 역기획 PRD (코드로부터 요구사항 역추적)
   1.3 분석 대상 — 파일/디렉토리/도메인
   1.4 As-Is 스냅샷 (비교 기준선)
       - 분석 시점 커밋 해시·분석 파일 목록 — 문서-코드 정합성 판정 기준

2. Background & Problem (배경 & 문제 정의)
   2.1 추정 배경 — 이 제품이 왜 존재하는가  [대개 추정]
   2.2 해결하려는 문제 / 사용자 페인포인트   [대개 추정]

3. Goals & Success Metrics (목표 & 성공지표)
   3.1 제품 목표 (Goals)
   3.2 성공지표 / KPI 후보
       - 10.2 이벤트/트래킹 명세가 있으면 그것을 KPI의 1차 근거로 사용
       - 트래킹이 없으면 전환 액션 기반 [추정] 표기
   3.3 비목표 (Non-goals)   [정보 없음 — 별도 확인 필요]

4. Users & Personas (사용자 & 페르소나)
   4.1 추정 타겟 사용자
   4.2 사용자 롤 / 권한 (코드의 role·auth 분기 기반)

5. User Stories & Journey (사용자 스토리 & 여정)
   5.1 사용자 여정 다이어그램 (SVG — scripts/flowgen.py로 생성, 아래 Step 4-B)
       - 노드 색으로 보호 등급 구분(공개/🔒로그인/🔒admin), 점선은 조건부/추정 전환
   5.2 User Story 목록 ("~로서 ~하기 위해 ~할 수 있다")

6. Functional Requirements (기능 요구사항)
   6.1 화면별 기능 요구사항
   6.2 입력 / 검증 요구사항
   6.3 비즈니스 규칙 요구사항

7. Non-functional Requirements (비기능 요구사항)
   - 성능 / 보안 / 접근성 / 호환성  (대개 [추정] 또는 [정보 없음])

8. Information Architecture & Flow (정보구조 & 흐름)
   8.1 화면 맵 / 라우트 계층
   8.2 화면 전환 관계

9. Data & API (데이터 & API)
   9.1 API 엔드포인트 목록
   9.2 데이터 모델 추정
   9.3 상태 관리 & 데이터 흐름
       - 전역 상태(store/context) 구조, 화면별 읽기/쓰기 매핑

10. Integrations & Analytics (외부 연동 & 측정)
    10.1 외부 연동 인벤토리
        - PG·소셜 로그인·지도·분석 도구 등 서드파티 목록과 사용 위치
    10.2 이벤트/트래킹 명세
        - 이벤트 호출 목록 [이벤트명 | 트리거 | 파라미터 | 위치]
        - "지표를 어떻게 재고 있었나" → 3.2 KPI 추정의 직접 근거

11. Scope & Milestones (범위 & 일정)
    11.1 In-scope / Out-of-scope
    11.2 마일스톤  [정보 없음 — 별도 확인 필요]

12. Risks & Open Questions (리스크 & 오픈 이슈)
    - 코드상 미구현/TODO/예외 누락 → 리스크
    - 교차 검증이 필요한 추정 항목 목록

13. Appendix (부록)
    13.1 주요 컴포넌트 목록
    13.2 에러/메시지 카탈로그
        - 사용자 노출 문구 전수 표 [ID | 문구 | 유형 | 노출 조건 | 근거 파일]
    13.3 추적성 매트릭스 (Traceability)
        - [요구사항 ID ↔ User Story ↔ 화면 ↔ 코드 파일] 매핑
    13.4 용어 정의 (도메인 용어)
    13.5 QA / 검증 체크리스트
─────────────────────────────────────
```

채우기 규칙:

- 코드에서 근거를 찾은 항목: 구체적으로 기술하고 **코드 근거**를 함께 명시
- 근거가 불충분한 항목: `[추정]` 태그 (배경·목표·페르소나·NFR은 대개 추정)
- 코드에 없는 항목: `[정보 없음 — 별도 확인 필요]` 표기
- 요구사항 문장은 검증 가능하게: "시스템은 ~해야 한다 / 사용자는 ~할 수 있다"

> PRD는 본질적으로 "의도"를 다루지만 코드에는 의도가 직접 적혀 있지 않다.
> 따라서 배경·목표·KPI·페르소나 섹션은 추정 비중이 높으며, 반드시 `[추정]`을
> 붙이고 Step 5 완료 보고에서 교차 검증 대상으로 강조한다.

### Step 4 — 출력 파일 생성

문서 렌더링은 인라인 코드가 아니라 스킬에 동봉된 **`scripts/render.py`** 로 수행한다.
(Markdown → PDF / DOCX / HTML 변환을 한 스크립트가 처리한다. `allowed-tools` 는
`Bash(python */scripts/render.py *)` 로 한정되어 있어 임의 Python 실행이 아닌
render.py 호출만 사전 승인된다 — `${CLAUDE_SKILL_DIR}` 치환은 본문에서만 동작하고
프론트매터에서는 확장되지 않으므로 경로 와일드카드 패턴을 사용한다.)

#### 4-A. 본문을 Markdown 파일로 저장

Step 3에서 구성한 PRD 전체 본문(Markdown)을 `Write` 도구로 임시 파일에 저장한다.
예: `reverse-prd-output/_prd_body.md`

#### 4-B. 유저플로우 SVG 생성

Step 1에서 생성된 `_flow.json` 스켈레톤(노드·보호등급·전환은 파서가 채움)에
라벨을 사람이 읽을 문구로 다듬고, 코드 근거 없는 전환은 `[추정]` 라벨 + `dashed: true`로
보강한 뒤, `flowgen.py`로 SVG를 생성해 본문의 5.1(사용자 여정 다이어그램)에 인라인 삽입한다.

```bash
python ${CLAUDE_SKILL_DIR}/scripts/flowgen.py --input reverse-prd-output/_flow.json --output reverse-prd-output/_flow.svg
```

- JSON 형식: `nodes[{id,label,guard: public|login|admin}]`, `edges[{from,to,label,dashed?}]`, `entry[]`
  (상세는 flowgen.py 상단 주석 참조)
- 코드 근거가 없는 전환(예: "담기")은 라벨에 `[추정]`을 붙이고 `dashed: true`로 표시한다.
- 인라인 SVG는 JS 없이 동작하므로 **HTML과 PDF 모두에서** 렌더링된다.

#### 4-C. 의존성 설치 (최초 1회)

```bash
pip install weasyprint markdown python-docx --quiet
```

> 환경에 이미 설치돼 있으면 생략한다. HTML 출력은 weasyprint 없이도 가능하다.
> macOS에서 `python`/`pip`이 없으면 `python3`/`pip3`를 사용한다.
>
> **플랫폼별 PDF 엔진(weasyprint) 요구사항** — pip만으로는 부족할 수 있다:
> - **Windows**: Pango 네이티브 라이브러리 필요. 공식 권장은 MSYS2 설치 후
>   `pacman -S mingw-w64-ucrt-x86_64-pango`. 설치가 어려우면 `--format docx,html`로 대체.
> - **macOS**: `brew install weasyprint` 한 줄로 해결.
> - PDF 생성 실패 시 사용자에게 위 안내를 전하고 `--format html`(또는 docx,html)로 계속 진행한다.

#### 4-D. 렌더링 실행

```bash
python ${CLAUDE_SKILL_DIR}/scripts/render.py --input reverse-prd-output/_prd_body.md --title "역기획 PRD" --accent "#1f4e79" --outdir reverse-prd-output --name reverse_prd
```

> 명령은 **한 줄로 실행**한다 (백슬래시 줄바꿈은 allowed-tools 패턴 매칭을 깨뜨릴 수 있다).

- **기본 출력은 PDF + HTML 세트**다 (`--format pdf,html` 기본값, 같은 타임스탬프로 쌍 생성).
  사용자가 형식을 지정하면 그에 맞춰 쉼표 조합: `--format docx,html` 등.
  단, 어떤 형식을 요청받든 **HTML은 항상 함께 생성**한다 (브라우저 즉시 확인용).
- 영문 문서 요청 시 `--lang en --title "Reverse-engineered PRD"` 를 함께 지정한다
  (`--lang`은 HTML/PDF의 `lang` 속성을 결정한다).
- 출력 파일: `reverse-prd-output/reverse_prd_YYYYMMDD_HHMMSS.pdf` + 동일 이름 `.html`

> `render.py` 는 GFM 파이프 테이블 · 헤딩 · 코드블록 · 불릿 · 인용을 PDF/DOCX 모두에서
> 처리한다. 따라서 사용자 스토리표·요구사항표는 본문 Markdown에 표로 작성하면 그대로 변환된다.

### Step 5 — 완료 보고

분석이 끝나면 아래 형식으로 요약을 출력한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
역기획 PRD 생성 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  시크릿 노출 경고   : N건 (발견 시 최상단에도 요약 배치, 값은 미노출)
📁 분석 파일 수       : N개 (커밋 <해시> 기준)
🖥  발견된 화면 수     : N개
👤 추정 페르소나/롤   : N개
📖 도출된 User Story  : N개
✅ 도출된 요구사항    : N개 (FR N / NFR N)
💬 수집된 사용자 문구 : N개 (에러/메시지 카탈로그)
🔗 외부 연동/트래킹   : N개 / N개
⚠️  추정 항목         : N개 ([추정] 표기됨)
❓ 정보 부족 항목     : N개 (별도 확인 필요)

📄 출력 파일: ./reverse-prd-output/reverse_prd_YYYYMMDD_HHMMSS.pdf (+ 동일 이름 .html)
🔍 파서 커버리지 경고: (있으면) 추출 통계가 비정상적으로 낮았던 항목과 수동 보완 내역

교차 검증이 꼭 필요한 항목:
  1. [배경/목표] — 코드에 의도가 없어 추정으로 작성됨
  2. [KPI] — 전환 액션 기반 추정, 실제 지표 확인 필요
  3. ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 사용 예시

```bash
# 기본 (현재 디렉토리, PDF 출력)
/reverse-prd

# 특정 파일로 PRD 생성
/reverse-prd src/index.html

# 디렉토리 전체 + Word 출력
/reverse-prd src/ --format docx

# 영문 PRD
/reverse-prd . --format pdf --lang en
```

## reverse-spec 과의 관계

- **같은 분석 엔진**: Step 1(코드 파싱)·Step 2 추출 로직은 reverse-spec과 공유한다.
- **다른 산출물**: reverse-spec은 "정책 규칙서", reverse-prd는 "제품 요구사항 문서".
- 한 코드베이스에 대해 두 스킬을 모두 돌리면 **PRD(왜/무엇) + 정책서(어떻게)** 를
  세트로 확보할 수 있다. PM은 reverse-prd를, 개발/QA는 reverse-spec을 참조하면 된다.

## 주의 사항

- 분석은 정적 코드 기반이므로 런타임 동적 생성 화면은 누락될 수 있다.
- PRD의 **배경·목표·KPI·페르소나**는 코드에 의도가 적혀 있지 않아 추정 비중이 높다.
  `[추정]` 항목은 반드시 PM/기획자가 교차 검증해야 한다.
- 민감 정보(API key, password)가 코드에 있으면 문서에 포함하지 않고 별도 경고로 표시한다.
- 파일이 500줄을 초과하면 섹션별로 나누어 순차 분석한다.
