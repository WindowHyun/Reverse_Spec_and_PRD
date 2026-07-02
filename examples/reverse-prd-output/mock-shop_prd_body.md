# 역기획 PRD — mock-shop

> 본 문서는 `examples/mock-shop/` 코드를 **정적 분석**해 역으로 재구성한 제품 요구사항 문서다.
> `[추정]` 항목은 코드에 의도가 명시되지 않아 추론한 것으로 교차 검증이 필요하며,
> `[정보 없음 — 별도 확인 필요]` 항목은 코드에 단서가 없다.

## 1. Overview (개요)

| 항목 | 내용 |
|------|------|
| 제품 한 줄 요약 | 로그인 기반 온라인 상점 — 상품 탐색부터 장바구니·결제·주문내역까지 제공하는 스토어프론트 |
| 문서 목적 | 완성된 프론트엔드 코드로부터 제품 요구사항을 역추적 (역기획 PRD) |
| 분석 대상 | `examples/mock-shop/src` (React 18 + React Router 6, 소스 6개 파일) |
| 분석 범위 한계 | 라우터가 참조하는 화면 8개 중 소스 포함은 Login·Cart·Checkout 3개. Home·ProductList·ProductDetail·Orders·AdminDashboard는 import만 확인 → 내부 동작 `[정보 없음]` |

### 1.4 As-Is 스냅샷 (비교 기준선)

| 항목 | 값 |
|------|-----|
| 기준 커밋 | `a1d3bc4` |
| 분석 시점 | 2026-07-02 12:52 UTC |
| 분석 파일 | `package.json`, `src/router.tsx`, `src/lib/RequireAuth.tsx`, `src/pages/Login.tsx`, `src/pages/Cart.tsx`, `src/pages/Checkout.tsx` |

> 이 커밋 이후 코드가 변경되면 본 문서의 사실 기술은 재검증이 필요하다.

## 2. Background & Problem (배경 & 문제 정의)

- **추정 배경** `[추정]` — 상품 탐색→결제 완료의 최소 단위 온라인 판매 채널. (`package.json.description` "Minimal storefront with auth, cart and checkout" 근거)
- **해결하려는 문제** `[추정]` — 비로그인 탐색은 허용하되 결제·주문은 인증 강제 → 미인증 주문으로 인한 데이터 무결성 문제 방지 (`RequireAuth` 가드 근거)

## 3. Goals & Success Metrics (목표 & 성공지표)

| 구분 | 내용 | 근거 |
|------|------|------|
| 제품 목표 | 방문→탐색→장바구니→결제 완료의 구매 퍼널 제공 | 라우트 `/products → /cart → /checkout → /orders` |
| KPI 후보 `[추정]` | 결제 완료 수(전환율), 로그인 전환율, 장바구니→결제 진입률 | `POST /api/orders`, `login()`, 진입 가드 |
| 비목표 (Non-goals) | **[정보 없음 — 별도 확인 필요]** | — |

> **KPI 근거 등급 주의**: 10.2 이벤트/트래킹 명세 결과 **트래킹 코드가 없어** 위 KPI는
> 전환 액션 기반 `[추정]`이다. 실측 지표 체계는 별도 확인이 필요하다.

## 4. Users & Personas (사용자 & 페르소나)

| 페르소나 | 설명 | 근거 |
|----------|------|------|
| 비로그인 방문자 `[추정]` | 홈/상품목록/상세/장바구니 탐색 | 해당 라우트 `RequireAuth` 미적용 |
| 일반 구매자 (user) | 로그인 후 결제·주문내역 | `/checkout`, `/orders` 보호 |
| 관리자 (admin) | 관리자 대시보드 접근 | `RequireAuth role="admin"` |

## 5. User Stories & Journey (사용자 스토리 & 여정)

**5.1 사용자 여정 다이어그램** (flowgen.py 생성 — 점선은 조건부/추정 전환, 🔒는 보호 라우트)

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1896 188" width="100%" style="max-width:1896px;font-family:'Noto Sans KR',sans-serif;">
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#5a6672"/></marker></defs>
<path d="M 192 50.0 C 228.0 50.0, 228.0 50.0, 264 50.0" fill="none" stroke="#5a6672" stroke-width="1.6" marker-end="url(#arrow)"/>
<text x="228.0" y="42.0" font-size="11" fill="#41505c" text-anchor="middle">탐색</text>
<path d="M 432 50.0 C 468.0 50.0, 468.0 50.0, 504 50.0" fill="none" stroke="#5a6672" stroke-width="1.6" marker-end="url(#arrow)"/>
<text x="468.0" y="42.0" font-size="11" fill="#41505c" text-anchor="middle">상품 선택</text>
<path d="M 672 50.0 C 708.0 50.0, 708.0 50.0, 744 50.0" fill="none" stroke="#5a6672" stroke-width="1.6" marker-end="url(#arrow)" stroke-dasharray="5 4"/>
<text x="708.0" y="42.0" font-size="11" fill="#41505c" text-anchor="middle">담기 [추정]</text>
<path d="M 912 50.0 C 1188.0 50.0, 1188.0 50.0, 1464 50.0" fill="none" stroke="#5a6672" stroke-width="1.6" marker-end="url(#arrow)"/>
<text x="1188.0" y="42.0" font-size="11" fill="#41505c" text-anchor="middle">결제하기 (빈 장바구니 차단)</text>
<path d="M 1632 50.0 C 1668.0 50.0, 1668.0 138.0, 1704 138.0" fill="none" stroke="#5a6672" stroke-width="1.6" marker-end="url(#arrow)"/>
<text x="1668.0" y="90.0" font-size="11" fill="#41505c" text-anchor="middle">주문 완료</text>
<path d="M 1632 50.0 C 1668.0 50.0, 1668.0 50.0, 1704 50.0" fill="none" stroke="#5a6672" stroke-width="1.6" marker-end="url(#arrow)" stroke-dasharray="5 4"/>
<text x="1668.0" y="42.0" font-size="11" fill="#41505c" text-anchor="middle">미인증 시</text>
<path d="M 1788.0 76 C 1788.0 94, 1548.0 94, 1548.0 76" fill="none" stroke="#5a6672" stroke-width="1.6" marker-end="url(#arrow)" stroke-dasharray="5 4"/>
<text x="1668.0" y="98" font-size="11" fill="#41505c" text-anchor="middle">로그인 후 복귀</text>
<path d="M 192 50.0 C 228.0 50.0, 228.0 138.0, 264 138.0" fill="none" stroke="#5a6672" stroke-width="1.6" marker-end="url(#arrow)" stroke-dasharray="5 4"/>
<text x="228.0" y="90.0" font-size="11" fill="#41505c" text-anchor="middle">admin 전용</text>
<rect x="24" y="24" width="168" height="52" rx="8" fill="#f4f6f8" stroke="#8a97a3" stroke-width="1.6"/>
<text x="108.0" y="54.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">홈 /</text>
<rect x="1704" y="24" width="168" height="52" rx="8" fill="#f4f6f8" stroke="#8a97a3" stroke-width="1.6"/>
<text x="1788.0" y="54.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">로그인 /login</text>
<rect x="264" y="24" width="168" height="52" rx="8" fill="#f4f6f8" stroke="#8a97a3" stroke-width="1.6"/>
<text x="348.0" y="54.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">상품목록 /products</text>
<rect x="504" y="24" width="168" height="52" rx="8" fill="#f4f6f8" stroke="#8a97a3" stroke-width="1.6"/>
<text x="588.0" y="54.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">상품상세 /:id</text>
<rect x="744" y="24" width="168" height="52" rx="8" fill="#f4f6f8" stroke="#8a97a3" stroke-width="1.6"/>
<text x="828.0" y="54.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">장바구니 /cart</text>
<rect x="1464" y="24" width="168" height="52" rx="8" fill="#e8f0fa" stroke="#2e75b6" stroke-width="1.6"/>
<text x="1548.0" y="47.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">결제 /checkout</text>
<text x="1548.0" y="64.0" font-size="10" fill="#2e75b6" text-anchor="middle">🔒</text>
<rect x="1704" y="112" width="168" height="52" rx="8" fill="#e8f0fa" stroke="#2e75b6" stroke-width="1.6"/>
<text x="1788.0" y="135.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">주문내역 /orders</text>
<text x="1788.0" y="152.0" font-size="10" fill="#2e75b6" text-anchor="middle">🔒</text>
<rect x="264" y="112" width="168" height="52" rx="8" fill="#fdf1e2" stroke="#c47a00" stroke-width="1.6"/>
<text x="348.0" y="135.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">관리자 /admin</text>
<text x="348.0" y="152.0" font-size="10" fill="#c47a00" text-anchor="middle">🔒 admin</text>
</svg>

> 다이어그램 원본 데이터: `mock-shop_flow.json` (같은 JSON → 항상 같은 SVG)


| ID | User Story | 대응 화면 | 근거 |
|----|-----------|-----------|------|
| US-1 | 방문자로서, 로그인 없이 상품을 둘러보고 싶다 | ProductList, ProductDetail `[정보 없음]` | 가드 없는 라우트 (소스 미포함) |
| US-2 | 구매자로서, 장바구니 수량을 조절하고 합계를 확인하고 싶다 | Cart | `updateQty`, `total` |
| US-3 | 구매자로서, 결제 전 로그인하고 원래 페이지로 돌아오고 싶다 | RequireAuth, Login | `state={{from}}` 복귀 |
| US-4 | 구매자로서, 배송지·결제수단을 입력해 주문을 완료하고 싶다 | Checkout | `placeOrder` → `POST /api/orders` |
| US-5 | 관리자로서, 전용 대시보드에 접근하고 싶다 | AdminDashboard `[정보 없음]` | `role="admin"` 가드 |

## 6. Functional Requirements (기능 요구사항)

| ID | 요구사항 | 코드 근거 |
|----|----------|-----------|
| FR-1 | 이메일 형식·비밀번호 8자 이상을 검증해야 한다 | `Login.validate()` |
| FR-2 | 인증 실패 시 오류 메시지(MSG-08)를 노출한다 | `catch` 분기 |
| FR-3 | 미인증 접근 시 로그인으로 보내고, 로그인 후 원래 경로로 복귀한다 | `RequireAuth` + `from` |
| FR-4 | admin 권한이 없으면 `/admin` 접근을 홈으로 차단한다 | `user.role !== role → "/"` |
| FR-5 | 장바구니가 비어 있으면 결제 버튼을 비활성화한다 | `disabled={items.length===0}` |
| FR-6 | 수량은 1 이상, 재고 이하로 제한한다 | `min={1} max={it.stock}` |
| FR-7 | 5만원 이상 구매 시 배송비(3,000원)를 무료 처리한다 | `FREE_SHIPPING_THRESHOLD` |
| FR-8 | 배송지 미입력 시 주문을 막고 안내(MSG-09)한다 | `placeOrder` 가드 |

## 7. Non-functional Requirements (비기능 요구사항)

| 항목 | 내용 |
|------|------|
| 보안 `[추정]` | 권한 검증이 클라이언트에만 존재 → 서버 측 검증 확인 필요 |
| 접근성 | `aria-label`, `role="alert"` 일부 적용 |
| 성능/호환성 | **[정보 없음 — 별도 확인 필요]** |

## 8. Information Architecture & Flow (정보구조 & 흐름)

| Path | 화면 | 보호 |
|------|------|------|
| `/` | 홈 | 공개 |
| `/login` | 로그인 | 공개 |
| `/products` | 상품목록 | 공개 |
| `/products/:id` | 상품상세 | 공개 |
| `/cart` | 장바구니 | 공개 |
| `/checkout` | 결제 | 🔒 로그인 |
| `/orders` | 주문내역 | 🔒 로그인 |
| `/admin` | 관리자 대시보드 | 🔒 admin |

## 9. Data & API (데이터 & API)

**9.1 API 엔드포인트**

| 엔드포인트 | 메서드 | 용도 | 근거 |
|------------|--------|------|------|
| `/api/auth/login` | POST | 로그인 인증 | `login()` 주석 |
| `/api/orders` | POST | 주문 생성 | `Checkout.placeOrder` |

**9.2 데이터 모델 추정** `[추정]`: `CartItem { id, name, qty, stock }` · `Order { items, address, pay, grandTotal }` · `User { role }`

**9.3 상태 관리 & 데이터 흐름**

| 상태 단위 | 노출 필드/액션 | 읽는 화면 | 쓰는 화면 |
|-----------|----------------|-----------|-----------|
| `useAuth` (lib/auth) | `user`, `login()` | RequireAuth(`user`), Login(`login`) | Login (로그인 성공 시) |
| `useCart` (lib/cart) | `items`, `total`, `updateQty`, `removeItem`, `clear` | Cart, Checkout | Cart(수량/삭제), Checkout(`clear` — 주문 완료 시 비움) |

> `lib/auth.ts`·`lib/cart.ts` 구현 파일은 분석 대상에 없음 → 저장 방식(메모리/localStorage 등) `[정보 없음]`

## 10. Integrations & Analytics (외부 연동 & 측정)

**10.1 외부 연동 인벤토리**

| 연동 대상 | 판정 |
|-----------|------|
| 결제 PG, 소셜 로그인, 지도, 채팅/CS, 푸시 | **해당 없음** — `dependencies`가 `react`, `react-router-dom` 뿐, 서드파티 서비스 SDK·외부 도메인 호출 없음 |

> 결제수단 선택(카드/계좌이체)은 있으나 PG SDK가 없음 → 결제 처리는 서버 위임 또는 미구현 `[정보 없음 — 별도 확인 필요]` (12장 R-2 연계)

**10.2 이벤트/트래킹 명세**

**[정보 없음 — 트래킹 미구현 또는 서버 측]** — gtag/amplitude/mixpanel/dataLayer 등 호출이 코드에 없다.
→ 3.2의 KPI는 실측 근거가 없는 `[추정]` 등급으로 유지된다.

## 11. Scope & Milestones (범위 & 일정)

- **In-scope**: 인증, 상품 탐색, 장바구니, 결제, 주문내역, 관리자 진입
- **Out-of-scope** `[추정]`: 회원가입, PG 연동 상세, 쿠폰/할인, 반품
- **마일스톤**: **[정보 없음 — 별도 확인 필요]**

## 12. Risks & Open Questions (리스크 & 오픈 이슈)

| # | 리스크 / 질문 | 근거 |
|---|----------------|------|
| R-1 | 권한 검증이 클라이언트에만 존재 — 서버 인가 없으면 우회 가능 | `RequireAuth`만 확인 |
| R-2 | PG SDK 부재 — 실제 결제 처리 경로 불명 | 10.1 인벤토리 |
| R-3 | 트래킹 부재 — KPI 측정 체계 미확인 | 10.2 |
| R-4 | 회원가입 화면 부재 — 계정 생성 흐름 미확인 | `/signup` 라우트 없음 |
| R-5 | 5개 화면이 import만 존재 — 내부 동작 미보증 | 1장 분석 범위 한계 |

## 13. Appendix (부록)

**13.1 주요 컴포넌트**
- 소스 분석됨: `Login`, `Cart`, `Checkout`, `RequireAuth`, `router`
- 참조만 확인 `[정보 없음]`: `Home`, `ProductList`, `ProductDetail`, `Orders`, `AdminDashboard`

**13.2 에러/메시지 카탈로그** (문구는 코드 원문 그대로)

| ID | 문구 | 유형 | 노출 조건 | 근거 파일 |
|----|------|------|-----------|-----------|
| MSG-01 | 이메일을 입력해주세요. | 에러 | 이메일 미입력 제출 | `Login.tsx` |
| MSG-02 | 올바른 이메일 형식이 아닙니다. | 에러 | 이메일 정규식 불일치 | `Login.tsx` |
| MSG-03 | 비밀번호는 8자 이상이어야 합니다. | 에러 | 비밀번호 8자 미만 | `Login.tsx` |
| MSG-04 | 이메일 | placeholder | 로그인 폼 | `Login.tsx` |
| MSG-05 | 비밀번호 (8자 이상) | placeholder | 로그인 폼 | `Login.tsx` |
| MSG-06 | 장바구니가 비어 있습니다. | 빈 상태 | `items.length === 0` | `Cart.tsx` |
| MSG-07 | 합계: {N}원 / 결제하기 / 삭제 | 라벨 | 장바구니 화면 | `Cart.tsx` |
| MSG-08 | 이메일 또는 비밀번호가 올바르지 않습니다. | 에러 | 로그인 API 실패 | `Login.tsx` |
| MSG-09 | 배송지를 입력해주세요. | 확인(alert) | 배송지 없이 결제 시도 | `Checkout.tsx` |
| MSG-10 | 배송지 | placeholder | 결제 화면 | `Checkout.tsx` |
| MSG-11 | 신용카드 / 계좌이체 | 옵션 라벨 | 결제수단 선택 | `Checkout.tsx` |
| MSG-12 | (무료배송) | 안내 | `shipping === 0` | `Checkout.tsx` |
| MSG-13 | {N}원 결제 | 버튼 라벨 | 결제 화면 | `Checkout.tsx` |

**13.3 추적성 매트릭스 (Traceability)**

| 요구사항 | User Story | 화면 | 코드 파일 | 관련 메시지 |
|----------|-----------|------|-----------|-------------|
| FR-1 | US-3 | 로그인 | `pages/Login.tsx` | MSG-01~03 |
| FR-2 | US-3 | 로그인 | `pages/Login.tsx` | MSG-08 |
| FR-3 | US-3 | 공통 가드 | `lib/RequireAuth.tsx` | — |
| FR-4 | US-5 | 공통 가드 | `lib/RequireAuth.tsx` | — |
| FR-5 | US-2 | 장바구니 | `pages/Cart.tsx` | MSG-06 |
| FR-6 | US-2 | 장바구니 | `pages/Cart.tsx` | — |
| FR-7 | US-4 | 결제 | `pages/Checkout.tsx` | MSG-12 |
| FR-8 | US-4 | 결제 | `pages/Checkout.tsx` | MSG-09 |

**13.4 용어 정의**: `RequireAuth`(인증 가드) · `grandTotal`(배송비 포함 결제금액) · `FREE_SHIPPING_THRESHOLD`(무료배송 기준액 50,000)

**13.5 QA 체크리스트**

- [ ] 미로그인 `/checkout` 진입 시 로그인 리다이렉트 후 원래 경로 복귀 (FR-3)
- [ ] user 계정 `/admin` 접근 시 홈 차단 (FR-4)
- [ ] 합계 49,999원/50,000원 경계에서 배송비 판정 (FR-7)
- [ ] 빈 장바구니 결제 버튼 비활성 + MSG-06 노출 (FR-5)
- [ ] MSG-01~03 각 검증 실패 케이스별 정확한 문구 노출 (FR-1)
