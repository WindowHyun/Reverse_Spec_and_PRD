# 공통 코드 파싱 규칙 (Phase 1)

`reverse-spec` / `reverse-prd` 공용 파싱 스펙. 두 스킬의 **Step 1**은 이 규칙을 따른다.

- 추출 결과는 **내부 메모로만** 정리하고 사용자에게 출력하지 않는다.
- 추출은 "있는 그대로의 원자료"만 모은다. 의미 해석(정책 규칙화 / 요구사항화)은
  각 스킬의 **Step 2**에서 목적에 맞게 수행한다.

---

## 0. 파일 탐색 우선순위

```
1순위: *.html               (nav/routing 구조 포함 가능성 높음)
2순위: router.js / router.ts / routes.js / routes.ts
3순위: App.vue / App.tsx / index.js
4순위: src/ 하위 전체 컴포넌트
5순위: package.json / README (제품 의도·도메인 단서 — 배경/목표 추론에 사용)
```

> `README`, `package.json`의 `description`, 폴더명, 커밋 메시지는 "제품 의도"를
> 추론하는 강력한 단서다. 배경/목표/도메인 섹션을 채울 때 우선 참고한다.

---

## 1-A. 네비게이션 / 라우트 구조

```
추출 대상:
- <nav> 내부 <a href>, <Link to>, <router-link to>
- React Router / Vue Router의 routes 배열
- Next.js pages/ 디렉토리 구조
- 앵커 href의 #섹션ID (단일 페이지 문서)
- 라우트의 인증/권한 가드 (RequireAuth, beforeEnter, middleware 등)

추출 형식:
  [depth] path → 화면명 [보호여부]  (예: [1] /checkout → 결제화면 [로그인필요])
```

## 1-B. 컴포넌트 & 화면 목록

```
추출 대상:
- export default / export function 으로 시작하는 컴포넌트
- class명, id명에서 화면 의미 추론
- placeholder, aria-label, title 속성 → 사용자에게 보이는 기능 단서

추출 형식:
  컴포넌트명 → 추정 역할 (예: LoginForm → 로그인 폼)
```

## 1-C. 조건 · 검증 · 권한 · API (로직 단서)

```
추출 대상:
- if / else / switch 조건문        → 분기 규칙 단서
- validation 함수                  → 입력 규칙 단서 (필수/형식/길이)
- API endpoint 호출                → 기능/데이터 흐름
- 에러 처리                        → 예외 규칙 단서
- 권한 체크 (role, permission, auth) → 접근 통제 / 사용자 롤 단서
- 상수/임계값 (가격, 한도, 기준액)   → 비즈니스 규칙 단서

추출 형식:
  코드 근거 → [단서]  (예: if (!token) → 미인증 시 로그인으로 리다이렉트)
```

## 1-D. 화면 간 전환 관계

```
추출 대상:
- navigate(), router.push(), window.location
- 모달 open/close 트리거
- 탭 전환, 단계(step) 이동, 결제/가입 등 퍼널 단계

추출 형식:
  출발화면 → [트리거조건] → 도착화면
```

## 1-E. 사용자 노출 문구 (에러/메시지 카탈로그)

```
추출 대상:
- alert(), confirm(), toast 계열 호출의 문자열 인자
- 검증 함수가 return하는 에러 메시지 문자열
- 빈 상태 문구 (items.length === 0 분기의 JSX 텍스트 등)
- placeholder, aria-label, 버튼 라벨 등 UI 문구
- i18n 키가 있으면 키와 기본 문구를 함께 수록

추출 형식:
  [ID | 문구(코드 원문 그대로) | 유형(에러/안내/빈상태/확인) | 노출 조건 | 근거 파일]

주의: 문구를 의역·수정하지 말 것 — 번역/CS 참조용이므로 원문 보존이 원칙.
```

## 1-F. 상태 관리 & 데이터 흐름

```
추출 대상:
- Context/Provider, redux slice, zustand/pinia store 정의
- 커스텀 훅(useAuth, useCart 등)이 노출하는 상태와 액션
- 각 화면(컴포넌트)이 어떤 상태를 읽는지/쓰는지

추출 형식:
  상태 단위 → 보유 필드/액션 → [읽는 화면들] / [쓰는 화면들]
```

## 1-G. 외부 연동 & 트래킹

```
추출 대상:
- package.json dependencies 중 서드파티 서비스 SDK
  (결제 PG, 소셜 로그인, 지도, 분석, 채팅/CS, 푸시 등)
- 서드파티 도메인으로의 fetch/스크립트 로드
- 트래킹 호출: gtag(), ga(), amplitude.track(), mixpanel.track(),
  dataLayer.push(), 커스텀 track()/logEvent() 등

추출 형식:
  연동: [대상 서비스 | 용도 | 사용 위치(파일) | 근거(패키지명/import)]
  트래킹: [이벤트명 | 트리거(어떤 행동) | 파라미터 | 위치(파일)]
```

## 1-H. As-Is 스냅샷 (비교 기준선)

```
수집 대상:
- git 저장소면: git rev-parse HEAD (커밋 해시), git log -1 --format=%ci (시점)
- 분석에 실제 포함된 파일 목록 (경로 정렬)
- git이 아니면 파일 목록 + 수정 시각만 기록

기록 위치: 문서 1장(Overview)의 As-Is 스냅샷 절.
목적: 이후 코드가 변경됐을 때 "이 문서가 유효한 기준 시점"을 판정.
```

---

## 2. 범위·정확성 표기 규칙 (필수)

정적 분석의 한계를 문서가 정직하게 드러내도록, 아래 규칙을 항상 적용한다.

- **소스 미포함 컴포넌트**: 라우터 등에서 `import`만 되고 실제 소스 파일이
  분석 대상에 없으면, 그 화면의 내부 동작은 `[정보 없음 — 별도 확인 필요]`로 표기한다.
  (라우트 존재만으로 화면 내부 기능을 단정하지 말 것.)
- **추정 항목**: 코드에 근거가 없는 의도/목표/배경/페르소나는 `[추정]` 태그를 붙인다.
- **민감 정보**: API key, password, 토큰 등이 코드에 노출돼 있으면 **문서에 포함하지 않고**
  별도 보안 경고로만 표시한다.
- **대용량 파일**: 500줄을 초과하는 파일은 섹션별로 나누어 순차 분석한다.
- **동적 생성 화면**: 런타임에 동적으로 만들어지는 화면은 누락될 수 있음을 명시한다.
