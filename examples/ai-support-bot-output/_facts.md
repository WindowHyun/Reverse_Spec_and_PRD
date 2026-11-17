<!-- scripts/extract.py 출력 — 결정적 사실 계층. LLM은 이 표를 근거로만 해석한다. -->

## 1-J. 하드코딩 시크릿 노출 스캔

발견된 항목 없음 (스캔 범위 내).

## 1-H. As-Is 스냅샷 (비교 기준선)

| 항목 | 값 |
|---|---|
| 기준 커밋 | `6e68087a1301770ac222d3b61c1291b3194a4094` |
| 커밋 시점 | 2026-10-10 04:42:48 +0000 |
| 분석 파일 수 | 12 |
| 분석 파일 | `package.json` · `src/evals/chatbot.eval.ts` · `src/lib/RequireAuth.tsx` · `src/lib/auth.ts` · `src/lib/openaiClient.ts` · `src/lib/validate.ts` · `src/pages/AdminEvalDashboard.tsx` · `src/pages/Chat.tsx` · `src/pages/Home.tsx` · `src/pages/Login.tsx` · `src/prompts/systemPrompt.ts` · `src/router.tsx` |

## 1-A. 라우트 맵

| Path | 컴포넌트 | 보호 | 근거 파일 |
|---|---|---|---|
| / | Home | 공개 | `src/router.tsx` |
| /admin/evals | AdminEvalDashboard | 🔒 admin | `src/router.tsx` |
| /chat | Chat | 🔒 로그인 | `src/router.tsx` |
| /login | Login | 공개 | `src/router.tsx` |

## 1-B. 컴포넌트 분석 범위

| 컴포넌트 | 소스 파일 | 분석 가능 |
|---|---|---|
| AdminEvalDashboard | `src/pages/AdminEvalDashboard.tsx` | ✅ 소스 포함 |
| AuthContext | `src/lib/auth.ts` | ✅ 소스 포함 |
| Chat | `src/pages/Chat.tsx` | ✅ 소스 포함 |
| GOLDEN_CASES | `src/evals/chatbot.eval.ts` | ✅ 소스 포함 |
| Home | `src/pages/Home.tsx` | ✅ 소스 포함 |
| Login | `src/pages/Login.tsx` | ✅ 소스 포함 |
| RequireAuth | `src/lib/RequireAuth.tsx` | ✅ 소스 포함 |
| SYSTEM_PROMPT | `src/prompts/systemPrompt.ts` | ✅ 소스 포함 |

## 1-C. API 호출

| 엔드포인트 | 메서드 | 근거 |
|---|---|---|
| `/api/auth/login` | POST | `src/pages/Login.tsx (주석)` |
| `/api/chat` | POST | `src/pages/Chat.tsx (주석)` |

## 1-C. 비즈니스 상수

| 상수 | 값 | 근거 파일 |
|---|---|---|
| `MAX_MESSAGE_LENGTH` | 1000 | `src/lib/validate.ts` |

## 1-C. 검증/차단 규칙

| 유형 | 조건 | 효과 | 근거 파일 |
|---|---|---|---|
| 동작 차단 | `!input.trim()` | 버튼 비활성화 | `src/pages/Chat.tsx` |
| 입력 검증 | `!text.trim()` | 메시지 "메시지를 입력해주세요." | `src/lib/validate.ts` |
| 입력 검증 | `text.length > MAX_MESSAGE_LENGTH` | 메시지 "메시지는 1000자를 넘을 수 없습니다." | `src/lib/validate.ts` |
| 필수값 | `email 조건 불충족` | 알림 "이메일을 입력해주세요." 후 중단 | `src/pages/Login.tsx` |

## 1-D. 화면 전환 호출

| 출발(파일) | 도착 경로 | 방식 |
|---|---|---|
| `src/lib/RequireAuth.tsx` | `/chat` | &lt;Navigate&gt; |
| `src/lib/RequireAuth.tsx` | `/login` | &lt;Navigate&gt; |
| `src/pages/Login.tsx` | `/chat` | navigate() |

## 1-E. 사용자 노출 문구 (에러/메시지 카탈로그 원자료)

| ID | 문구 | 유형 | 노출 조건 | 근거 파일 |
|---|---|---|---|---|
| MSG-01 | 메시지는 1000자를 넘을 수 없습니다. | 에러 | `text.length > MAX_MESSAGE_LENGTH` | `src/lib/validate.ts` |
| MSG-02 | 메시지를 입력해주세요. | 에러 | `!text.trim()` | `src/lib/validate.ts` |
| MSG-03 | 챗봇 품질 eval 리포트 | UI 텍스트 | - | `src/pages/AdminEvalDashboard.tsx` |
| MSG-04 | eval 리포트 | aria-label | - | `src/pages/AdminEvalDashboard.tsx` |
| MSG-05 | AI 상담 | UI 텍스트 | - | `src/pages/Chat.tsx` |
| MSG-06 | 아직 대화가 없습니다. 궁금한 점을 물어보세요. | UI 텍스트 | - | `src/pages/Chat.tsx` |
| MSG-07 | 전송 | UI 텍스트 | - | `src/pages/Chat.tsx` |
| MSG-08 | 상담 채팅 | aria-label | - | `src/pages/Chat.tsx` |
| MSG-09 | 메시지를 입력하세요 | placeholder | - | `src/pages/Chat.tsx` |
| MSG-10 | AI 고객지원 챗봇 | UI 텍스트 | - | `src/pages/Home.tsx` |
| MSG-11 | 로그인하고 상담 시작하기 | UI 텍스트 | - | `src/pages/Home.tsx` |
| MSG-12 | 로그인하면 24시간 AI 상담원과 대화할 수 있습니다. | UI 텍스트 | - | `src/pages/Home.tsx` |
| MSG-13 | 로그인 | UI 텍스트 | - | `src/pages/Login.tsx` |
| MSG-14 | 로그인 | aria-label | - | `src/pages/Login.tsx` |
| MSG-15 | 이메일 | placeholder | - | `src/pages/Login.tsx` |
| MSG-16 | 이메일을 입력해주세요. | 확인(alert) | `코드 분기` | `src/pages/Login.tsx` |

## 1-F. 상태 관리 사용처

| 상태 단위 | 사용 필드/액션 | 사용 파일 |
|---|---|---|
| `(createContext 정의)` | - | `src/lib/auth.ts` |
| `useAuth` | user | `src/lib/RequireAuth.tsx` |
| `useAuth` | user | `src/pages/Chat.tsx` |
| `useLocation` | location | `src/lib/RequireAuth.tsx` |
| `useNavigate` | navigate | `src/pages/Login.tsx` |

## 1-G. 외부 연동 & 트래킹

서드파티 의존성: `@langchain/core`, `openai`

트래킹 호출: **[정보 없음 — 트래킹 미구현 또는 서버 측]**

## 1-K. AI/LLM 연동 감지

AI/LLM SDK 의존성: `@langchain/core`, `openai`

| 모델 ID 리터럴 | 추정 벤더 | 근거 파일 |
|---|---|---|
| `gpt-3.5-turbo` | OpenAI | `src/lib/openaiClient.ts` |
| `gpt-4o-mini` | OpenAI | `src/lib/openaiClient.ts` |

프롬프트 관련 파일(파일명 패턴만, 내용 미해석): `src/prompts/systemPrompt.ts`

평가(eval) 관련 파일(파일명 패턴만, 내용 미해석): `src/evals/chatbot.eval.ts`

<!-- 추출 통계: 라우트 4 · 컴포넌트 8 · API 2 · 상수 1 · 규칙 4 · 전환 3 · 문구 16 · 상태 5 · 트래킹 0 · AI연동(SDK 2/모델ID 2/프롬프트파일 1/eval파일 1) -->
