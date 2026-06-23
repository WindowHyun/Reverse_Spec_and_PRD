# -*- coding: utf-8 -*-
import markdown, pathlib

# ── reverse-prd Step 3 결과: mock-shop 분석으로 구성한 PRD (Markdown) ──
content = r"""
# 역기획 PRD — mock-shop

> 본 문서는 `examples/mock-shop/` 코드를 **정적 분석**해 역으로 재구성한 제품 요구사항 문서다.
> `[추정]` 표기 항목은 코드에 의도가 명시되어 있지 않아 추론한 것으로, 반드시 교차 검증이 필요하다.

## 1. Overview (개요)

| 항목 | 내용 |
|------|------|
| 제품 한 줄 요약 | 로그인 기반 온라인 상점 — 상품 탐색부터 장바구니·결제·주문내역까지 제공하는 스토어프론트 |
| 문서 목적 | 완성된 프론트엔드 코드로부터 제품 요구사항을 역추적 (역기획 PRD) |
| 분석 대상 | `examples/mock-shop/` (React 18 + React Router 6, 파일 6개) |
| 도메인 | e-commerce (스토어프론트) — `package.json.description` "Minimal storefront with auth, cart and checkout" 근거 |
| 분석 범위 한계 | 라우터가 참조하는 화면 컴포넌트는 8개지만, **소스가 포함된 건 Login·Cart·Checkout 3개뿐**. Home·ProductList·ProductDetail·Orders·AdminDashboard는 라우팅에서 import만 확인되어 화면 내부 동작은 `[정보 없음 — 별도 확인 필요]` |

## 2. Background & Problem (배경 & 문제 정의)

- **2.1 추정 배경** `[추정]` — 사용자가 상품을 탐색하고 결제까지 완료하는 최소 단위 온라인 판매 채널이 필요했던 것으로 보인다. (`description`의 "Minimal storefront" 근거)
- **2.2 해결하려는 문제** `[추정]` — 비로그인 탐색은 허용하되 결제·주문 단계는 인증을 강제해, 미인증 구매 시도로 인한 주문 데이터 무결성 문제를 방지한다. (`RequireAuth` 가드 근거)

## 3. Goals & Success Metrics (목표 & 성공지표)

| 구분 | 내용 | 근거 |
|------|------|------|
| 제품 목표 | 방문 → 상품 탐색 → 장바구니 → 결제 완료의 구매 퍼널 제공 | 라우트 `/products → /cart → /checkout → /orders` |
| KPI 후보 `[추정]` | 결제 완료 수(주문 전환율) | `POST /api/orders` 호출 = 전환 액션 |
| KPI 후보 `[추정]` | 로그인 전환율, 장바구니→결제 진입률 | `login()`, `/checkout` 진입 가드 |
| 비목표 (Non-goals) | **[정보 없음 — 별도 확인 필요]** — 반품/교환, 쿠폰, 위시리스트 등은 코드에 없음 | — |

## 4. Users & Personas (사용자 & 페르소나)

| 페르소나 | 설명 | 근거 |
|----------|------|------|
| 비로그인 방문자 `[추정]` | 로그인 없이 홈/상품목록/상세/장바구니까지 탐색 가능 | 해당 라우트에 `RequireAuth` 미적용 |
| 일반 구매자 (user) | 로그인 후 결제·주문내역 조회 | `/checkout`, `/orders`가 `RequireAuth`로 보호 |
| 관리자 (admin) | 관리자 대시보드 접근 | `RequireAuth role="admin"` (`/admin`) |

## 5. User Stories & Journey (사용자 스토리 & 여정)

**5.1 핵심 사용자 여정 (구매 퍼널)**

```
[홈 /] → [상품목록 /products] → [상품상세 /products/:id]
       → [장바구니 /cart] --(로그인 필요)--> [로그인 /login]
       → [결제 /checkout] → [주문완료 → 주문내역 /orders]
```

**5.2 User Story 목록**

| ID | User Story | 대응 화면/컴포넌트 | 근거 |
|----|-----------|--------------------|------|
| US-1 | 방문자로서, 로그인 없이 상품을 둘러보고 싶다 | ProductList, ProductDetail `[정보 없음]` | 가드 없는 라우트 (단, 두 컴포넌트 소스 미포함 → 화면 내부 동작 미확인) |
| US-2 | 구매자로서, 장바구니 수량을 조절하고 합계를 확인하고 싶다 | Cart | `updateQty`, `total` |
| US-3 | 구매자로서, 결제 전 반드시 로그인하고 원래 페이지로 돌아오고 싶다 | RequireAuth, Login | `state={{from}}` 후 복귀 |
| US-4 | 구매자로서, 배송지·결제수단을 입력해 주문을 완료하고 싶다 | Checkout | `placeOrder` → `POST /api/orders` |
| US-5 | 관리자로서, 일반 사용자는 못 보는 대시보드에 접근하고 싶다 | AdminDashboard `[정보 없음]` | `role="admin"` 가드 (대시보드 내용은 소스 미포함) |

## 6. Functional Requirements (기능 요구사항)

| ID | 요구사항 | 유형 | 코드 근거 |
|----|----------|------|-----------|
| FR-1 | 시스템은 이메일 형식·비밀번호 8자 이상을 검증해야 한다 | FR | `Login.validate()` |
| FR-2 | 인증 실패 시 "이메일 또는 비밀번호가 올바르지 않습니다" 메시지를 노출한다 | FR | `catch` 분기 |
| FR-3 | 미인증 사용자가 보호 경로 접근 시 로그인으로 리다이렉트하고, 로그인 후 원래 경로로 복귀한다 | FR | `RequireAuth` + `from` |
| FR-4 | admin 권한이 없으면 `/admin` 접근을 홈으로 차단한다 | FR | `role !== role → "/"` |
| FR-5 | 장바구니가 비어 있으면 결제 버튼을 비활성화한다 | FR | `disabled={items.length===0}` |
| FR-6 | 수량은 1 이상, 재고(stock) 이하로 제한한다 | FR | `min={1} max={it.stock}` |
| FR-7 | 5만원 이상 구매 시 배송비를 무료 처리한다 (기본 배송비 3,000원) | FR | `FREE_SHIPPING_THRESHOLD` |
| FR-8 | 배송지 미입력 시 주문을 막고 안내한다 | FR | `placeOrder` 가드 |

## 7. Non-functional Requirements (비기능 요구사항)

| 항목 | 내용 |
|------|------|
| 보안 `[추정]` | 인증 상태로 결제/주문 보호. 단, 권한 검증이 **클라이언트 사이드**에만 존재 → 서버 측 검증 필요성 확인 요망 |
| 접근성 | 폼에 `aria-label`, 오류에 `role="alert"` 일부 적용됨 |
| 성능 / 호환성 | **[정보 없음 — 별도 확인 필요]** |

## 8. Information Architecture & Flow (정보구조 & 흐름)

| Depth | Path | 화면 | 보호 |
|-------|------|------|------|
| 1 | `/` | 홈 | 공개 |
| 1 | `/login` | 로그인 | 공개 |
| 1 | `/products` | 상품목록 | 공개 |
| 2 | `/products/:id` | 상품상세 | 공개 |
| 1 | `/cart` | 장바구니 | 공개 |
| 1 | `/checkout` | 결제 | 🔒 로그인 |
| 1 | `/orders` | 주문내역 | 🔒 로그인 |
| 1 | `/admin` | 관리자 대시보드 | 🔒 admin |

## 9. Data & API (데이터 & API)

| 엔드포인트 | 메서드 | 용도 | 근거 |
|------------|--------|------|------|
| `/api/auth/login` | POST | 로그인 인증 | `login()` 주석 |
| `/api/orders` | POST | 주문 생성 | `Checkout.placeOrder` |

데이터 모델 추정 `[추정]`: `CartItem { id, name, qty, stock }`, `Order { items, address, pay, grandTotal }`, `User { role }`

## 10. Scope & Milestones (범위 & 일정)

- **In-scope**: 인증, 상품 탐색, 장바구니, 결제, 주문내역, 관리자 진입
- **Out-of-scope** `[추정]`: 회원가입, 결제 PG 연동 상세, 쿠폰/할인, 반품 (코드에 없음)
- **마일스톤**: **[정보 없음 — 별도 확인 필요]**

## 11. Risks & Open Questions (리스크 & 오픈 이슈)

| # | 리스크 / 질문 | 근거 |
|---|----------------|------|
| R-1 | 권한 검증이 클라이언트 측에만 존재 — 서버 측 인가 없으면 우회 가능 | `RequireAuth`만 확인됨 |
| R-2 | 결제수단이 카드/계좌이체 2종뿐, 실제 PG 연동 흐름 불명 | `Checkout` `<select>` |
| R-3 | 배경·목표·KPI·페르소나는 추정 — 실제 제품 의도 확인 필요 | 코드에 의도 미기재 |
| R-4 | 회원가입 화면 부재 — 계정 생성 흐름 누락 또는 외부 처리? | 라우트에 `/signup` 없음 |

## 12. Appendix (부록)

**12.1 주요 컴포넌트**

- 소스 분석됨: `Login`, `Cart`, `Checkout`, `RequireAuth`, `router`
- 라우팅에서 참조만 확인 (내부 `[정보 없음]`): `Home`, `ProductList`, `ProductDetail`, `Orders`, `AdminDashboard`

**12.2 용어 정의**: `RequireAuth`(인증 가드), `grandTotal`(배송비 포함 결제금액), `FREE_SHIPPING_THRESHOLD`(무료배송 기준액 50,000)

**12.3 QA 체크리스트**

- [ ] 미로그인 상태로 `/checkout` 직접 진입 시 로그인 리다이렉트되는가
- [ ] 로그인 후 원래 경로(`from`)로 복귀하는가
- [ ] user 계정으로 `/admin` 접근 시 홈으로 차단되는가
- [ ] 합계 49,999원/50,000원 경계에서 배송비가 올바른가
- [ ] 빈 장바구니에서 결제 버튼이 비활성인가
"""

md_html = markdown.markdown(content, extensions=['tables', 'toc', 'fenced_code'])

# ── reverse-prd 스킬의 PDF 템플릿 CSS를 그대로 사용 (출력만 HTML) ──
html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
  body {{ font-family: 'Noto Sans KR', sans-serif; font-size: 11pt; line-height: 1.8;
          color: #1a1a1a; max-width: 860px; margin: 0 auto; padding: 32px; background:#fff; }}
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
  blockquote {{ border-left: 4px solid #c47a00; background:#fff8ec; margin:16px 0; padding:8px 16px; color:#7a5200; }}
</style>
</head>
<body>
{md_html}
</body>
</html>"""

out = pathlib.Path("/home/user/Skills/examples/reverse-prd-output")
out.mkdir(parents=True, exist_ok=True)
p = out / "reverse_prd_mock-shop_sample.html"
p.write_text(html_template, encoding="utf-8")
print(f"OK: {p}")
