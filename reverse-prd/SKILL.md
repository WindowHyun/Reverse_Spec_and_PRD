---
name: reverse-prd
description: >
  코드(HTML/JS/TS/Vue/React)를 분석해서 역기획 PRD(제품 요구사항 문서, PDF 또는 docx)를
  자동 생성한다. 사용자가 "역기획 PRD", "PRD 만들어줘", "코드로 요구사항 문서",
  "기획 문서 역으로 뽑아줘" 등을 요청할 때 자동 실행. 인자로 파일 경로 또는 디렉토리를 받는다.
  정책 규칙 위주의 정책서가 필요하면 reverse-spec 스킬을 사용한다.
argument-hint: <파일_또는_디렉토리_경로> [--format pdf|docx] [--lang ko|en]
allowed-tools: >
  Read, Glob, Bash(find *), Bash(ls *), Bash(cat *), Bash(pip install *), Bash(python *)
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
2. `--format` 플래그로 출력 형식 결정 (기본값: `pdf`)
3. `--lang` 플래그로 문서 언어 결정 (기본값: `ko`)
4. 경로가 없으면 현재 디렉토리(`.`)를 대상으로 한다.

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

### Step 1 — 코드 파싱 & 구조 추출

대상 파일을 읽어 아래 항목을 추출한다. 결과는 내부 메모로 정리하되 사용자에게 출력하지 않는다.
(reverse-spec과 동일한 추출 로직)

#### 1-A. 네비게이션 / 라우트 구조

```
추출 대상:
- <nav> 내부 <a href>, <Link to>, <router-link to>
- React Router / Vue Router의 routes 배열
- Next.js pages/ 디렉토리 구조
- 앵커 href의 #섹션ID (단일 페이지 문서)

추출 형식:
  [depth] path → 화면명 (예: [1] /login → 로그인화면)
```

#### 1-B. 컴포넌트 & 화면 목록

```
추출 대상:
- export default / export function 으로 시작하는 컴포넌트
- class명, id명에서 화면 의미 추론
- placeholder, aria-label, title 속성 → 사용자에게 보이는 기능 단서

추출 형식:
  컴포넌트명 → 추정 역할 (예: LoginForm → 로그인 폼)
```

#### 1-C. 기능 단서 & 비즈니스 로직

```
추출 대상:
- if / else / switch 조건문 → 요구사항/규칙 단서
- validation 함수 → 입력 요구사항
- API endpoint 호출 → 기능/데이터 흐름
- 에러 처리 → 예외 요구사항
- 권한 체크 (role, permission, auth) → 사용자 롤/권한 요구사항

추출 형식:
  코드 근거 → [요구사항 단서] (예: if (cart.length===0) disable → 빈 장바구니 결제 차단 요구)
```

#### 1-D. 화면 간 전환 관계 (사용자 여정 단서)

```
추출 대상:
- navigate(), router.push(), window.location
- 모달 open/close 트리거
- 탭 전환, 단계(step) 이동, 결제/가입 등 퍼널 단계

추출 형식:
  출발화면 → [트리거조건] → 도착화면
```

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

2. Background & Problem (배경 & 문제 정의)
   2.1 추정 배경 — 이 제품이 왜 존재하는가  [대개 추정]
   2.2 해결하려는 문제 / 사용자 페인포인트   [대개 추정]

3. Goals & Success Metrics (목표 & 성공지표)
   3.1 제품 목표 (Goals)
   3.2 성공지표 / KPI 후보  (전환 액션 기반, [추정] 표기)
   3.3 비목표 (Non-goals)   [정보 없음 — 별도 확인 필요]

4. Users & Personas (사용자 & 페르소나)
   4.1 추정 타겟 사용자
   4.2 사용자 롤 / 권한 (코드의 role·auth 분기 기반)

5. User Stories & Journey (사용자 스토리 & 여정)
   5.1 사용자 여정 다이어그램 (ASCII 또는 Mermaid)
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

10. Scope & Milestones (범위 & 일정)
    10.1 In-scope / Out-of-scope
    10.2 마일스톤  [정보 없음 — 별도 확인 필요]

11. Risks & Open Questions (리스크 & 오픈 이슈)
    - 코드상 미구현/TODO/예외 누락 → 리스크
    - 교차 검증이 필요한 추정 항목 목록

12. Appendix (부록)
    12.1 주요 컴포넌트 목록
    12.2 용어 정의 (도메인 용어)
    12.3 QA / 검증 체크리스트
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

#### 4-A. 출력 경로 결정

```
기본 출력 경로: ./reverse-prd-output/
파일명: reverse_prd_YYYYMMDD_HHMMSS.[pdf|docx]
```

#### 4-B. PDF 출력 (`--format pdf` 또는 기본값)

```bash
pip install weasyprint markdown --quiet
```

아래 Python 스크립트를 실행한다:

```python
import datetime, markdown, pathlib
from weasyprint import HTML, CSS

content = """{{ Step3에서 구성한 전체 PRD 내용 (Markdown) }}"""

md_html = markdown.markdown(content, extensions=['tables', 'toc', 'fenced_code'])

html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
  body {{ font-family: 'Noto Sans KR', sans-serif; font-size: 11pt; line-height: 1.8;
          color: #1a1a1a; margin: 0; padding: 0; }}
  h1 {{ font-size: 20pt; border-bottom: 2px solid #1f4e79; padding-bottom: 8px; margin-top: 40px; color: #1f4e79; }}
  h2 {{ font-size: 15pt; border-left: 4px solid #2e75b6; padding-left: 10px; margin-top: 30px; }}
  h3 {{ font-size: 12pt; color: #444; margin-top: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 10pt; }}
  th {{ background: #1f4e79; color: white; padding: 8px 12px; text-align: left; }}
  td {{ border: 1px solid #ccc; padding: 7px 12px; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #f4f8fc; }}
  code {{ background: #eef2f7; padding: 2px 5px; border-radius: 3px; font-size: 9.5pt; }}
  pre {{ background: #1e1e1e; color: #d4d4d4; padding: 14px; border-radius: 6px;
         font-size: 9pt; overflow-x: auto; }}
  .tag-assumed {{ color: #c47a00; font-size: 9pt; font-weight: bold; }}
  .tag-missing  {{ color: #999; font-size: 9pt; }}
  @page {{
    size: A4;
    margin: 20mm 18mm 20mm 20mm;
    @top-center {{
      content: "역기획 PRD";
      font-size: 9pt; color: #888;
    }}
    @bottom-right {{
      content: counter(page) " / " counter(pages);
      font-size: 9pt; color: #888;
    }}
  }}
</style>
</head>
<body>
{md_html}
</body>
</html>
"""

out_dir = pathlib.Path("reverse-prd-output")
out_dir.mkdir(exist_ok=True)
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_path = out_dir / f"reverse_prd_{ts}.pdf"

HTML(string=html_template).write_pdf(str(out_path))
print(f"✅ PRD(PDF) 생성 완료: {out_path}")
```

#### 4-C. Word 출력 (`--format docx`)

```bash
pip install python-docx --quiet
```

```python
import datetime, pathlib
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

# 페이지 여백
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
section = doc.sections[0]
section.top_margin    = Cm(2.0)
section.bottom_margin = Cm(2.0)
section.left_margin   = Cm(2.5)
section.right_margin  = Cm(2.0)

# 스타일 설정 함수
def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    h.runs[0].font.color.rgb = RGBColor(0x1f, 0x4e, 0x79)
    return h

def add_story_table(doc, rows):
    """사용자 스토리 테이블: [ID, 사용자 스토리, 대응 화면, 우선순위, 근거]"""
    table = doc.add_table(rows=1 + len(rows), cols=5)
    table.style = 'Table Grid'
    headers = ['ID', 'User Story', '대응 화면/컴포넌트', '우선순위', '코드 근거']
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        cell.paragraphs[0].runs[0].bold = True
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            table.rows[i+1].cells[j].text = str(val)
    return table

def add_req_table(doc, rows):
    """요구사항 테이블: [ID, 요구사항, 유형(FR/NFR), 근거, 비고]"""
    table = doc.add_table(rows=1 + len(rows), cols=5)
    table.style = 'Table Grid'
    headers = ['ID', '요구사항', '유형', '코드 근거', '비고']
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        cell.paragraphs[0].runs[0].bold = True
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            table.rows[i+1].cells[j].text = str(val)
    return table

# ── 본문 채우기 (Step 3 PRD 목차를 섹션별로 삽입) ──
# 여기에 Step 3의 각 섹션 내용을 doc.add_heading / doc.add_paragraph / 위 테이블 함수로 삽입

out_dir = pathlib.Path("reverse-prd-output")
out_dir.mkdir(exist_ok=True)
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_path = out_dir / f"reverse_prd_{ts}.docx"
doc.save(str(out_path))
print(f"✅ PRD(DOCX) 생성 완료: {out_path}")
```

### Step 5 — 완료 보고

분석이 끝나면 아래 형식으로 요약을 출력한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
역기획 PRD 생성 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 분석 파일 수       : N개
🖥  발견된 화면 수     : N개
👤 추정 페르소나/롤   : N개
📖 도출된 User Story  : N개
✅ 도출된 요구사항    : N개 (FR N / NFR N)
⚠️  추정 항목         : N개 ([추정] 표기됨)
❓ 정보 부족 항목     : N개 (별도 확인 필요)

📄 출력 파일: ./reverse-prd-output/reverse_prd_YYYYMMDD_HHMMSS.pdf

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
