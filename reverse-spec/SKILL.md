---
name: reverse-spec
description: >
  코드(HTML/JS/TS/Vue/React)를 분석해서 역기획 정책서(PDF 또는 docx)를 자동 생성한다.
  사용자가 "역기획", "정책서", "스펙 문서", "코드 분석해서 문서화" 등을 요청할 때 자동 실행.
  인자로 파일 경로 또는 디렉토리를 받는다.
argument-hint: <파일_또는_디렉토리_경로> [--format pdf|docx] [--lang ko|en]
allowed-tools: >
  Read, Glob, Write,
  Bash(find *), Bash(ls *),
  Bash(pip install weasyprint *), Bash(pip install markdown *), Bash(pip install python-docx *),
  Bash(python */scripts/render.py *)
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

대상 파일을 읽어 **네비게이션/라우트, 컴포넌트/화면, 조건·검증·권한·API, 화면 전환**을
추출한다. 상세 추출 규칙은 **`${CLAUDE_SKILL_DIR}/reference.md` (공통 코드 파싱 규칙)** 을 따른다.
결과는 내부 메모로만 정리하고 사용자에게 출력하지 않는다.

> `reverse-spec` / `reverse-prd`가 동일한 파싱 규칙(`reference.md`)을 공유한다.
> 추출된 원자료의 의미 해석은 Step 2에서 스킬 목적(정책 규칙화)에 맞게 수행한다.
> 특히 `reference.md`의 **범위·정확성 표기 규칙**(소스 미포함 컴포넌트 → `[정보 없음]`,
> 민감정보 비포함, 추정 `[추정]` 표기)을 반드시 적용한다.

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
   1.3 이해관계자
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

3. 핵심 로직 / 교차검증
   3.1 핵심 비즈니스 로직 상세
       - 도메인의 중심이 되는 계산식·산정 규칙 (예: 요금 계산, 할인 판정)
   3.2 전환영향 집계
       - 이 로직 변경 시 영향을 받는 화면/정책 목록
   3.3 소스 밖 교차검증
       - 코드만으로 확정할 수 없어 외부 확인이 필요한 항목

4. Appendix
   4.1 개발 참조
       - 주요 컴포넌트 목록
       - API 엔드포인트 목록
   4.2 체크리스트
       - QA 확인 항목
   4.3 용어 정의
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

문서 렌더링은 인라인 코드가 아니라 스킬에 동봉된 **`scripts/render.py`** 로 수행한다.
(Markdown → PDF / DOCX / HTML 변환을 한 스크립트가 처리한다. `allowed-tools` 는
`Bash(python */scripts/render.py *)` 로 한정되어 있어 임의 Python 실행이 아닌
render.py 호출만 사전 승인된다 — `${CLAUDE_SKILL_DIR}` 치환은 본문에서만 동작하고
프론트매터에서는 확장되지 않으므로 경로 와일드카드 패턴을 사용한다.)

#### 4-A. 본문을 Markdown 파일로 저장

Step 3에서 구성한 정책서 전체 본문(Markdown)을 `Write` 도구로 임시 파일에 저장한다.
예: `reverse-spec-output/_spec_body.md`

#### 4-B. 의존성 설치 (최초 1회)

```bash
pip install weasyprint markdown python-docx --quiet
```

> 환경에 이미 설치돼 있으면 생략한다. `--format html` 미리보기는 weasyprint 없이도 가능하다.

#### 4-C. 렌더링 실행

```bash
python ${CLAUDE_SKILL_DIR}/scripts/render.py --input reverse-spec-output/_spec_body.md --format pdf --title "역기획 정책서" --accent "#2c2c2c" --outdir reverse-spec-output --name reverse_spec
```

> 명령은 **한 줄로 실행**한다 (백슬래시 줄바꿈은 allowed-tools 패턴 매칭을 깨뜨릴 수 있다).

- `--format` : `pdf`(기본) / `docx` / `html`(미리보기)
- 영문 문서 요청 시 `--lang en --title "Reverse-engineered Spec"` 를 함께 지정한다
  (`--lang`은 HTML/PDF의 `lang` 속성을 결정한다).
- 출력 파일: `reverse-spec-output/reverse_spec_YYYYMMDD_HHMMSS.[pdf|docx|html]`

> `render.py` 는 GFM 파이프 테이블 · 헤딩 · 코드블록 · 불릿 · 인용을 PDF/DOCX 모두에서
> 처리한다. 따라서 정책 항목표는 본문 Markdown에 표(`| No | 정책 내용 | 코드 근거 | 비고 |`)로
> 작성하면 그대로 변환된다.

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
