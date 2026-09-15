#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
결정적 코드 사실 추출기 (reverse-spec / reverse-prd 공용).

reference.md의 1-A~1-H 추출 규칙을 파서(정규식)로 구현한다. LLM 없이 동작하며,
같은 입력 → 항상 같은 출력 (모든 목록 정렬, 실행 시각 미포함 — 스냅샷은 커밋 시각 사용).

역할 분담(하이브리드):
  - 이 스크립트: 사실(라우트/컴포넌트/API/상수/규칙/문구/상태/연동/스냅샷) 추출
  - LLM: 사실 표를 근거로 한 해석·서술 (사실 표 밖의 내용을 도입하지 않음)

사용법:
  python extract.py <대상경로> --output facts.md [--emit-flow flow.json]

출력:
  facts.md   : 1-A~1-H, 1-J 사실 표 (Markdown) — 문서의 사실 계층에 그대로 사용
  flow.json  : (선택) flowgen.py 입력용 흐름도 스켈레톤 — LLM이 라벨/점선 보강 후 사용
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

SRC_EXT = (".tsx", ".ts", ".jsx", ".js", ".vue", ".html")

# 보안/가용성: 이 스크립트는 신뢰 못 할(적대적일 수 있는) 코드를 정규식으로 분석한다.
# 비정상적으로 거대한 단일 파일(예: 실수로 포함된 번들/난독화 파일, 혹은 의도적으로
# 심어진 파일)은 route/API 등 추출기의 백트래킹 가능한 정규식과 결합해 CPU를
# 과도하게 소모시킬 수 있다 — 상한을 넘는 파일은 분석에서 제외한다.
MAX_FILE_BYTES = 2_000_000

# 라우트 element를 감싸는 흔한 래퍼/HOC — 페이지 컴포넌트 판정 시 건너뛴다.
WRAPPER_COMPONENTS = {
    "RequireAuth", "ProtectedRoute", "PrivateRoute", "AuthGuard", "Suspense",
    "ErrorBoundary", "Layout", "AppLayout", "MainLayout", "Fragment",
}

SECRET_FILENAMES = {"secrets.json", "credentials.json", "id_rsa", "id_rsa.pub"}
SECRET_SUFFIXES = (".pem", ".key")
SECRET_KEY_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"AIza[0-9A-Za-z_\-]{35}", "Google API key"),
    (r"sk_(?:live|test)_[0-9a-zA-Z]{16,}", "Stripe secret key"),
    (r"gh[pousr]_[0-9A-Za-z]{20,}", "GitHub token"),
    (r"xox[baprs]-[0-9A-Za-z-]{10,}", "Slack token"),
]

# 서드파티 판정에서 제외할 프레임워크/유틸 (서비스 연동이 아닌 것)
FRAMEWORK_DEPS = {
    "react", "react-dom", "react-router", "react-router-dom", "vue", "vue-router",
    "next", "nuxt", "svelte", "typescript", "vite", "webpack", "axios", "lodash",
    "dayjs", "date-fns", "classnames", "clsx", "zod", "yup",
}
TRACKING_PATTERNS = [
    (r"\bgtag\(\s*['\"]event['\"]\s*,\s*['\"]([^'\"]+)['\"]", "gtag"),
    (r"\bga\(\s*['\"]send['\"]\s*,\s*['\"]([^'\"]+)['\"]", "ga"),
    (r"\bamplitude(?:\.getInstance\(\))?\.(?:track|logEvent)\(\s*['\"]([^'\"]+)['\"]", "amplitude"),
    (r"\bmixpanel\.track\(\s*['\"]([^'\"]+)['\"]", "mixpanel"),
    (r"\bdataLayer\.push\(\s*\{[^}]*event\s*:\s*['\"]([^'\"]+)['\"]", "dataLayer"),
    (r"\b(?:track|logEvent|trackEvent)\(\s*['\"]([^'\"]+)['\"]", "custom"),
]


_TRAILING_COMMENT = re.compile(r"\s//")
# `// POST /api/x` 형태의 의도적 API 문서화 표기는 유효 JS 문법이 아니라
# 순수 주석 표기이므로, 죽은 코드(진짜 문법)와 구분해 보존해야 한다.
# extract_api_calls의 전용 패턴이 이 표기를 찾는다.
_API_ANNOTATION = re.compile(r"^//\s*(?:GET|POST|PUT|PATCH|DELETE)\s+/\S+")


def _blank_full_line_comments(src: str) -> str:
    """실전 검증 교훈(reverse-backend 자매 스킬에서 먼저 발견 후 이식, 이후
    재점검 중 트레일링 주석 사각지대와 그로 인한 API 문서화 표기 유실을
    추가 발견): 주석 처리된 죽은 코드가 실제 정책/화면/API로 오탐되는 것을
    막되, 의도적인 API 주석 표기(`// POST /api/x`)는 보존한다.

    1. 한 줄 전체가 `//`로 시작하는 라인, 한 줄 안에서 완전히 닫히는
       HTML 주석(`<!-- ... -->`)은 통째로 비운다 — 단 `_API_ANNOTATION`
       형태는 예외로 보존한다.
    2. `코드; // 주석` 형태의 **트레일링 주석**도 잘라낸다 — 재점검 중
       `doRealThing(); // fetch("/api/fake") 예시` 같은 줄에서 주석 안의
       가짜 API 호출이 실제 fetch처럼 오탐되는 것을 발견해 추가했다.
       단, `//` 앞에 공백이 있을 때만 주석 시작으로 본다(URL 오손상 방지)
       이고, 트레일링 주석이 `_API_ANNOTATION` 형태면 역시 보존한다 —
       처음엔 이 예외 없이 구현해 mock-shop의 `await login(...); //
       POST /api/auth/login` 같은 의도된 문서화 주석까지 함께 지워지는
       회귀를 냈다가 재점검 중 발견해 수정했다.

    한계: 문자열 리터럴 안에 우연히 " //"가 포함되면(드묾) 그 지점에서 잘릴 수
    있고, JSX 블록 주석(`{/* ... */}`)과 여러 줄 블록 주석은 다루지 않는다
    — reference.md 1-I에 명시."""
    out = []
    for line in src.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            out.append(line if _API_ANNOTATION.match(stripped) else "")
            continue
        if stripped.startswith("<!--") and stripped.rstrip().endswith("-->"):
            out.append("")
            continue
        m = _TRAILING_COMMENT.search(line)
        if m and not _API_ANNOTATION.match(line[m.start() + 1:].lstrip()):
            out.append(line[:m.start()])
        else:
            out.append(line)
    return "\n".join(out)


def _is_within(root: pathlib.Path, p: pathlib.Path) -> bool:
    """p의 실제 경로(심볼릭 링크 해석 후)가 root 하위에 있는지 확인.
    보안 검증 발견: rglob/is_file은 심볼릭 링크를 따라가므로, root 하위처럼
    보이는 심링크로 root 밖 임의 파일을 읽을 수 있었다 — resolve()로 실제
    경로를 확인해 저장소 밖 파일 접근을 차단한다."""
    try:
        rp = root.resolve()
        rr = p.resolve()
        return rr == rp or rp in rr.parents
    except (OSError, RuntimeError):
        return False


def _walk_safe_files(root: pathlib.Path):
    """root 하위 파일을 순회하되 심볼릭 링크(파일/디렉토리)는 건너뛴다.
    보안: 심링크 추적으로 저장소 밖 파일을 읽는 것을 원천 차단."""
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            continue
        if not p.is_file():
            continue
        if not _is_within(root, p):
            continue
        yield p


def read_sources(root: pathlib.Path) -> dict:
    files = {}
    for p in _walk_safe_files(root):
        if any(part in ("node_modules", ".git", "dist", "build") for part in p.parts):
            continue
        if p.suffix in SRC_EXT or p.name == "package.json":
            try:
                if p.stat().st_size > MAX_FILE_BYTES:
                    print(f"⚠️  건너뜀(파일 크기 {p.stat().st_size:,}B > 상한): {p}",
                          file=sys.stderr)
                    continue
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if p.name != "package.json":
                text = _blank_full_line_comments(text)
            files[str(p.relative_to(root))] = text
    return files


# ── 1-A. 라우트 ──────────────────────────────────────────────

def _component_and_guard(elem_str: str) -> tuple:
    """JSX element 문자열에서 (페이지 컴포넌트명, 보호등급)을 파싱한다.
    보안 검증 발견: JSX <Route> 경로에는 createBrowserRouter 쪽에만 있던
    RequireAuth 가드 스트리핑이 빠져 있어, 가드로 감싼 라우트가 컴포넌트를
    'RequireAuth'로, 보호를 'public'으로 잘못 보고했다(정반대). 이 헬퍼로
    두 경로가 동일 로직을 공유하게 통합했다.
    또한 <RequireAuth><Layout><Page/></Layout> 처럼 래퍼가 겹칠 때 첫 태그가
    래퍼면 건너뛰고 실제 페이지 컴포넌트를 고른다(WRAPPER_COMPONENTS)."""
    guard = "public"
    m_role = re.search(r'<RequireAuth\s+role="([^"]+)"', elem_str)
    if m_role:
        guard = f"role:{m_role.group(1)}"
    elif "<RequireAuth" in elem_str:
        guard = "login"
    tags = re.findall(r"<([A-Za-z]\w*)\b", elem_str)
    page = next((t for t in tags if t not in WRAPPER_COMPONENTS), None)
    if page is None:
        page = tags[0] if tags else "?"
    return page, guard


def _basename_no_ext(path: str) -> str:
    base = path.rstrip("/").split("/")[-1]
    return base.split(".")[0] or path


_REGEX_PRECEDING_KEYWORDS = {
    "return", "throw", "yield", "case", "typeof", "instanceof",
    "in", "of", "new", "delete", "void", "do", "else",
}


def _looks_like_regex_start(src: str, idx: int) -> bool:
    """`/`가 나눗셈 연산자가 아니라 정규식 리터럴의 시작일 것 같으면 True.

    정확성 검증 발견 1차(PR 리뷰): `/don't/.test(value)`처럼 정규식 리터럴 안에
    아포스트로피가 있으면, 코드 맥락 따옴표 스캐너들이 이를 문자열 시작으로
    오인해 나머지 파일 끝까지 잘못 스캔했다 — `<`의 비교연산자/태그 모호성과
    같은 종류의 문제("/"가 나눗셈인지 정규식 시작인지도 문법적으로 모호함,
    실제 JS 토크나이저도 겪는 문제)라 `_looks_like_operator_lt`와 같은 해소
    규칙을 쓴다: 직전(공백 제외)이 식별자 문자나 닫는 괄호/대괄호/중괄호면
    "값이 방금 끝난 자리"라 `/`는 나눗셈, 아니면(여는 괄호/콤마/콜론/다른
    연산자/시작 위치) 표현식이 새로 시작하는 자리라 정규식 리터럴로 본다.

    정확성 검증 발견 2차(자체 재검토): `<Page label="{" />`의 자체닫힘 `/>`
    에서, `/` 직전(공백 제외)이 속성값의 닫는 따옴표 `"`였는데 이는 "값이
    방금 끝난 자리" 집합에 없어 정규식 시작으로 오판했다(§13.7 재발 증상) —
    따옴표로 끝난 뒤의 `/`는 실제 JS에서도 나눗셈/자체닫힘일 수밖에 없고
    (`"str"` 바로 뒤에 정규식이 올 문법은 없음) 정규식 시작일 수 없으므로,
    닫는 따옴표도 "값이 방금 끝난 자리"에 포함한다.

    정확성 검증 발견 3차(PR 리뷰): `return /don't/.test(value)`처럼 `/` 직전이
    `return`/`throw`/`case` 등 **키워드**로 끝나면, 그 키워드도 식별자 문자로
    끝나서 "값이 방금 끝난 자리"로 오판돼 나눗셈으로 잘못 판정했다 — 이런
    키워드 뒤는 항상 새 표현식이 시작하는 자리이지 값이 끝난 자리가 아니다.
    직전 단어가 이 키워드 목록에 있으면 식별자 문자로 끝나더라도 정규식
    시작으로 뒤집는다."""
    j = idx - 1
    while j >= 0 and src[j] in " \t\r\n":
        j -= 1
    if j >= 0 and (src[j].isalnum() or src[j] in "_$)]}'\"`"):
        if src[j].isalnum() or src[j] == "_" or src[j] == "$":
            k = j
            while k >= 0 and (src[k].isalnum() or src[k] in "_$"):
                k -= 1
            word = src[k + 1:j + 1]
            if word in _REGEX_PRECEDING_KEYWORDS:
                return True
        return False
    return True


def _skip_regex_literal(src: str, idx: int) -> int:
    """idx(정규식 리터럴 시작 `/`)부터, 대응하는 종료 `/`(문자 클래스 `[...]`
    안의 `/`는 리터럴로 무시, 백슬래시 이스케이프 존중) 다음에 오는 플래그
    문자(`g`, `i` 등)까지 건너뛴 위치를 반환한다. 개행을 만나거나 EOF까지
    닫는 `/`를 못 찾으면(정규식이 아니라 실제 나눗셈이었을 가능성) 보수적으로
    `idx + 1`만 건너뛴다."""
    n = len(src)
    j = idx + 1
    in_class = False
    while j < n:
        c = src[j]
        if c == "\\":
            j += 2
            continue
        if c == "\n":
            return idx + 1
        if c == "[":
            in_class = True
        elif c == "]":
            in_class = False
        elif c == "/" and not in_class:
            j += 1
            while j < n and src[j].isalpha():
                j += 1
            return j
        j += 1
    return idx + 1


def _looks_like_operator_lt(src: str, idx: int) -> bool:
    """`<`가 JSX 태그 시작이 아니라 `a < b`류 비교/제네릭 연산자로 쓰인 것 같으면
    True. 정확성 검증 발견(PR 리뷰, 4연속): `a <b && c > d ? <One/> : <Two/>`
    처럼 공백 없이 붙은 `<식별자`는 태그 시작과 문법적으로 구분이 안 돼(TS 컴파일러
    조차 겪는 유명한 모호성), 비교연산자를 태그로 오인해 그 `>`를 태그 종료로
    잘못 소비하면서 실제 구조적 `}`를 지나쳐 스캔이 깨졌다. 표준적인 해소 규칙과
    같은 방식으로: `<` 직전(공백 제외)이 식별자 문자나 닫는 괄호/대괄호/중괄호면
    "값이 방금 끝난 자리"이므로 다음에 오는 `<`는 십중팔구 연산자다 — 반대로
    `(`, `{`, `,`, `:`, `?`, 다른 연산자, 또는 시작 위치라면 "표현식이 새로 시작하는
    자리"라 `<`는 태그 시작으로 본다. (`element={...}`는 문(statement)이 아니라
    표현식만 오므로 `return <X/>`류로 식별자 뒤에 정당하게 태그가 오는 경우는
    이 스캐너의 실제 사용 범위에서는 나타나지 않는다.)

    보안 검증 발견(자체 재검토): 정규식 `search(src, 0, idx)`로 구현했다가,
    `<`가 자주 나오는 입력에서 매 호출마다 최악의 경우 idx에 비례해 훑을 수
    있어(앵커링에도 불구하고) 다시 이차식 비용을 재도입할 위험이 있었다 —
    정규식 대신 공백만 건너뛰는 짧은 역방향 문자 스캔으로 바꿔, 호출당 비용이
    직전 공백 런 길이에만 비례하도록(사실상 상수) 만들었다."""
    j = idx - 1
    while j >= 0 and src[j] in " \t\r\n":
        j -= 1
    return j >= 0 and (src[j].isalnum() or src[j] in "_$)]}")


_GENERIC_CONSTRAINT_KEYWORDS = ("extends",)


def _looks_like_generic_params(src: str, idx: int) -> bool:
    """`<`가 JSX 태그 시작이 아니라 TSX 제네릭 매개변수 목록(`<T,>(x: T) => x`
    같은, `.tsx`에서 JSX와 제네릭 화살표 함수를 구분하려고 일부러 트레일링
    콤마를 붙이는 관용구, 또는 `<T extends object>(x: T) => x` 같은 제약
    제네릭)일 것 같으면 True.

    정확성 검증 발견 1차(PR 리뷰): `fn={<T,>(x: T) => x}`에서 `<T,`는
    `_looks_like_operator_lt` 기준(직전이 `{`)으로는 "연산자 아님 = 태그"로
    판정돼, `<T,>`를 여는 태그로 오인하고 그 `>`를 태그 종료로 소비해 뒤따르는
    `(x: T) => x`가 JSX 텍스트로 잘못 처리됐다(§13.9와 같은 근본 문제의 또
    다른 얼굴 — `<`의 모호성은 비교연산자뿐 아니라 제네릭에도 있다). JSX 태그
    이름 뒤에는 콤마가 바로 오는 경우가 없으므로(그러면 문법 오류), 식별자 뒤
    (공백 허용) 첫 문자가 콤마면 제네릭으로 본다.
    정확성 검증 발견 2차(PR 리뷰): `<T extends object>`처럼 제약이 있는
    제네릭은 콤마 없이 `extends` 키워드로 이어져 1차 수정을 통과하지 못했다
    — 식별자 뒤에 `extends` 키워드(단어 경계 확인)가 오는 경우도 같이 본다.
    정확성 검증 발견 3차(PR 리뷰): `<T = unknown>`처럼 기본값이 있는 제네릭은
    콤마도 `extends`도 없이 `=`로 이어져 앞선 두 수정 다 통과하지 못했다 —
    식별자 뒤에 (다음 문자가 `=`나 `>`가 아닌, 즉 `==`/`===`/`=>`가 아닌)
    단독 `=`가 오는 경우도 같이 본다."""
    j = idx + 1
    while j < len(src) and (src[j].isalnum() or src[j] in "_$"):
        j += 1
    k = j
    while k < len(src) and src[k] in " \t\r\n":
        k += 1
    if k < len(src) and src[k] == ",":
        return True
    if k < len(src) and src[k] == "=" and src[k + 1:k + 2] not in ("=", ">"):
        return True
    for kw in _GENERIC_CONSTRAINT_KEYWORDS:
        end = k + len(kw)
        if src[k:end] == kw and (end >= len(src) or not (src[end].isalnum() or src[end] in "_$")):
            return True
    return False


def _find_matching_skip_strings(src: str, open_idx: int, open_ch: str, close_ch: str) -> int:
    """`_find_matching`과 같되, "JSX 텍스트"와 "코드"(태그 속성/표현식) 맥락을
    구분해 코드 맥락의 문자열 리터럴 안 여는/닫는 문자는 깊이 계산에서
    제외한다.

    이 함수는 세 차례에 걸친 PR 리뷰 재검증에서 좁은 휴리스틱을 하나씩 늘려가며
    번번이 반대쪽 사례에서 다시 터졌다:
      1차: 순수 괄호 카운팅 → JSX 속성값 안 리터럴 `{`(`label="{"`)에 걸려
           닫는 `}`를 못 찾음.
      2차: "따옴표는 무조건 문자열" → JSX **텍스트** 안 아포스트로피
           (`Don't stop`)까지 문자열 시작으로 오인.
      3차: "`=` 뒤에 오는 따옴표만 문자열" → `attr={cond ? "{" : "x"}`처럼
           `=` 없이 표현식 안에 오는 문자열(삼항 분기 등)을 놓침.
    세 사례 모두 "따옴표가 코드 맥락(태그 속성 목록/표현식 내부)에 있는지, JSX
    텍스트 맥락에 있는지"를 구분하지 못한 게 근본 원인이었다 — 위치(직전 문자가
    `=`인지)가 아니라 **맥락**이 기준이어야 한다. 그래서 이번엔 `<Tag ...>`
    (코드: 속성 목록, 따옴표=문자열) ↔ JSX 자식 텍스트(따옴표=그냥 글자) 전환을
    실제로 추적하는 작은 상태기계로 다시 짰다:

    - `mode`: "code"(따옴표/백틱=문자열 구분자) 또는 "text"(따옴표는 글자).
      시작은 "code"(`element={` 바로 다음이 표현식이므로).
    - `{`/`}`: 어느 모드에서든 항상 깊이로 세고(JSX 규격상 이스케이프 없는
      `{`는 텍스트에서도 언제나 표현식 시작), `{`를 열 때 현재 mode를 스택에
      저장했다가 대응하는 `}`에서 복원한다 — 이게 바로 목표 깊이(0)를 찾는
      기준이다.
    - `<식별자` 또는 `</`: 태그 시작 — 그 태그 자신의 종료 `>`를 찾을 때까지
      (같은 깊이에서) mode를 "code"로 둬 속성 목록을 정상 처리한다. 종료 `>`를
      만나면: 닫는 태그면 `text_stack`을 복원(부모 텍스트로 복귀), 자체 닫힘
      (`/>`)이면 태그 시작 전 mode로 복귀, 여는 태그(자식 있음)면 "text"로
      전환하고 복귀용 mode를 `text_stack`에 쌓아둔다.
    - 그 외 문자는 현재 mode에서 그대로 지나간다(코드 맥락 문자열/백틱만
      건너뛰고, 텍스트 맥락에서는 아무 글자나 그냥 텍스트).

    여전히 문자 스캔 기반 근사치라 정규식 리터럴, JS 비교연산자 `<`/`>`가
    표현식 안에서 오탐될 가능성 등 더 복잡한 경우까지 완벽히 다루진 않는다 —
    reference.md 1-I의 알려진 한계와 같은 성격이지만, 실제 라우트 JSX에서
    나올 법한 "속성값 문자열 vs 텍스트 vs 표현식 안 문자열"은 모두 다룬다.
    여전히 단일 좌→우 패스(문자당 O(1) 상태)라 이차식 비용 문제는 재발하지
    않는다."""
    depth, mode, i, n = 0, "code", open_idx, len(src)
    brace_modes: list = []   # `{`를 열 때 mode를 저장, 대응 `}`에서 복원
    text_stack: list = []    # 여는 태그가 "text"로 들어갈 때 복귀용 mode를 저장
    pending_tags: list = []  # [(태그 시작 시점의 depth, 닫는태그 여부, 시작 전 mode), ...]

    def _skip_delimited(j: int, delim: str) -> int:
        """j(따옴표/백틱 다음)부터 이스케이프를 존중하며 delim과 같은 문자를 찾는다."""
        while j < n and src[j] != delim:
            j += 2 if src[j] == "\\" else 1
        return j + 1  # 닫는 문자 다음(또는 EOF) 위치

    while i < n:
        ch = src[i]

        # 정확성 검증 발견(PR 리뷰): `<Page /> /* don't */`처럼 코드 맥락의
        # 블록 주석 안에 아포스트로피가 있으면, 주석을 인식 못 하고 그 안의
        # 따옴표를 문자열 시작으로 오인해 §13.7과 같은 증상(스캔이 EOF까지
        # 튀어 -1 반환)이 재발했다 — `_blank_full_line_comments`는 줄 전체
        # `//` 주석만 지우고 블록 주석은 reference.md 1-I에 명시된 대로 원래
        # 처리 대상이 아니었다. 코드 맥락에서 `/*`를 보면 대응하는 `*/`까지
        # (없으면 파일 끝까지) 통째로 건너뛴다.
        if mode == "code" and ch == "/" and i + 1 < n and src[i + 1] == "*":
            end = src.find("*/", i + 2)
            i = end + 2 if end != -1 else n
            continue

        # 정확성 검증 발견(PR 리뷰): `_blank_full_line_comments`는 `//` 앞에
        # 공백이 있을 때만 트레일링 주석으로 본다(URL 오손상 방지 목적) —
        # `const x=1;// don't`처럼 공백 없이 바로 붙은 `//` 주석은 지워지지
        # 않고 그대로 남아 안의 아포스트로피가 문자열 시작으로 오인됐다.
        # 개행까지(없으면 파일 끝까지) 건너뛴다.
        if mode == "code" and ch == "/" and i + 1 < n and src[i + 1] == "/":
            nl = src.find("\n", i + 2)
            i = nl + 1 if nl != -1 else n
            continue

        # 정확성 검증 발견(PR 리뷰): `/don't/.test(value)`처럼 정규식 리터럴
        # 안의 아포스트로피도 문자열 시작으로 오인해 같은 증상이 재발했다 —
        # 나눗셈과 정규식 리터럴 시작은 문법적으로 모호하므로(`<`와 같은
        # 종류의 문제) `_looks_like_regex_start`로 판정 후 건너뛴다.
        if (mode == "code" and ch == "/" and i + 1 < n and src[i + 1] != "/"
                and _looks_like_regex_start(src, i)):
            i = _skip_regex_literal(src, i)
            continue

        if mode == "code" and ch in ("'", '"', "`"):
            i = _skip_delimited(i + 1, ch)
            continue

        if ch == open_ch:
            brace_modes.append(mode)
            mode = "code"
            depth += 1
            i += 1
            continue

        if ch == close_ch:
            if mode == "code":
                depth -= 1
                mode = brace_modes.pop() if brace_modes else "code"
                if depth == 0:
                    return i
            i += 1
            continue

        # 정확성 검증 발견(PR 리뷰): JSX 프래그먼트 단축 문법 `<>...</>` 의 여는
        # `<>`는 다음 문자가 식별자도 `/`도 아니라(바로 `>`) 아래의 일반 태그
        # 감지 조건에 안 걸려, 내용이 계속 이전 mode(대개 "code")에 남아 그 안의
        # 아포스트로피 등을 문자열 시작으로 오인했다(§13.7과 같은 증상 재발).
        # 프래그먼트는 속성이 없어 속성 목록 스캔이 필요 없으므로, 만나는 즉시
        # "text"로 전환한다. (닫는 `</>`는 `/`로 시작하므로 아래 일반 태그 감지
        # 조건에서 이미 정상 처리된다.)
        if ch == "<" and i + 1 < n and src[i + 1] == ">":
            text_stack.append(mode)
            mode = "text"
            i += 2
            continue

        # `<`가 비교연산자/TSX 제네릭으로 오인될 수 있는 모호성은 "code" 맥락
        # (표현식 안)에서만 존재한다 — "text" 맥락(JSX 자식)에서는 `<` 뒤에
        # 문자/`/`가 오면 항상 자식 태그이거나 닫는 태그이므로 무조건 태그
        # 시작으로 본다. (자체 재검토 발견: 처음엔 맥락 구분 없이 비교연산자
        # 검사를 걸었다가 `<div>Don't stop</div>`의 `</div>`가 "stop"(식별자
        # 문자) 뒤에 온다는 이유로 태그가 아니라고 오판해 §13.7 회귀가
        # 재발했었다.)
        if (ch == "<" and i + 1 < n and (src[i + 1].isalpha() or src[i + 1] == "/")
                and not (mode == "code" and (_looks_like_operator_lt(src, i)
                                              or _looks_like_generic_params(src, i)))):
            is_closing = src[i + 1] == "/"
            pending_tags.append((depth, is_closing, mode))
            mode = "code"
            # 정확성 검증 발견(자체 재검토): 닫는 태그의 `/`(예: `</div>`)까지만
            # 건너뛰고 그 `/` 자체는 다음 반복에서 별도 문자로 다시 보면,
            # 방금 code 맥락으로 전환된 데다 직전 문자가 `<`(식별자/닫는 괄호가
            # 아님)라 `_looks_like_regex_start`가 이를 정규식 리터럴 시작으로
            # 오판했다(`<div>Don't stop</div>`가 다시 §13.7처럼 깨짐) — `<`와
            # `/`를 한 번에 건너뛰어 그 `/`가 별도 문자로 재검사되지 않게 한다.
            i += 2 if is_closing else 1
            continue

        if mode == "code" and ch == ">" and pending_tags and pending_tags[-1][0] == depth:
            _, is_closing, mode_before = pending_tags.pop()
            self_closing = i > 0 and src[i - 1] == "/"
            if is_closing:
                mode = text_stack.pop() if text_stack else "code"
            elif self_closing:
                mode = mode_before
            else:
                text_stack.append(mode_before)
                mode = "text"
            i += 1
            continue

        i += 1
    return -1


def _iter_jsx_route_blocks(src: str):
    """`<Route path="..." element={ ... }>` 블록을 파일을 단 한 번만 좌→우로
    순회하며 찾는다.

    보안 검증 발견(PR 리뷰, 재재검토): "각 발견마다 독립적으로 재스캔하되 길이를
    4000자로 제한"한 이전 수정은, `<Route path="x" element={` 접두어가 아주
    많이 반복되는 입력에서 "발견 횟수 × 4000자 상한"만큼 비용이 누적돼 여전히
    나쁘게 확장됐다(2MB 근처 입력에서 3초+, 그런 파일 100개면 누적 수 분).
    대신 파일 전체를 한 번만 훑으며 각 발견 지점에서 `_find_matching_skip_strings`
    (괄호 깊이 카운팅 + 문자열 리터럴 건너뛰기)로 대응하는 `}`를 찾고,
    다음 탐색은 그 지점부터 이어간다 — 이미 훑은 구간을 다시 스캔하지 않으므로
    닫는 `}`가 정상적으로 존재하는 한 총 비용은 파일 길이에 선형이다.
    닫는 `}`를 못 찾으면(적대적으로 깨진 JSX) 그 지점에서 더 찾지 않고 전체
    탐색을 종료한다 — 재시도하며 반복 스캔하지 않으므로, 안 닫히는 접두어가
    아무리 많이 반복돼도 전체 비용은 파일을 한 번 훑는 것으로 고정된다.
    (실제 동작하는 코드는 문법상 괄호가 항상 맞으므로, 이 조기 종료 경로는
    적대적이거나 손상된 입력에서만 타고, 정상 파일의 라우트 추출에는 영향이
    없다.)"""
    pat = re.compile(r'<Route\s+path="([^"]+)"\s+element=\{')
    pos, n = 0, len(src)
    while pos < n:
        m = pat.search(src, pos)
        if not m:
            return
        open_idx = m.end() - 1  # '{' 위치
        close_idx = _find_matching_skip_strings(src, open_idx, "{", "}")
        if close_idx == -1:
            return
        yield m.group(1), src[open_idx + 1:close_idx]
        pos = close_idx + 1


def extract_routes(files: dict) -> list:
    routes = []
    for fname, src in files.items():
        if "createBrowserRouter" in src or "createHashRouter" in src:
            for block in re.split(r"\},\s*\{", src):
                m_path = re.search(r'path:\s*"([^"]+)"', block)
                if not m_path:
                    continue
                component, guard = _component_and_guard(block)
                routes.append({"path": m_path.group(1), "component": component,
                               "guard": guard, "source": fname})
        # React Router JSX: element={ ... } 전체를 캡처해 가드/컴포넌트 파싱.
        for path, element_src in _iter_jsx_route_blocks(src):
            component, guard = _component_and_guard(element_src)
            routes.append({"path": path, "component": component,
                           "guard": guard, "source": fname})
        # Vue Router: path와 component 사이에 meta:{...} 등 중첩 객체가 있어도
        # 매칭되도록, 그리고 lazy-load(() => import("..."))도 잡도록 개선.
        if "vue-router" in src or "createRouter" in src:
            for m in re.finditer(
                    r"path:\s*['\"]([^'\"]+)['\"][\s\S]{0,300}?component:\s*"
                    r"(?:\(\)\s*=>\s*import\(\s*['\"]([^'\"]+)['\"]|(\w+))", src):
                if m.group(3):
                    component = m.group(3)
                else:
                    component = _basename_no_ext(m.group(2))
                routes.append({"path": m.group(1), "component": component,
                               "guard": "public", "source": fname})
    uniq = {(r["path"], r["source"]): r for r in routes}
    return sorted(uniq.values(), key=lambda r: (r["path"], r["source"]))


# ── 1-B. 컴포넌트 ────────────────────────────────────────────

def extract_components(files: dict) -> list:
    """컴포넌트(PascalCase)의 정의/참조를 수집한다. 정확성 검증 발견: 이전에는
    default export/import만 인식해 `export const Foo = () => ...`,
    `export function Foo()` 같은 named-export 컴포넌트와 `import { Foo }` 같은
    named import가 표에 아예 나타나지 않았다 — named 형태도 함께 인식한다.
    (소문자 시작 이름은 유틸/훅으로 보고 제외해 노이즈를 줄인다.)"""
    defined, referenced = {}, set()
    for fname, src in files.items():
        # default export
        for m in re.finditer(r"export\s+default\s+function\s+([A-Z]\w*)", src):
            defined[m.group(1)] = fname
        for m in re.finditer(r"export\s+default\s+([A-Z]\w*)\s*;", src):
            defined.setdefault(m.group(1), fname)
        # named export: export const/function/class Foo (PascalCase만)
        for m in re.finditer(r"export\s+(?:const|let|var|function|class)\s+([A-Z]\w*)", src):
            defined.setdefault(m.group(1), fname)
        # default import: import Foo from './...'
        for m in re.finditer(r'import\s+([A-Z]\w*)\s+from\s+["\']\.{1,2}/', src):
            referenced.add(m.group(1))
        # named import: import { Foo, Bar } from './...' (상대경로 한정)
        for m in re.finditer(r'import\s+\{([^}]+)\}\s+from\s+["\']\.{1,2}/', src):
            for name in m.group(1).split(","):
                name = name.split(" as ")[0].strip()
                if re.match(r"^[A-Z]\w*$", name):
                    referenced.add(name)
    rows = []
    for name in sorted(referenced | set(defined)):
        rows.append({"name": name, "source": defined.get(name, ""),
                     "analyzed": name in defined})
    return rows


# ── 1-C. API / 상수 / 검증·차단 규칙 ─────────────────────────


_FETCH_START = re.compile(r'fetch\(\s*[\'"`]([^\'"`]+)[\'"`]')


def _iter_fetch_calls(src: str):
    """`fetch(...)` 호출(중첩 포함)을 파일을 단 한 번만 좌→우로 순회하며 찾는다.

    3단계에 걸친 재검토 끝에 나온 설계다:
    1차: 각 `fetch("x"` 발견마다 독립적으로 `_find_matching_paren`을 불러
         닫는 `)`를 찾았는데, 닫히지 않는 접두어가 반복되면 매 발견마다
         나머지 파일 끝까지 스캔해 이차식으로 느려졌다(20KB만으로 1초+).
    2차: "발견마다 이미 지나온 구간은 다시 스캔하지 않고, 못 찾으면 전체
         탐색 종료"로 바꿔 위 문제는 해결했지만, 두 가지를 놓쳤다 — (a) 인자
         문자열 안의 짝 안 맞는 괄호(예: JSON 바디 `"("`)가 있으면 정말
         못 찾은 것처럼 보여 그 뒤의 멀쩡한 호출까지 전부 사라졌고, (b) 바깥
         호출의 닫는 `)` 다음으로 건너뛰다 보니 `fetch("/outer", {x: fetch("/inner")})`
         처럼 인자 **안에 중첩된** fetch 호출은 통째로 지나쳐 아예 못 찾았다.
         (b)를 "바깥을 찾은 뒤 그 인자 범위 안을 다시 검색"으로 고치면, 깊이
         중첩된 입력(`fetch(fetch(fetch(...)))`)에서 바깥쪽일수록 매번 남은
         전체를 다시 훑어 또 이차식(중첩 깊이 기준)이 될 위험이 있었다.
    3차(현재): `fetch(` 발견 지점 전체를 먼저 한 번의 `finditer`로 모아두고,
         파일을 정말 **한 번만** 좌→우로 훑으며 괄호 깊이를 추적한다 — 그
         발견 지점의 `(`을 지날 때 (그 시점의 깊이, 끝점 문자열)을 스택에
         쌓고, 어떤 `)`에서 깊이가 스택 맨 위가 열렸던 깊이로 돌아오면 그
         호출이 완결된 것으로 보아 즉시 내보낸다. 문자열/템플릿 리터럴 안의
         괄호는 깊이에서 제외한다. 각 문자를 정확히 한 번씩만 방문하므로
         중첩 개수·깊이와 무관하게 전체 비용은 파일 길이에 선형이고, 특정
         호출 하나가 안 닫혀도(스택에 그대로 남을 뿐) 다른 호출 탐색을 막지
         않는다 — 2차의 "하나가 이상하면 나머지 다 못 찾음" 취약점도 함께
         해소된다."""
    starts = {m.start() + 5: m.group(1) for m in _FETCH_START.finditer(src)}  # '(' 위치 -> endpoint
    if not starts:
        return
    # 정확성 검증 발견(PR 리뷰): 템플릿 리터럴을 백틱째로 통째 건너뛰는
    # (`${...}` 보간을 코드가 아니라 그냥 문자열 내용으로 취급하는) 방식은,
    # `` `resp: ${fetch("/inner")}` `` 처럼 보간 **안에** 있는 fetch 호출을
    # 아예 못 봤다 — `$`+`{` 를 만나면 보간이 끝나는 대응 `}`까지는 다시 code
    # 맥락(괄호/따옴표 정상 추적)으로 들어가야 한다. `{`/`}`는 라우트
    # 스캐너와 같은 스택 방식(여는 시점의 mode를 저장했다가 닫는 시점에
    # 복원)으로 다뤄, 보간 안의 일반 객체 리터럴 `{}`과도 구분한다.
    stack: list = []         # [(그 호출의 '('을 지날 때의 깊이, endpoint, '(' 위치), ...]
    brace_modes: list = []   # `{`를 열 때 mode를 저장, 대응 `}`에서 복원 (템플릿 보간용)
    mode = "code"            # "code" | "template"
    depth, i, n = 0, 0, len(src)
    while i < n:
        ch = src[i]

        # 정확성 검증 발견(PR 리뷰): 라우트 스캐너의 §13.13과 같은 문제가
        # fetch 스캐너에도 있었다 — `/* don't */`처럼 code 맥락의 블록 주석
        # 안에 아포스트로피가 있으면 문자열 시작으로 오인해 그 뒤의 정상
        # fetch 호출까지 못 봤다. 대응하는 `*/`까지(없으면 파일 끝까지) 건너뛴다.
        if mode == "code" and ch == "/" and i + 1 < n and src[i + 1] == "*":
            end = src.find("*/", i + 2)
            i = end + 2 if end != -1 else n
            continue

        # 정확성 검증 발견(PR 리뷰): `const x=1;// don't`처럼 `//` 앞에 공백이
        # 없으면 `_blank_full_line_comments`가 지우지 않는다(URL 오손상 방지
        # 목적으로 공백이 있을 때만 트레일링 주석으로 인식) — 안의 아포스트로피가
        # 문자열 시작으로 오인되지 않도록 개행까지 건너뛴다.
        if mode == "code" and ch == "/" and i + 1 < n and src[i + 1] == "/":
            nl = src.find("\n", i + 2)
            i = nl + 1 if nl != -1 else n
            continue

        # 정확성 검증 발견(PR 리뷰): `/don't/.test(value); fetch("/real")`처럼
        # 정규식 리터럴 안의 아포스트로피도 문자열 시작으로 오인해 그 뒤의
        # 정상 fetch 호출을 놓쳤다 — 나눗셈과 정규식 리터럴 시작은 문법적으로
        # 모호하므로 `_looks_like_regex_start`로 판정 후 건너뛴다.
        if (mode == "code" and ch == "/" and i + 1 < n and src[i + 1] != "/"
                and _looks_like_regex_start(src, i)):
            i = _skip_regex_literal(src, i)
            continue

        if mode == "code" and ch in ("'", '"'):
            q = ch
            j = i + 1
            while j < n and src[j] != q:
                j += 2 if src[j] == "\\" else 1
            i = j + 1
            continue

        if mode == "code" and ch == "`":
            mode = "template"
            i += 1
            continue

        if mode == "template":
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                mode = "code"  # 백틱 문자열은 항상 code 모드에서 시작하므로 닫히면 code로
                i += 1
                continue
            if ch == "$" and i + 1 < n and src[i + 1] == "{":
                brace_modes.append("template")
                mode = "code"
                i += 2
                continue
            i += 1
            continue

        if ch == "{":
            brace_modes.append("code")
            i += 1
            continue
        if ch == "}":
            mode = brace_modes.pop() if brace_modes else "code"
            i += 1
            continue
        if ch == "(":
            depth += 1
            if i in starts:
                stack.append((depth, starts[i], i))
            i += 1
            continue
        if ch == ")":
            if stack and stack[-1][0] == depth:
                _, endpoint, paren_idx = stack.pop()
                yield endpoint, src[paren_idx:i + 1]
            depth -= 1
            i += 1
            continue
        i += 1


def extract_api_calls(files: dict) -> list:
    calls = []
    for fname, src in files.items():
        for endpoint, call_text in _iter_fetch_calls(src):
            method = "GET"
            m_method = re.search(r'method:\s*[\'"](\w+)[\'"]', call_text)
            if m_method:
                method = m_method.group(1)
            calls.append({"endpoint": endpoint, "method": method, "source": fname})
        # axios.get(...) 직접 호출 + `const api = axios.create(); api.get("/x")` 처럼
        # 인스턴스를 통한 호출(정확성 검증 발견 — baseURL/인터셉터 설정 시 표준 패턴)도
        # 첫 인자가 경로/URL 문자열인 .메서드( 호출로 포착한다.
        for m in re.finditer(r"\baxios\.(get|post|put|patch|delete)\(\s*[\'\"`]([^\'\"`]+)", src):
            calls.append({"endpoint": m.group(2), "method": m.group(1).upper(), "source": fname})
        for m in re.finditer(
                r"\b\w+\.(get|post|put|patch|delete)\(\s*[\'\"`]"
                r"(/[^\'\"`]*|https?://[^\'\"`]+)", src):
            calls.append({"endpoint": m.group(2), "method": m.group(1).upper(),
                          "source": fname})
        for m in re.finditer(r"//\s*(GET|POST|PUT|PATCH|DELETE)\s+(/\S+)", src):
            calls.append({"endpoint": m.group(2), "method": m.group(1),
                          "source": fname + " (주석)"})
    uniq = {(c["endpoint"], c["method"]): c for c in calls}
    return sorted(uniq.values(), key=lambda c: (c["endpoint"], c["method"], c["source"]))


def extract_constants(files: dict) -> list:
    consts = []
    for fname, src in files.items():
        # 음수 상수도 포함 (정확성 검증 발견: -?가 없어 음수는 매칭 자체가 실패했음)
        for m in re.finditer(r"const\s+([A-Z][A-Z0-9_]+)\s*=\s*(-?[\d_.]+)", src):
            consts.append({"name": m.group(1), "value": m.group(2), "source": fname})
    return sorted(consts, key=lambda c: (c["name"], c["source"]))


_IF_PAREN = re.compile(r"if\s*\(")


def _find_if_return_pairs(src: str) -> list:
    """`if (조건) return "메시지"` 패턴을 중첩 괄호까지 고려해 찾는다.
    extract_rules와 extract_messages가 공유하는 헬퍼(중복 로직 통합).

    정확성 검증 발견 후 개선:
    - 중괄호 블록형 early-return `if (cond) { return "msg" }` 지원
      (Prettier/ESLint curly 규칙상 오히려 주류 스타일인데 누락되고 있었음).
    - 단따옴표/템플릿 리터럴 return 문자열도 지원(이전엔 큰따옴표만).

    보안 검증 발견(PR 리뷰): 각 `if (` 발견마다 독립적으로 `_find_matching_paren`
    을 불러 닫는 `)`를 찾았는데, fetch 스캐너가 §13.10~13.12에서 겪은 것과
    같은 근본 원인이다 — 닫히지 않는 `if (` 접두어가 반복되면 매 발견마다
    나머지 파일 끝까지 스캔해 이차식으로 느려졌다(32KB만으로 7초+). `if (`
    발견 지점을 먼저 한 번의 `finditer`로 모아두고, 파일을 한 번만 훑으며
    괄호 깊이를 스택으로 추적하는 §13.12의 fetch 스캐너와 같은 설계로
    교체했다 — `if (cond1) { if (cond2) {...} }`처럼 조건 문자열 안에
    다른 if가 텍스트로 등장하는 경우(예: 함수 인자 콜백 안)에도 안쪽 것을
    놓치지 않는다. 문자열/템플릿 리터럴 안의 괄호도 깊이에서 제외한다
    (조건 안에 `)`를 포함한 문자열 리터럴이 있어도 깨지지 않도록)."""
    starts = {src.index("(", m.start()) for m in _IF_PAREN.finditer(src)}
    if not starts:
        return []
    pairs = []
    stack: list = []  # [(그 if의 '('을 지날 때의 깊이, '(' 위치), ...]
    depth, quote, i, n = 0, None, 0, len(src)
    while i < n:
        ch = src[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        # 정확성 검증 발견(PR 리뷰): 라우트/fetch 스캐너와 같은 문제 —
        # `/* don't */ if (x) return "bad"`처럼 조건 앞뒤 블록 주석 안의
        # 아포스트로피를 문자열 시작으로 오인하면 이 if 전체를 못 찾았다.
        if ch == "/" and i + 1 < n and src[i + 1] == "*":
            end = src.find("*/", i + 2)
            i = end + 2 if end != -1 else n
            continue
        # `//`는 공백 없이 붙으면 `_blank_full_line_comments`가 안 지운다 —
        # 마찬가지로 개행까지 건너뛴다.
        if ch == "/" and i + 1 < n and src[i + 1] == "/":
            nl = src.find("\n", i + 2)
            i = nl + 1 if nl != -1 else n
            continue
        # `/don't/.test(x)`류 정규식 리터럴 안의 아포스트로피도 같은 이유로
        # 문자열 시작으로 오인될 수 있어 마찬가지로 건너뛴다.
        if (ch == "/" and i + 1 < n and src[i + 1] != "/"
                and _looks_like_regex_start(src, i)):
            i = _skip_regex_literal(src, i)
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            i += 1
            continue
        if ch == "(":
            depth += 1
            if i in starts:
                stack.append((depth, i))
            i += 1
            continue
        if ch == ")":
            if stack and stack[-1][0] == depth:
                _, paren_idx = stack.pop()
                condition = src[paren_idx + 1:i].strip()
                # `)` 다음에 (선택적 `{` 블록 후) return "…"/'…'/`…` 이 오는지 확인
                m2 = re.match(r'\s*\{?\s*return\s+(["\'`])(.*?)\1',
                              src[i + 1:i + 400], re.S)
                if condition and m2:
                    pairs.append((condition, m2.group(2).strip()))
            depth -= 1
            i += 1
            continue
        i += 1
    return pairs


_DISABLED_BRACE = re.compile(r"disabled=\{")


def _iter_disabled_conditions(src: str):
    """`disabled={...}` 안의 조건식(중첩 중괄호/화살표 블록/객체 포함)을
    파일을 단 한 번만 좌→우로 순회하며 찾는다.

    보안 검증 발견(PR 리뷰): 이 함수 역시 각 `disabled={` 발견마다 독립적으로
    `_find_matching`을 불러 닫는 `}`를 찾는, 이 PR에서 다섯 번째로 드러난
    같은 근본 원인이었다 — 닫히지 않는 `disabled={` 접두어가 반복되면 매
    발견마다 나머지 파일 끝까지 스캔해 이차식으로 느려졌다(16KB만으로 1초
    가까이). 처음부터 fetch/if-return 스캐너와 같은 설계(발견 지점을 모아
    두고 단일 패스로 깊이를 스택 추적)로, 그리고 이번 라운드에서 드러난
    문자열·블록 주석·줄 주석·정규식 리터럴 인식까지 전부 포함해서 짰다 —
    같은 종류의 재발을 다시 기다리지 않기 위함이다."""
    starts = {m.start() + len("disabled=") for m in _DISABLED_BRACE.finditer(src)}
    if not starts:
        return
    stack: list = []
    depth, quote, i, n = 0, None, 0, len(src)
    while i < n:
        ch = src[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch == "/" and i + 1 < n and src[i + 1] == "*":
            end = src.find("*/", i + 2)
            i = end + 2 if end != -1 else n
            continue
        if ch == "/" and i + 1 < n and src[i + 1] == "/":
            nl = src.find("\n", i + 2)
            i = nl + 1 if nl != -1 else n
            continue
        if (ch == "/" and i + 1 < n and src[i + 1] != "/"
                and _looks_like_regex_start(src, i)):
            i = _skip_regex_literal(src, i)
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
            if i in starts:
                stack.append((depth, i))
            i += 1
            continue
        if ch == "}":
            if stack and stack[-1][0] == depth:
                _, open_idx = stack.pop()
                yield src[open_idx + 1:i].strip()
            depth -= 1
            i += 1
            continue
        i += 1


def extract_rules(files: dict) -> list:
    rules = []
    for fname, src in files.items():
        for condition, message in _find_if_return_pairs(src):
            rules.append({"kind": "입력 검증", "condition": condition,
                          "effect": f'메시지 "{message}"', "source": fname})
        # min/max는 순서·인접에 무관하게(사이에 다른 속성 허용, 역순 허용) 잡는다.
        # 보안 검증 발견(PR 리뷰): 무경계 lazy `[^>]*?`는, `>`도 뒤따르는 `max=`도
        # 없이 `min={x}`가 반복되는 입력에서 매 발견마다 나머지 파일 끝까지
        # 훑어 이차식으로 느려졌다(112KB만으로 10초 가까이). 두 속성은 실제로
        # 같은 태그의 인접 속성이라 몇십 자 이내가 보통이므로 300자로 상한을
        # 둬 매 시도 비용을 상수로 고정한다.
        for m in re.finditer(r"min=\{(\w+)\}[^>]{0,300}?max=\{([\w.]+)\}", src):
            rules.append({"kind": "범위 제한", "condition": f"min {m.group(1)} / max {m.group(2)}",
                          "effect": "입력값 범위 강제", "source": fname})
        for m in re.finditer(r"max=\{([\w.]+)\}[^>]{0,300}?min=\{(\w+)\}", src):
            rules.append({"kind": "범위 제한", "condition": f"min {m.group(2)} / max {m.group(1)}",
                          "effect": "입력값 범위 강제", "source": fname})
        # disabled={...} 의 조건은 중첩 중괄호(화살표 블록/객체)까지 포함해 잡는다
        for cond in _iter_disabled_conditions(src):
            rules.append({"kind": "동작 차단", "condition": cond,
                          "effect": "버튼 비활성화", "source": fname})
        for m in re.finditer(r'if\s*\(!?(\w+)\)\s*\{\s*alert\("([^"]+)"\)', src):
            rules.append({"kind": "필수값", "condition": f"{m.group(1)} 조건 불충족",
                          "effect": f'알림 "{m.group(2)}" 후 중단', "source": fname})
    uniq = {(r["kind"], r["condition"], r["effect"], r["source"]): r for r in rules}
    return sorted(uniq.values(), key=lambda r: (r["kind"], r["condition"], r["source"]))


# ── 1-D. 화면 전환 ───────────────────────────────────────────

def extract_transitions(files: dict) -> list:
    trans = []
    for fname, src in files.items():
        for m in re.finditer(r'navigate\(\s*["\']([^"\']+)["\']', src):
            trans.append({"target": m.group(1), "via": "navigate()", "source": fname})
        for m in re.finditer(r'router\.push\(\s*["\']([^"\']+)["\']', src):
            trans.append({"target": m.group(1), "via": "router.push()", "source": fname})
        for m in re.finditer(r'<Navigate\s+to="([^"]+)"', src):
            trans.append({"target": m.group(1), "via": "<Navigate>", "source": fname})
        for m in re.finditer(r'window\.location(?:\.href)?\s*=\s*["\']([^"\']+)["\']', src):
            trans.append({"target": m.group(1), "via": "window.location", "source": fname})
    uniq = {(t["target"], t["source"], t["via"]): t for t in trans}
    return sorted(uniq.values(), key=lambda t: (t["source"], t["target"], t["via"]))


# ── 1-E. 사용자 노출 문구 ────────────────────────────────────

def extract_messages(files: dict) -> list:
    msgs = []

    def add(text, kind, cond, fname):
        text = text.strip()
        if len(text) >= 2:
            msgs.append({"text": text, "kind": kind, "cond": cond, "source": fname})

    for fname, src in files.items():
        if fname == "package.json":
            continue
        for m in re.finditer(r'\balert\(\s*"([^"]+)"\s*\)', src):
            add(m.group(1), "확인(alert)", "코드 분기", fname)
        for condition, message in _find_if_return_pairs(src):
            add(message, "에러", condition, fname)
        for m in re.finditer(r'setError\(\s*"([^"]+)"\s*\)', src):
            add(m.group(1), "에러", "코드 분기", fname)
        for m in re.finditer(r'placeholder="([^"]+)"', src):
            add(m.group(1), "placeholder", "-", fname)
        for m in re.finditer(r'aria-label="([^"]+)"', src):
            add(m.group(1), "aria-label", "-", fname)
        # JSX/HTML 텍스트 노드. 정확성 검증 발견: \n 을 제외해 자기 줄에 놓인
        # 텍스트(Prettier 기본 포맷)를 놓쳤으므로 개행을 허용하고 strip 처리.
        for m in re.finditer(r">([^<>{}]+)<", src):
            t = m.group(1).strip()
            if not t:
                continue
            if (not t.isascii()) or (re.search(r"[A-Za-z]{2,}", t) and len(t) > 3):
                add(t, "UI 텍스트", "-", fname)
        # JSX 조건부 렌더링 안의 문자열: {cond && "메시지"} / {cond ? "A" : "B"}
        for m in re.finditer(r'\{[^{}]*?&&\s*[\'"]([^\'"]{2,})[\'"]', src):
            add(m.group(1), "UI 텍스트(조건부)", "코드 분기", fname)
        for m in re.finditer(r'\?\s*[\'"]([^\'"]{2,})[\'"]\s*:\s*[\'"]([^\'"]{2,})[\'"]', src):
            add(m.group(1), "UI 텍스트(조건부)", "코드 분기", fname)
            add(m.group(2), "UI 텍스트(조건부)", "코드 분기", fname)
    seen, out = set(), []
    for m in sorted(msgs, key=lambda x: (x["source"], x["kind"], x["text"])):
        key = (m["text"], m["kind"], m["source"])
        if key not in seen:
            seen.add(key)
            out.append(m)
    return out


# ── 1-F. 상태 관리 ───────────────────────────────────────────

def extract_state(files: dict) -> list:
    """전역 상태 훅 사용처를 수집한다. 정확성 검증 발견: 이전 정규식이 빈 괄호
    `use[A-Z]\\w*\\(\\)` 만 매칭해 인자 있는 훅(useContext(Ctx), useSelector(fn),
    파라미터 받는 커스텀 훅)을 전부 놓쳤다 — React/Redux에서 가장 흔한 상태
    접근 패턴이다. 인자 유무와 무관하게, 구조분해/단일변수 할당 모두 잡는다."""
    usages = []
    for fname, src in files.items():
        # 구조분해: const { a, b } = useX(...)
        for m in re.finditer(r"const\s*\{([^}]+)\}\s*=\s*(use[A-Z]\w*)\s*\(", src):
            fields = ", ".join(sorted(f.strip() for f in m.group(1).split(",") if f.strip()))
            usages.append({"hook": m.group(2), "fields": fields, "source": fname})
        # 단일 변수: const cart = useSelector(...) (useSelector/useContext 등)
        for m in re.finditer(r"const\s+(\w+)\s*=\s*(use[A-Z]\w*)\s*\(", src):
            usages.append({"hook": m.group(2), "fields": m.group(1), "source": fname})
        for m in re.finditer(r"createContext|createStore|defineStore|createSlice", src):
            usages.append({"hook": f"({m.group(0)} 정의)", "fields": "-", "source": fname})
    uniq = {(u["hook"], u["fields"], u["source"]): u for u in usages}
    return sorted(uniq.values(), key=lambda u: (u["hook"], u["source"], u["fields"]))


# ── 1-G. 외부 연동 & 트래킹 ──────────────────────────────────

def extract_integrations(files: dict) -> dict:
    deps = []
    pkg = files.get("package.json")
    if pkg:
        try:
            data = json.loads(pkg)
            all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            deps = sorted(d for d in all_deps if d.split("/")[-1] not in FRAMEWORK_DEPS
                          and not d.startswith("@types"))
        except json.JSONDecodeError:
            pass
    tracking = []
    for fname, src in files.items():
        # 정확성 검증 발견: amplitude.track(...) 이 벤더 전용 패턴과 마지막
        # generic `track(` 패턴에 이중 매칭돼 같은 호출이 두 행(vendor + custom)으로
        # 나왔다. 벤더 패턴을 먼저 적용해 매칭 구간을 기록하고, generic 패턴은
        # 그 구간과 겹치면 건너뛰어 first-match-wins 로 만든다.
        claimed = []  # (start, end) 벤더 매칭 구간
        for pattern, tool in TRACKING_PATTERNS[:-1]:
            for m in re.finditer(pattern, src):
                claimed.append((m.start(), m.end()))
                tracking.append({"event": m.group(1), "tool": tool, "source": fname})
        generic_pat, generic_tool = TRACKING_PATTERNS[-1]
        for m in re.finditer(generic_pat, src):
            if any(a <= m.start() < b for a, b in claimed):
                continue
            tracking.append({"event": m.group(1), "tool": generic_tool, "source": fname})
    tracking = sorted({(t["event"], t["tool"], t["source"]): t for t in tracking}.values(),
                      key=lambda t: (t["tool"], t["event"], t["source"]))
    return {"third_party_deps": deps, "tracking": tracking}


# ── 1-H. As-Is 스냅샷 ────────────────────────────────────────

def extract_snapshot(root: pathlib.Path, files: dict) -> dict:
    # 결정성 검증 발견: 축약 해시 %h 는 clone 방식/오브젝트 수/core.abbrev 에 따라
    # 같은 커밋도 값이 달라진다. reference.md 스펙대로 전체 해시(%H)를 사용한다.
    commit, when = "git 정보 없음", "-"
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%H|%ci"], cwd=root,
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and "|" in out.stdout:
            commit, when = out.stdout.strip().split("|", 1)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {"commit": commit, "commit_time": when, "files": sorted(files)}


# ── 1-J. 하드코딩 시크릿 노출 스캔 (reverse-backend에서 검증된 로직 이식) ──

def extract_secret_findings(root: pathlib.Path) -> list:
    """reference.md의 '민감 정보는 문서에 포함하지 않고 경고로 표시'라는 원칙이
    실제로는 코드로 강제되지 않던 것을 이식으로 보완 (reverse-backend 자매
    스킬에서 먼저 구현·검증됨). 실제 값은 절대 읽어 반환하지 않는다."""
    findings = []
    tracked = set()
    try:
        out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True,
                             text=True, timeout=10)
        if out.returncode == 0:
            tracked = set(out.stdout.splitlines())
    except (OSError, subprocess.TimeoutExpired):
        pass

    # 심볼릭 링크는 건너뛴다(_walk_safe_files) — root 밖 파일 접근 차단.
    for p in _walk_safe_files(root):
        if ".git" in p.parts:
            continue
        rel = str(p.relative_to(root))
        if p.name in SECRET_FILENAMES or p.suffix in SECRET_SUFFIXES:
            findings.append({"path": rel, "pattern": f"파일명/확장자: {p.name or p.suffix}",
                             "tracked": rel in tracked})
            continue
        # 보안 검증 발견: `.env` 완전일치만 봐서 .env.local/.env.production 등
        # 프레임워크 공통 변형을 놓쳤다 — .env 로 시작하면 모두 잡는다.
        if p.name == ".env" or p.name.startswith(".env."):
            findings.append({"path": rel, "pattern": f"{p.name} 파일", "tracked": rel in tracked})
            continue
        # .vue 도 스캔 대상에 포함 (SRC_EXT엔 있으면서 시크릿 스캔에선 빠져있던 비일관 수정)
        if p.suffix in (".ts", ".tsx", ".js", ".jsx", ".vue", ".json", ".yml", ".yaml"):
            try:
                # 보안 검증 발견(PR 리뷰): read_sources()의 MAX_FILE_BYTES 상한은
                # 이 시크릿 스캔 경로를 거치지 않는다 — 일반 소스 파일 하나와
                # 거대한 파일 하나가 같이 있는 디렉터리를 대상으로 주면, 거대한
                # 파일이 read_sources()에서는 건너뛰어져도 여기서는 별도로
                # 다시 읽혀 상한 없이 모든 정규식을 그대로 돌았다 — 동일한
                # 상한을 여기에도 적용한다.
                if p.stat().st_size > MAX_FILE_BYTES:
                    print(f"⚠️  시크릿 스캔에서 건너뜀(파일 크기 {p.stat().st_size:,}B > 상한): {p}",
                          file=sys.stderr)
                    continue
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for pattern, label in SECRET_KEY_PATTERNS:
                if re.search(pattern, text):
                    findings.append({"path": rel, "pattern": label, "tracked": rel in tracked})
                    break
    uniq = {(f["path"], f["pattern"]): f for f in findings}
    return sorted(uniq.values(), key=lambda f: f["path"])


# ── 출력 ─────────────────────────────────────────────────────

def _escape_cell(v: str) -> str:
    """테이블 셀 안전화.

    - 백틱(`...`)으로 감싼 값은 마크다운 코드 스팬이 되어 렌더러가 파이프를
      리터럴로 보존하고 raw HTML도 자동 이스케이프하므로 그대로 둔다. (백틱
      안에서 `\\|`를 이스케이프하면 CommonMark 규칙상 백슬래시가 그대로 노출됨.)
    - 백틱 밖 순수 텍스트(메시지 카탈로그 문구·효과 설명 등)는:
        1) 보안 검증 발견: python-markdown이 raw HTML을 통과시켜, 분석 대상
           코드에서 추출한 문자열에 `<img src=x onerror=...>` 같은 태그가
           있으면 생성 HTML에서 그대로 실행될 수 있었다(저장형 XSS). `<`,`>`,`&`
           를 HTML 엔티티로 이스케이프해 차단한다.
        2) 파이프(|)는 `\\|`로 이스케이프해 셀 컬럼 분리를 막는다."""
    s = str(v)
    if s.startswith("`") and s.endswith("`") and len(s) >= 2:
        return s
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s.replace("|", "\\|")


def md_table(headers: list, rows: list) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_escape_cell(v) for v in r) + " |")
    return "\n".join(out)


def guard_label(g: str) -> str:
    if g == "public":
        return "공개"
    if g == "login":
        return "🔒 로그인"
    return f"🔒 {g.split(':', 1)[1]}" if g.startswith("role:") else g


def build_facts_md(root, routes, comps, apis, consts, rules, trans, msgs, state,
                   integ, snap, secrets) -> str:
    s = ["<!-- scripts/extract.py 출력 — 결정적 사실 계층. LLM은 이 표를 근거로만 해석한다. -->",
         ""]
    if secrets:
        s += ["## ⚠️ 1-J. 하드코딩 시크릿 노출 스캔 — 발견됨 (값은 미출력)", "",
              md_table(["파일 경로", "발견 패턴", "git 추적됨"],
                       [[f["path"], f["pattern"], "예 — 즉시 로테이션 권고" if f["tracked"]
                         else "아니오"] for f in secrets]),
              "", "> 실제 값은 이 문서에 포함하지 않았다. git 추적 대상이면 이미 커밋 "
              "이력에 남아있으므로 값 로테이션 + 히스토리 제거를 권고한다.", ""]
    else:
        s += ["## 1-J. 하드코딩 시크릿 노출 스캔", "", "발견된 항목 없음 (스캔 범위 내).", ""]
    s += ["## 1-H. As-Is 스냅샷 (비교 기준선)", "",
         md_table(["항목", "값"], [["기준 커밋", f"`{snap['commit']}`"],
                                   ["커밋 시점", snap["commit_time"]],
                                   ["분석 파일 수", len(snap["files"])],
                                   ["분석 파일", " · ".join(f"`{f}`" for f in snap["files"])]]),
         "", "## 1-A. 라우트 맵", "",
         md_table(["Path", "컴포넌트", "보호", "근거 파일"],
                  [[r["path"], r["component"], guard_label(r["guard"]), f'`{r["source"]}`']
                   for r in routes]) if routes else "(라우트 정의 미발견)",
         "", "## 1-B. 컴포넌트 분석 범위", "",
         md_table(["컴포넌트", "소스 파일", "분석 가능"],
                  [[c["name"], f'`{c["source"]}`' if c["source"] else "—",
                    "✅ 소스 포함" if c["analyzed"] else "❌ import만 — [정보 없음]"]
                   for c in comps]) if comps else "(컴포넌트 미발견)",
         "", "## 1-C. API 호출", "",
         md_table(["엔드포인트", "메서드", "근거"],
                  [[f'`{a["endpoint"]}`', a["method"], f'`{a["source"]}`'] for a in apis])
         if apis else "(API 호출 미발견)",
         "", "## 1-C. 비즈니스 상수", "",
         md_table(["상수", "값", "근거 파일"],
                  [[f'`{c["name"]}`', c["value"], f'`{c["source"]}`'] for c in consts])
         if consts else "(상수 미발견)",
         "", "## 1-C. 검증/차단 규칙", "",
         md_table(["유형", "조건", "효과", "근거 파일"],
                  [[r["kind"], f'`{r["condition"]}`', r["effect"], f'`{r["source"]}`']
                   for r in rules]) if rules else "(규칙 미발견)",
         "", "## 1-D. 화면 전환 호출", "",
         md_table(["출발(파일)", "도착 경로", "방식"],
                  [[f'`{t["source"]}`', f'`{t["target"]}`', t["via"]] for t in trans])
         if trans else "(전환 호출 미발견)",
         "", "## 1-E. 사용자 노출 문구 (에러/메시지 카탈로그 원자료)", "",
         md_table(["ID", "문구", "유형", "노출 조건", "근거 파일"],
                  [[f"MSG-{i+1:02d}", m["text"], m["kind"], f'`{m["cond"]}`'
                    if m["cond"] != "-" else "-", f'`{m["source"]}`']
                   for i, m in enumerate(msgs)]) if msgs else "(문구 미발견)",
         "", "## 1-F. 상태 관리 사용처", "",
         md_table(["상태 단위", "사용 필드/액션", "사용 파일"],
                  [[f'`{u["hook"]}`', u["fields"], f'`{u["source"]}`'] for u in state])
         if state else "(전역 상태 사용 미발견)",
         "", "## 1-G. 외부 연동 & 트래킹", "",
         ("서드파티 의존성: " + (", ".join(f"`{d}`" for d in integ["third_party_deps"])
                                if integ["third_party_deps"]
                                else "**해당 없음** (프레임워크 외 서비스 SDK 없음)")),
         "",
         md_table(["이벤트", "도구", "근거 파일"],
                  [[t["event"], t["tool"], f'`{t["source"]}`'] for t in integ["tracking"]])
         if integ["tracking"]
         else "트래킹 호출: **[정보 없음 — 트래킹 미구현 또는 서버 측]**",
         "",
         f"<!-- 추출 통계: 라우트 {len(routes)} · 컴포넌트 {len(comps)} · API {len(apis)} · "
         f"상수 {len(consts)} · 규칙 {len(rules)} · 전환 {len(trans)} · 문구 {len(msgs)} · "
         f"상태 {len(state)} · 트래킹 {len(integ['tracking'])} -->"]
    return "\n".join(s) + "\n"


def build_flow_skeleton(routes, trans, comps) -> dict:
    """flowgen.py 입력 스켈레톤. LLM이 라벨/점선(추정 표시)을 보강해 사용한다."""
    comp_route = {r["component"]: r["path"] for r in routes}
    file_comp = {c["source"]: c["name"] for c in comps if c["source"]}
    nodes = []
    for r in routes:
        guard = ("admin" if r["guard"].startswith("role:")
                 else "login" if r["guard"] == "login" else "public")
        nid = re.sub(r"[^a-zA-Z0-9]+", "_", r["path"]).strip("_") or "root"
        nodes.append({"id": nid, "label": f'{r["component"]} {r["path"]}', "guard": guard})
    path_id = {r["path"]: re.sub(r"[^a-zA-Z0-9]+", "_", r["path"]).strip("_") or "root"
               for r in routes}
    edges = []
    for t in trans:
        comp = next((c for f, c in file_comp.items() if t["source"].endswith(f)
                     or f.endswith(t["source"])), None)
        src_path = comp_route.get(comp)
        if src_path and t["target"] in path_id:
            edges.append({"from": path_id[src_path], "to": path_id[t["target"]],
                          "label": t["via"]})
    seen, uniq_edges = set(), []
    for e in edges:
        k = (e["from"], e["to"])
        if k not in seen:
            seen.add(k)
            uniq_edges.append(e)
    return {"nodes": nodes, "edges": uniq_edges,
            "entry": [path_id.get("/", nodes[0]["id"] if nodes else "root")]}


def main() -> int:
    ap = argparse.ArgumentParser(description="결정적 코드 사실 추출기 (1-A~1-H)")
    ap.add_argument("target", help="분석 대상 디렉토리 또는 파일")
    ap.add_argument("--output", help="사실 표 Markdown 출력 경로 (생략 시 stdout)")
    ap.add_argument("--emit-flow", help="flowgen용 흐름 스켈레톤 JSON 출력 경로")
    args = ap.parse_args()

    root = pathlib.Path(args.target)
    if root.is_file():
        # 보안 검증 발견(PR 리뷰): 대상이 파일 하나로 직접 지정되면 이 분기가
        # read_sources()를 완전히 우회해, read_sources() 안에 있는
        # MAX_FILE_BYTES 크기 상한이 전혀 적용되지 않았다 — 거대한 적대적
        # 파일을 직접 지정하면 상한 없이 모든 추출기에 그대로 들어갔다.
        # read_sources()와 동일한 상한을 여기서도 적용한다.
        if root.stat().st_size > MAX_FILE_BYTES:
            print(f"⚠️  건너뜀(파일 크기 {root.stat().st_size:,}B > 상한): {root}",
                  file=sys.stderr)
            files = {}
        else:
            files = {root.name: root.read_text(encoding="utf-8")}
        root = root.parent
    else:
        files = read_sources(root)
    if not files:
        print("❌ 분석 가능한 소스 파일이 없습니다.", file=sys.stderr)
        return 1

    routes = extract_routes(files)
    comps = extract_components(files)
    apis = extract_api_calls(files)
    consts = extract_constants(files)
    rules = extract_rules(files)
    trans = extract_transitions(files)
    msgs = extract_messages(files)
    state = extract_state(files)
    integ = extract_integrations(files)
    snap = extract_snapshot(root, files)
    secrets = extract_secret_findings(root)

    md = build_facts_md(root, routes, comps, apis, consts, rules, trans, msgs,
                        state, integ, snap, secrets)
    if args.output:
        pathlib.Path(args.output).write_text(md, encoding="utf-8")
        print(f"✅ 사실 표 생성 완료: {args.output}", file=sys.stderr)
    else:
        print(md)

    if args.emit_flow:
        flow = build_flow_skeleton(routes, trans, comps)
        pathlib.Path(args.emit_flow).write_text(
            json.dumps(flow, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 흐름 스켈레톤 생성 완료: {args.emit_flow}", file=sys.stderr)

    if secrets:
        print(f"⚠️  시크릿 노출 의심 {len(secrets)}건 발견 — facts.md 1-J 참조",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
