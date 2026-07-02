# 역기획 PRD — mock-shop (하이브리드 방식)

> **이 문서의 신뢰 등급 체계**
> 🔒 **파서 추출** — `extract.py`가 코드에서 결정적으로 추출. 재실행해도 항상 동일 (SHA-256 검증됨).
> ✍️ **LLM 서술** — 추출된 사실만을 근거로 LLM이 해석·작성. 재실행 시 표현이 달라질 수 있으며 `[추정]` 규칙 적용.

## 1. Overview ✍️

| 항목 | 내용 |
|------|------|
| 제품 한 줄 요약 | 로그인 기반 온라인 상점 — 탐색·장바구니·결제·주문내역 스토어프론트 |
| 분석 방식 | 하이브리드: 사실은 파서(extract.py), 해석·서술은 LLM |
| 분석 대상 | `examples/mock-shop/src` (6개 소스 파일) |

## 2. 사실 계층 (Fact Layer) 🔒

아래 5개 표는 **extract.py 출력 그대로**이며 LLM이 한 글자도 만지지 않았다.
같은 코드로 재실행하면 항상 동일하다.

## 라우트 맵 (파서 추출)

| Path | 컴포넌트 | 보호 | 근거 파일 |
|---|---|---|---|
| / | Home | 공개 | `router.tsx` |
| /admin | AdminDashboard | role=admin | `router.tsx` |
| /cart | Cart | 공개 | `router.tsx` |
| /checkout | Checkout | 로그인 필요 | `router.tsx` |
| /login | Login | 공개 | `router.tsx` |
| /orders | Orders | 로그인 필요 | `router.tsx` |
| /products | ProductList | 공개 | `router.tsx` |
| /products/:id | ProductDetail | 공개 | `router.tsx` |

## 컴포넌트 분석 범위 (파서 추출)

| 컴포넌트 | 소스 파일 | 분석 가능 |
|---|---|---|
| AdminDashboard | — | ❌ import만 — [정보 없음] |
| Cart | `pages/Cart.tsx` | ✅ 소스 포함 |
| Checkout | `pages/Checkout.tsx` | ✅ 소스 포함 |
| Home | — | ❌ import만 — [정보 없음] |
| Login | `pages/Login.tsx` | ✅ 소스 포함 |
| Orders | — | ❌ import만 — [정보 없음] |
| ProductDetail | — | ❌ import만 — [정보 없음] |
| ProductList | — | ❌ import만 — [정보 없음] |
| RequireAuth | `lib/RequireAuth.tsx` | ✅ 소스 포함 |

## API 호출 (파서 추출)

| 엔드포인트 | 메서드 | 근거 |
|---|---|---|
| `/api/auth/login` | POST | `pages/Login.tsx (주석)` |
| `/api/orders` | POST | `pages/Checkout.tsx (주석)` |

## 비즈니스 상수 (파서 추출)

| 상수 | 값 | 근거 파일 |
|---|---|---|
| `FREE_SHIPPING_THRESHOLD` | 50000 | `pages/Checkout.tsx` |
| `SHIPPING_FEE` | 3000 | `pages/Checkout.tsx` |

## 검증/차단 규칙 (파서 추출)

| 유형 | 조건 | 효과 | 근거 파일 |
|---|---|---|---|
| 동작 차단 | `items.length === 0` | 버튼 비활성화 | `pages/Cart.tsx` |
| 범위 제한 | `min 1 / max it.stock` | 입력값 범위 강제 | `pages/Cart.tsx` |
| 입력 검증 | `!email` | 메시지 "이메일을 입력해주세요." | `pages/Login.tsx` |
| 입력 검증 | `password.length < 8` | 메시지 "비밀번호는 8자 이상이어야 합니다." | `pages/Login.tsx` |
| 필수값 | `address 미입력` | 알림 "배송지를 입력해주세요." 후 중단 | `pages/Checkout.tsx` |

<!-- 추출 통계: 라우트 8 · 컴포넌트 9 · API 2 · 상수 2 · 규칙 5 -->

## 3. 해석 계층 (Interpretation Layer) ✍️

**이하 서술은 위 사실 계층의 표만을 근거로 작성되었다. 표에 없는 화면·API·규칙은 언급하지 않는다.**

### 3.1 사용자 & 페르소나 `[추정]`

라우트 맵의 보호 컬럼이 세 등급(공개 / 로그인 필요 / role=admin)으로 나뉘므로,
**비로그인 방문자 · 일반 구매자 · 관리자**의 3개 페르소나를 추정한다.

### 3.2 핵심 사용자 여정 `[추정]`

공개 라우트(`/products` → `/products/:id` → `/cart`)에서 보호 라우트(`/checkout` → `/orders`)로
이어지는 구조는 전형적인 **구매 퍼널**이다. `/checkout`의 "로그인 필요" 가드는
결제 직전에 인증을 강제하는 설계로 해석된다.

### 3.3 핵심 비즈니스 규칙 해석

- 🔒 `FREE_SHIPPING_THRESHOLD = 50000` + `SHIPPING_FEE = 3000` → ✍️ **"5만원 이상 무료배송, 미만 3,000원"** 정책 `[클라이언트 측 — 서버 미확인]`
- 🔒 `disabled={items.length === 0}` → ✍️ **빈 장바구니 결제 차단** 요구사항
- 🔒 검증 규칙 표의 이메일 형식·비밀번호 8자 조건 → ✍️ 입력값 정책 (서버 측 동일 검증 여부 확인 필요)

### 3.4 리스크 & 확인 필요 `[추정]`

1. 컴포넌트 분석 범위 표에서 **5개 화면이 ❌ import만** 상태 — 해당 화면 내부 동작은 이 문서가 보증하지 않는다.
2. 권한 가드는 클라이언트 코드에만 존재 — 서버 측 인가 확인 필요.
3. `/signup` 라우트 부재 — 계정 생성 흐름 미확인.

## 4. 재현성 정보 🔒

- 사실 계층 생성: `python extract.py ../mock-shop/src`
- 검증: 2회 실행 SHA-256 동일 (`d717700f…4742`)
- 서술 계층: 재실행 시 문구가 달라질 수 있으나, 사실 계층 밖의 내용을 도입할 수 없음
