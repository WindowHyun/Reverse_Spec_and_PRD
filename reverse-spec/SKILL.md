---
name: reverse-spec
description: >
  코드(HTML/JS/TS/Vue/React)를 분석해서 역기획 정책서(PDF 또는 docx)를 자동 생성한다.
  사용자가 "역기획", "정책서", "스펙 문서", "코드 분석해서 문서화" 등을 요청할 때 자동 실행.
  인자로 파일 경로 또는 디렉토리를 받는다.
argument-hint: <파일_또는_디렉토리_경로> [--format pdf|docx] [--lang ko|en]
allowed-tools: >
  Read, Glob, Bash(find *), Bash(ls *), Bash(cat *), Bash(pip install *), Bash(python *)
---

# reverse-spec — 코드 역기획 정책서 생성기

## 개요

입력된 코드를 4단계로 분석해 역기획 정책서를 생성한다.

- **Phase 1**: 코드 구조 파싱 (nav, route, component, function, class)
- **Phase 2**: 의미 분석 (화면흐름 / 기능목적 / 정책규칙)
- **Phase 3**: 문서 구조 자동 구성
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
```

### Step 1 — 코드 파싱 & 구조 추출

대상 파일을 읽어 아래 항목을 추출한다. 결과는 내부 메모로 정리하되 사용자에게 출력하지 않는다.

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
- placeholder, aria-label, title 속성

추출 형식:
  컴포넌트명 → 추정 역할 (예: LoginForm → 로그인 폼)
```

#### 1-C. 비즈니스 로직 & 정책 규칙

```
추출 대상:
- if / else / switch 조건문 → 정책 규칙
- validation 함수 → 입력값 정책
- API endpoint 호출 → 데이터 흐름
- 에러 처리 → 예외 정책
- 권한 체크 (role, permission, auth) → 접근 정책

추출 형식:
  조건 → [정책 설명] (예: if (!token) → 미인증 시 로그인 페이지로 리다이렉트)
```

#### 1-D. 화면 간 전환 관계

```
추출 대상:
- navigate(), router.push(), window.location
- 모달 open/close 트리거
- 탭 전환, 단계(step) 이동

추출 형식:
  출발화면 → [트리거조건] → 도착화면
```

### Step 2 — 의미 분석 (3개 축 동시 수행)

Step 1 추출 결과를 기반으로 다음 3가지를 병렬 추론한다.

#### 2-A. 화면 흐름 추론

- 라우트 계층 → 사용자 여정(User Journey) 재구성
- 진입점(Entry Point) → 핵심 흐름 → 이탈점 파악
- 흐름도용 노드/엣지 데이터 준비

#### 2-B. 기능 목적 추론

- 함수명/컴포넌트명의 의미를 한국어로 해석
- 비즈니스 도메인 파악 (e-commerce, banking, admin 등)
- 각 화면의 주요 목적 1~2줄로 요약

#### 2-C. 정책 항목 도출

- 조건문 → "~한 경우 ~한다" 형태의 정책 문장으로 변환
- 검증 규칙 → 입력값 정책 (필수값, 형식, 길이 제한 등)
- 권한 분기 → 접근 통제 정책

### Step 3 — 문서 구조 구성

아래 목차 구조로 내용을 배치한다. 섹션별로 Step 1~2의 추출 결과를 채워 넣는다.

```
역기획 정책서 목차
─────────────────────────────────────
1. Document Overview
   1.1 배경
       - 분석 대상 파일/시스템 개요
       - 역기획 목적
   1.2 목표 / 성공지표
       - 이 문서를 통해 달성하려는 것
   1.4 이해관계자
       - 추정 관련 직군 (개발, 기획, QA, 운영)

2. Scope & Product Policy
   2.1 흐름 (흐름도)
       - 전체 화면 흐름 다이어그램 (텍스트 기반 ASCII 또는 Mermaid)
   2.2 작업 내용
       - 각 화면별 주요 기능 목록
   2.3 공통 정책
       - 인증/권한 정책
       - 에러 처리 공통 규칙
       - 공통 입력값 정책
   2.4 화면 정책
       - 화면별 세부 정책 항목
   2.5 안내 메시지
       - 사용자에게 노출되는 메시지 목록
   2.6 보조 화면
       - 모달, 팝업, 툴팁 등

3. ★ 전환영향 / 교차검증
   합의금 계산 로직 (또는 핵심 비즈니스 로직)
   전환영향 ★ 집계
   소스 밖 교차검증

4. Appendix
   3.1 개발 참조
       - 주요 컴포넌트 목록
       - API 엔드포인트 목록
   3.2 체크리스트
       - QA 확인 항목
   3.3 용어 정의
       - 코드에서 발견된 도메인 용어

5. 보안 점검
   - 인증 처리 방식
   - 민감 데이터 노출 여부
   - 권한 분기 누락 위험 항목
─────────────────────────────────────
```

채우기 규칙:

- 코드에서 근거를 찾은 항목: 구체적으로 기술
- 근거가 불충분한 항목: `[추정]` 태그 붙여 작성
- 코드에 없는 항목: `[정보 없음 — 별도 확인 필요]` 표기

### Step 4 — 출력 파일 생성

#### 4-A. 출력 경로 결정

```
기본 출력 경로: ./reverse-spec-output/
파일명: reverse_spec_YYYYMMDD_HHMMSS.[pdf|docx]
```

#### 4-B. PDF 출력 (`--format pdf` 또는 기본값)

```bash
pip install weasyprint markdown --quiet
```

아래 Python 스크립트를 실행한다:

```python
import datetime, markdown, pathlib
from weasyprint import HTML, CSS

content = """{{ Step3에서 구성한 전체 문서 내용 (Markdown) }}"""

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
  h1 {{ font-size: 20pt; border-bottom: 2px solid #333; padding-bottom: 8px; margin-top: 40px; }}
  h2 {{ font-size: 15pt; border-left: 4px solid #555; padding-left: 10px; margin-top: 30px; }}
  h3 {{ font-size: 12pt; color: #444; margin-top: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 10pt; }}
  th {{ background: #2c2c2c; color: white; padding: 8px 12px; text-align: left; }}
  td {{ border: 1px solid #ccc; padding: 7px 12px; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #f8f8f8; }}
  code {{ background: #f0f0f0; padding: 2px 5px; border-radius: 3px; font-size: 9.5pt; }}
  pre {{ background: #1e1e1e; color: #d4d4d4; padding: 14px; border-radius: 6px;
         font-size: 9pt; overflow-x: auto; }}
  .tag-assumed {{ color: #c47a00; font-size: 9pt; font-weight: bold; }}
  .tag-missing  {{ color: #999; font-size: 9pt; }}
  @page {{
    size: A4;
    margin: 20mm 18mm 20mm 20mm;
    @top-center {{
      content: "역기획 정책서";
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

out_dir = pathlib.Path("reverse-spec-output")
out_dir.mkdir(exist_ok=True)
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_path = out_dir / f"reverse_spec_{ts}.pdf"

HTML(string=html_template).write_pdf(str(out_path))
print(f"✅ PDF 생성 완료: {out_path}")
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
    h.runs[0].font.color.rgb = RGBColor(0x1a, 0x1a, 0x1a)
    return h

def add_policy_table(doc, rows):
    """정책 항목 테이블: [번호, 정책 내용, 근거, 비고]"""
    table = doc.add_table(rows=1 + len(rows), cols=4)
    table.style = 'Table Grid'
    headers = ['No', '정책 내용', '코드 근거', '비고']
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        cell.paragraphs[0].runs[0].bold = True
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            table.rows[i+1].cells[j].text = str(val)
    return table

# ── 본문 채우기 (Step 3 내용을 섹션별로 삽입) ──
# 여기에 Step 3의 각 섹션 내용을 doc.add_heading / doc.add_paragraph로 삽입

out_dir = pathlib.Path("reverse-spec-output")
out_dir.mkdir(exist_ok=True)
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_path = out_dir / f"reverse_spec_{ts}.docx"
doc.save(str(out_path))
print(f"✅ DOCX 생성 완료: {out_path}")
```

### Step 5 — 완료 보고

분석이 끝나면 아래 형식으로 요약을 출력한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
역기획 정책서 생성 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 분석 파일 수     : N개
🖥  발견된 화면 수   : N개
📋 도출된 정책 항목 : N개
⚠️  추정 항목       : N개 ([추정] 표기됨)
❓ 정보 부족 항목   : N개 (별도 확인 필요)

📄 출력 파일: ./reverse-spec-output/reverse_spec_YYYYMMDD_HHMMSS.pdf

확인이 필요한 항목:
  1. [섹션명] — [이유]
  2. ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 사용 예시

```bash
# 기본 (현재 디렉토리, PDF 출력)
/reverse-spec

# 특정 파일 분석
/reverse-spec src/index.html

# 디렉토리 전체 + Word 출력
/reverse-spec src/ --format docx

# 영문 PDF
/reverse-spec . --format pdf --lang en
```

## 주의 사항

- 분석은 정적 코드 기반이므로 런타임 동적 생성 화면은 누락될 수 있다
- `[추정]` 항목은 반드시 기획자/개발자가 교차 검증해야 한다
- 민감 정보(API key, password)가 코드에 있으면 문서에 포함하지 않고 별도 경고로 표시한다
- 파일이 500줄을 초과하면 섹션별로 나누어 순차 분석한다
