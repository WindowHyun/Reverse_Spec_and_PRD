# 역기획 PRD — ai-support-bot

> 본 문서는 `examples/ai-support-bot/` 코드를 **정적 분석**해 역으로 재구성한 제품 요구사항 문서다.
> `[추정]` 항목은 코드에 의도가 명시되지 않아 추론한 것으로 교차 검증이 필요하며,
> `[정보 없음 — 별도 확인 필요]` 항목은 코드에 단서가 없다.

## 1. Overview (개요)

| 항목 | 내용 |
|------|------|
| 제품 한 줄 요약 | 로그인 사용자가 OpenAI 기반 챗봇과 상담하고, 관리자는 응답 품질 eval 리포트를 보는 AI 고객지원 서비스 |
| 문서 목적 | 완성된 프론트엔드 코드로부터 제품 요구사항을 역추적 (역기획 PRD) |
| 분석 대상 | `examples/ai-support-bot/src` (React 18 + React Router 6 + openai SDK, 소스 12개 파일) |
| 분석 범위 한계 | 라우터가 참조하는 화면 4개 모두 소스 포함(분석 가능). `/api/chat` 서버 측 구현(실제 모델 호출·응답 가공 로직)은 분석 대상 밖 → `[정보 없음]` |

### 1.4 As-Is 스냅샷 (비교 기준선)

| 항목 | 값 |
|------|-----|
| 기준 커밋 | `6e68087a1301770ac222d3b61c1291b3194a4094` |
| 분석 시점 | 2026-10-10 04:42:48 +0000 |
| 분석 파일 | `package.json`, `src/router.tsx`, `src/lib/RequireAuth.tsx`, `src/lib/auth.ts`, `src/lib/openaiClient.ts`, `src/lib/validate.ts`, `src/pages/*.tsx`, `src/prompts/systemPrompt.ts`, `src/evals/chatbot.eval.ts` |
| 감지된 AI 연동 (1-K) | SDK `openai`, `@langchain/core` · 모델 ID `gpt-4o-mini`, `gpt-3.5-turbo` (`src/lib/openaiClient.ts`) |

> 이 커밋 이후 **코드가 변경되면** 본 문서의 사실 기술은 재검증이 필요하다.
> 추가로, 이 저장소는 AI/LLM 연동이 감지됐으므로(1-K) **모델 버전(`DEFAULT_MODEL`/
> `FALLBACK_MODEL`)이나 `src/prompts/systemPrompt.ts`의 프롬프트가 바뀌는 경우에도**
> 본 문서(특히 3장 성공지표, 9.4, 12장)는 코드 변경 없이 동작이 달라질 수 있으므로
> 재검증이 필요하다.

## 2. Background & Problem (배경 & 문제 정의)

- **추정 배경** `[추정]` — 상담원 응대 없이도 1차 문의를 처리하는 24시간 AI 상담 채널. (`package.json.description` "로그인 사용자가 OpenAI 기반 상담 챗봇과 대화" 근거)
- **해결하려는 문제** `[추정]` — 사람이 상주하지 않는 시간대의 단순 문의(배송/환불 등) 응대 지연 문제 (`src/evals/chatbot.eval.ts`의 골든셋 주제 "배송"/"환불" 근거)

## 3. Goals & Success Metrics (목표 & 성공지표)

| 구분 | 내용 | 근거 |
|------|------|------|
| 제품 목표 | 로그인 사용자가 AI 챗봇으로 1차 상담을 받는 흐름 제공 | 라우트 `/login → /chat` |
| KPI 후보 `[추정]` | 채팅 세션 시작 수, 메시지 전송 수 | `POST /api/chat` 호출, 트래킹 코드는 없음 |
| 비목표 (Non-goals) | **[정보 없음 — 별도 확인 필요]** | — |

> **KPI 근거 등급 주의**: 10.2 이벤트/트래킹 명세 결과 **트래킹 코드가 없어** 위 KPI는
> 전환 액션 기반 `[추정]`이다. 실측 지표 체계는 별도 확인이 필요하다.
>
> **AI PRD 관련 주의** — 1-K에서 AI 연동이 감지됐지만, "챗봇 응답 품질"을 측정할
> **허용 오차 범위나 품질 지표(정확도/유해성/만족도 등)는 코드 어디에도 숫자로
> 적혀 있지 않다.** `src/evals/chatbot.eval.ts`에 골든셋 2건(입력→기대 주제)이
> 존재해 "품질을 평가하려 한 흔적"은 있지만, 합격선(threshold)이나 채점 로직은
> 분석 대상에 없다. 이 값을 추정해서 채우지 않았다 — PM이 직접 정의해야 한다
> (12장 R-AI-1 연계).

## 4. Users & Personas (사용자 & 페르소나)

| 페르소나 | 설명 | 근거 |
|----------|------|------|
| 비로그인 방문자 | 홈/로그인 화면만 접근 | `/`, `/login`이 가드 없음 |
| 일반 사용자 (user) | 로그인 후 AI 챗봇과 상담 | `/chat`이 `RequireAuth`로 보호 |
| 관리자 (admin) | 챗봇 품질 eval 리포트 열람 | `RequireAuth role="admin"` |

## 5. User Stories & Journey (사용자 스토리 & 여정)

**5.1 사용자 여정 다이어그램** (flowgen.py 생성 — 점선은 조건부/추정 전환, 🔒는 보호 라우트)

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1176 100" width="100%" style="max-width:1176px;font-family:'Noto Sans KR',sans-serif;">
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#5a6672"/></marker></defs>
<path d="M 192 50.0 C 228.0 50.0, 228.0 50.0, 264 50.0" fill="none" stroke="#5a6672" stroke-width="1.6" marker-end="url(#arrow)" stroke-dasharray="5 4"/>
<text x="228.0" y="42.0" font-size="11" fill="#41505c" text-anchor="middle">[추정] 로그인하고 상담 시작하기 클릭</text>
<path d="M 432 50.0 C 468.0 50.0, 468.0 50.0, 504 50.0" fill="none" stroke="#5a6672" stroke-width="1.6" marker-end="url(#arrow)"/>
<text x="468.0" y="42.0" font-size="11" fill="#41505c" text-anchor="middle">로그인 완료 (navigate)</text>
<rect x="24" y="24" width="168" height="52" rx="8" fill="#f4f6f8" stroke="#8a97a3" stroke-width="1.6"/>
<text x="108.0" y="54.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">홈 /</text>
<rect x="264" y="24" width="168" height="52" rx="8" fill="#f4f6f8" stroke="#8a97a3" stroke-width="1.6"/>
<text x="348.0" y="54.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">로그인 /login</text>
<rect x="504" y="24" width="168" height="52" rx="8" fill="#e8f0fa" stroke="#2e75b6" stroke-width="1.6"/>
<text x="588.0" y="47.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">AI 상담 /chat</text>
<text x="588.0" y="64.0" font-size="10" fill="#2e75b6" text-anchor="middle">🔒</text>
<rect x="984" y="24" width="168" height="52" rx="8" fill="#fdf1e2" stroke="#c47a00" stroke-width="1.6"/>
<text x="1068.0" y="47.0" font-size="12.5" font-weight="bold" fill="#22303c" text-anchor="middle">eval 리포트 /admin/evals</text>
<text x="1068.0" y="64.0" font-size="10" fill="#c47a00" text-anchor="middle">🔒 admin</text>
</svg>

> `/admin/evals`는 `/chat`과 코드상 전환 관계(링크·navigate)가 없어 독립 노드로 배치했다
> (실제 접근 경로는 URL 직접 이동으로 추정되며, 코드에 근거가 없어 간선을 그리지 않았다).
> 다이어그램 원본 데이터: `_flow.json` (같은 JSON → 항상 같은 SVG)

**5.2 User Story 목록**

| ID | User Story | 대응 화면 | 근거 |
|----|-----------|-----------|------|
| US-1 | 방문자로서, 로그인 없이 서비스를 소개받고 로그인 경로를 찾고 싶다 | Home | `<Link to="/login">` |
| US-2 | 사용자로서, 로그인해서 AI 상담을 시작하고 싶다 | Login | `navigate("/chat")` |
| US-3 | 사용자로서, 메시지를 입력해 AI 챗봇의 답변을 받고 싶다 | Chat | `POST /api/chat` |
| US-4 | 사용자로서, 빈 메시지나 너무 긴 메시지는 보내지 않도록 안내받고 싶다 | Chat | `validateMessage` |
| US-5 | 관리자로서, 챗봇 응답 품질 골든셋 결과를 확인하고 싶다 | AdminEvalDashboard | `GOLDEN_CASES` |

## 6. Functional Requirements (기능 요구사항)

| ID | 요구사항 | 코드 근거 |
|----|----------|-----------|
| FR-1 | 이메일 미입력 시 로그인을 막고 안내(MSG-16)한다 | `Login.login()` |
| FR-2 | 로그인 성공 시 `/chat`으로 이동한다 | `navigate("/chat")` |
| FR-3 | 미인증 사용자가 `/chat`, `/admin/evals` 접근 시 `/login`으로 보낸다 | `RequireAuth` |
| FR-4 | admin 권한이 없으면 `/admin/evals` 접근을 `/chat`으로 차단한다 | `user.role !== role → "/chat"` |
| FR-5 | 빈 메시지는 전송을 차단한다(입력 검증 + 버튼 비활성) | `validateMessage`, `disabled={!input.trim()}` |
| FR-6 | 메시지가 1000자를 넘으면 전송을 막고 안내(MSG-01)한다 | `MAX_MESSAGE_LENGTH` |
| FR-7 | 전송된 메시지는 `/api/chat`에 사용자 ID와 함께 POST된다 | `fetch("/api/chat", ...)` |
| FR-8 | 대화가 없을 때는 안내 문구(MSG-06)를 보여준다 | `messages.length === 0` |

## 7. Non-functional Requirements (비기능 요구사항)

| 항목 | 내용 |
|------|------|
| 보안 `[추정]` | 권한 검증이 클라이언트에만 존재 → 서버 측 검증 확인 필요. `OPENAI_API_KEY`는 `process.env`로 참조되나 실제 값은 시크릿 스캔(1-J)에서 미발견 |
| 접근성 | `aria-label` 적용 |
| 성능/호환성 | **[정보 없음 — 별도 확인 필요]** |

## 8. Information Architecture & Flow (정보구조 & 흐름)

| Path | 화면 | 보호 |
|------|------|------|
| `/` | 홈 | 공개 |
| `/login` | 로그인 | 공개 |
| `/chat` | AI 상담 | 🔒 로그인 |
| `/admin/evals` | eval 리포트 | 🔒 admin |

## 9. Data & API (데이터 & API)

**9.1 API 엔드포인트**

| 엔드포인트 | 메서드 | 용도 | 근거 |
|------------|--------|------|------|
| `/api/auth/login` | POST | 로그인 인증 | `Login.login()` 주석 |
| `/api/chat` | POST | 챗봇 메시지 전송 | `Chat.send()` 주석 |

**9.2 데이터 모델 추정** `[추정]`: `User { id, role }` · `ChatMessage { role, content }`

**9.3 상태 관리 & 데이터 흐름**

| 상태 단위 | 노출 필드/액션 | 읽는 화면 | 쓰는 화면 |
|-----------|----------------|-----------|-----------|
| `AuthContext`/`useAuth` (lib/auth) | `user` | RequireAuth, Chat | **[정보 없음]** — 로그인 성공 시 context를 어디서 채우는지 분석 대상 밖 |

**9.4 AI/LLM 연동** (1-K 사실 표 그대로 — 추정 없이 코드 문자열만 기재)

| 구분 | 내용 | 근거 |
|------|------|------|
| SDK 의존성 | `openai` (dependencies), `@langchain/core` (devDependencies) | `package.json` |
| 모델 ID 리터럴 | `gpt-4o-mini` (`DEFAULT_MODEL`), `gpt-3.5-turbo` (`FALLBACK_MODEL`) | `src/lib/openaiClient.ts` |
| 프롬프트 관련 파일 | `src/prompts/systemPrompt.ts` | 파일명 패턴 매칭 — 내용은 `SYSTEM_PROMPT` 상수로 코드에 존재하나, "이 프롬프트가 올바른지"는 평가하지 않음 |
| 평가(eval) 관련 파일 | `src/evals/chatbot.eval.ts` | 파일명 패턴 매칭 — 골든셋 2건 존재(13.6 참조) |

> `@langchain/core`는 의존성에는 있으나 실제 `import` 사용처는 분석 대상 파일에서
> 발견되지 않았다 — 설치만 되어 있고 미사용이거나, 서버 측(분석 대상 밖)에서
> 쓰일 수 있다 `[정보 없음 — 별도 확인 필요]`.

## 10. Integrations & Analytics (외부 연동 & 측정)

**10.1 외부 연동 인벤토리**

| 연동 대상 | 판정 |
|-----------|------|
| `openai` | 챗봇 응답 생성 (`src/lib/openaiClient.ts`) |
| `@langchain/core` | devDependencies에만 존재, 사용처 미발견 `[정보 없음]` |
| 결제 PG, 소셜 로그인, 지도, 분석 도구 | **해당 없음** |

**10.2 이벤트/트래킹 명세**

**[정보 없음 — 트래킹 미구현 또는 서버 측]** — gtag/amplitude/mixpanel/dataLayer 등 호출이 코드에 없다.
→ 3.2의 KPI는 실측 근거가 없는 `[추정]` 등급으로 유지된다.

## 11. Scope & Milestones (범위 & 일정)

- **In-scope**: 로그인, AI 챗봇 상담, 메시지 길이 검증, 관리자 eval 리포트 열람
- **Out-of-scope** `[추정]`: 회원가입, 채팅 이력 저장/조회, 다국어 지원
- **마일스톤**: **[정보 없음 — 별도 확인 필요]**

## 12. Risks & Open Questions (리스크 & 오픈 이슈)

| # | 리스크 / 질문 | 근거 |
|---|----------------|------|
| R-1 | 권한 검증이 클라이언트에만 존재 — 서버 인가 없으면 `/chat`, `/admin/evals` 우회 가능 | `RequireAuth`만 확인 |
| R-2 | 트래킹 부재 — KPI 측정 체계 미확인 | 10.2 |
| R-3 | `AuthContext`를 채우는 로그인 연동 코드가 분석 대상 밖 — 실제 인증 흐름 미보증 | 9.3 |
| R-4 | `@langchain/core` 의존성은 있으나 사용처 미발견 — 미사용 의존성인지 서버 측 사용인지 불명 | 9.4 |
| **R-AI-1** | **[AI 기능]** `openai` SDK·모델(`gpt-4o-mini`/`gpt-3.5-turbo`) 사용이 코드에서 확인됨 — 완료기준 허용오차·품질지표·eval 기준(합격선)은 코드에 없어 **PM이 별도 정의/교차검증 필요** | 1-K, 3장 AI PRD 주의 |

## 13. Appendix (부록)

**13.1 주요 컴포넌트**
- 소스 분석됨: `Home`, `Login`, `Chat`, `AdminEvalDashboard`, `RequireAuth`, `router`

**13.2 에러/메시지 카탈로그** (문구는 코드 원문 그대로)

| ID | 문구 | 유형 | 노출 조건 | 근거 파일 |
|----|------|------|-----------|-----------|
| MSG-01 | 메시지는 1000자를 넘을 수 없습니다. | 에러 | `text.length > MAX_MESSAGE_LENGTH` | `lib/validate.ts` |
| MSG-02 | 메시지를 입력해주세요. | 에러 | `!text.trim()` | `lib/validate.ts` |
| MSG-06 | 아직 대화가 없습니다. 궁금한 점을 물어보세요. | UI 텍스트 | 대화 없음 | `pages/Chat.tsx` |
| MSG-09 | 메시지를 입력하세요 | placeholder | 채팅 입력란 | `pages/Chat.tsx` |
| MSG-16 | 이메일을 입력해주세요. | 확인(alert) | 이메일 미입력 제출 | `pages/Login.tsx` |

> 전체 16건은 `_facts.md` 1-E 표 참조 (UI 텍스트·aria-label 등 포함).

**13.3 추적성 매트릭스 (Traceability)**

| 요구사항 | User Story | 화면 | 코드 파일 | 관련 메시지 |
|----------|-----------|------|-----------|-------------|
| FR-1 | US-2 | 로그인 | `pages/Login.tsx` | MSG-16 |
| FR-2 | US-2 | 로그인 | `pages/Login.tsx` | — |
| FR-3 | US-2,US-5 | 공통 가드 | `lib/RequireAuth.tsx` | — |
| FR-4 | US-5 | 공통 가드 | `lib/RequireAuth.tsx` | — |
| FR-5 | US-4 | 채팅 | `pages/Chat.tsx` | MSG-02 |
| FR-6 | US-4 | 채팅 | `lib/validate.ts` | MSG-01 |
| FR-7 | US-3 | 채팅 | `pages/Chat.tsx` | — |
| FR-8 | US-3 | 채팅 | `pages/Chat.tsx` | MSG-06 |

**13.4 용어 정의**: `RequireAuth`(인증 가드) · `DEFAULT_MODEL`/`FALLBACK_MODEL`(챗봇 응답 생성에 쓰는 OpenAI 모델) · `GOLDEN_CASES`(챗봇 응답 품질을 가늠하기 위한 입력/기대주제 쌍)

**13.5 QA 체크리스트**

- [ ] 미로그인 `/chat` 진입 시 `/login` 리다이렉트 (FR-3)
- [ ] user 계정 `/admin/evals` 접근 시 `/chat`으로 차단 (FR-4)
- [ ] 빈 메시지 전송 버튼 비활성 + 알림 미노출(버튼 자체가 막음) (FR-5)
- [ ] 1000자 초과 메시지 전송 시 MSG-01 노출, 전송 안 됨 (FR-6)
- [ ] 이메일 없이 로그인 시도 시 MSG-16 노출 (FR-1)

**13.6 발견된 AI 평가(eval) 체계** (1-K 발견 있음 — 조건부 작성)

- `src/evals/chatbot.eval.ts` — 파일명 패턴으로 발견. 골든셋 2건(`배송`, `환불` 주제의
  입력/기대주제 쌍)을 `GOLDEN_CASES`로 export하며, `AdminEvalDashboard`가 이를 읽어
  표시한다(소스 확인됨).
- **코드에서 확인되지 않는 것** `[정보 없음 — 별도 확인 필요]`: 이 골든셋을 실제로
  채점하는 로직(모델 응답과 `expectedTopic`을 비교하는 코드), 합격선(threshold),
  CI에서 자동 실행되는지 여부 — 전부 분석 대상 파일에는 없다. "평가 체계가
  존재한다"는 사실과 "그 평가가 신뢰할 만한가"는 별개이며, 후자는 추정하지 않았다.
