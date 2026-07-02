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
