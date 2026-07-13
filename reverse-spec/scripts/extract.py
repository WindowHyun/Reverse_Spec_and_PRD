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
import hashlib
import json
import pathlib
import re
import subprocess
import sys

SRC_EXT = (".tsx", ".ts", ".jsx", ".js", ".vue", ".html")

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
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                # 구조 재점검 발견: 권한 오류 등 OSError는 잡지 않아 파일 하나로
                # 전체 추출이 죽었다 (시크릿 스캔 쪽은 이미 잡고 있던 비일관).
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
        # React Router JSX: element={ ... } 전체를 캡처해 가드/컴포넌트 파싱
        for m in re.finditer(r'<Route\s+path="([^"]+)"\s+element=\{(.*?)\}\s*/?>', src, re.S):
            component, guard = _component_and_guard(m.group(2))
            routes.append({"path": m.group(1), "component": component,
                           "guard": guard, "source": fname})
        # Vue Router: path와 component 사이에 meta:{...} 등 중첩 객체가 있어도
        # 매칭되도록, 그리고 lazy-load(() => import("..."))도 잡도록 개선.
        # 구조 재점검 발견: 사이 구간이 라우트 객체 경계를 넘어갈 수 있어,
        # component 없는 라우트(redirect 등)가 다음 라우트의 component와 오결합되고
        # 그 다음 라우트는 표에서 사라졌다 — 사이 구간에 다음 `path:`가 나오면
        # 매칭을 중단해 같은 라우트 객체 안에서만 짝을 짓는다.
        if "vue-router" in src or "createRouter" in src:
            for m in re.finditer(
                    r"path:\s*['\"]([^'\"]+)['\"](?:(?!path\s*:)[\s\S]){0,300}?component:\s*"
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

def _find_matching(src: str, open_idx: int, open_ch: str, close_ch: str) -> int:
    """open_idx의 여는 괄호에 대응하는 닫는 괄호 인덱스를 중첩까지 셈해 찾는다."""
    depth = 0
    for i in range(open_idx, len(src)):
        if src[i] == open_ch:
            depth += 1
        elif src[i] == close_ch:
            depth -= 1
            if depth == 0:
                return i
    return -1


def _find_matching_paren(src: str, open_idx: int) -> int:
    """`(`에 대응하는 `)` 인덱스. 중첩 괄호 안전 (실전 검증에서 fetch(...) /
    if(...) 정규식의 조기종료 버그를 잡기 위해 도입)."""
    return _find_matching(src, open_idx, "(", ")")


def extract_api_calls(files: dict) -> list:
    calls = []
    for fname, src in files.items():
        for m in re.finditer(r'fetch\(\s*[\'"`]([^\'"`]+)[\'"`]', src):
            paren_idx = src.index("(", m.start())
            close_idx = _find_matching_paren(src, paren_idx)
            call_text = src[paren_idx:close_idx + 1] if close_idx != -1 else m.group(0)
            method = "GET"
            m_method = re.search(r'method:\s*[\'"](\w+)[\'"]', call_text)
            if m_method:
                method = m_method.group(1)
            calls.append({"endpoint": m.group(1), "method": method, "source": fname})
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


def _find_if_return_pairs(src: str) -> list:
    """`if (조건) return "메시지"` 패턴을 중첩 괄호까지 고려해 찾는다.
    extract_rules와 extract_messages가 공유하는 헬퍼(중복 로직 통합).

    정확성 검증 발견 후 개선:
    - 중괄호 블록형 early-return `if (cond) { return "msg" }` 지원
      (Prettier/ESLint curly 규칙상 오히려 주류 스타일인데 누락되고 있었음).
    - 단따옴표/템플릿 리터럴 return 문자열도 지원(이전엔 큰따옴표만)."""
    pairs = []
    for m in re.finditer(r"if\s*\(", src):
        paren_idx = src.index("(", m.start())
        close_idx = _find_matching_paren(src, paren_idx)
        if close_idx == -1:
            continue
        condition = src[paren_idx + 1:close_idx].strip()
        # `)` 다음에 (선택적 `{` 블록 후) return "…"/'…'/`…` 이 오는지 확인
        m2 = re.match(r'\s*\{?\s*return\s+(["\'`])(.*?)\1',
                      src[close_idx + 1:close_idx + 400], re.S)
        if condition and m2:
            pairs.append((condition, m2.group(2).strip()))
    return pairs


def extract_rules(files: dict) -> list:
    rules = []
    for fname, src in files.items():
        for condition, message in _find_if_return_pairs(src):
            rules.append({"kind": "입력 검증", "condition": condition,
                          "effect": f'메시지 "{message}"', "source": fname})
        # min/max는 순서·인접에 무관하게(사이에 다른 속성 허용, 역순 허용) 잡는다
        for m in re.finditer(r"min=\{(\w+)\}[^>]*?max=\{([\w.]+)\}", src):
            rules.append({"kind": "범위 제한", "condition": f"min {m.group(1)} / max {m.group(2)}",
                          "effect": "입력값 범위 강제", "source": fname})
        for m in re.finditer(r"max=\{([\w.]+)\}[^>]*?min=\{(\w+)\}", src):
            rules.append({"kind": "범위 제한", "condition": f"min {m.group(2)} / max {m.group(1)}",
                          "effect": "입력값 범위 강제", "source": fname})
        # disabled={...} 의 조건은 중첩 중괄호(화살표 블록/객체)까지 포함해 잡는다
        for m in re.finditer(r"disabled=\{", src):
            open_idx = src.index("{", m.start())
            close_idx = _find_matching(src, open_idx, "{", "}")
            if close_idx != -1:
                cond = src[open_idx + 1:close_idx].strip()
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
            # 구조 재점검 발견: 화살표 함수 `=>` 뒤부터 다음 JSX `<` 사이의 코드가
            # UI 텍스트로 오탐됐다(예: `=> navigate("/x"); ... return <div>`) —
            # `>` 바로 앞이 `=`이면(=> 또는 >=) 텍스트 노드가 아니므로 건너뛴다.
            if m.start() > 0 and src[m.start() - 1] == "=":
                continue
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
        # 구조 재점검 발견: read_sources와 달리 .git만 제외해 node_modules의
        # vendored 코드가 프로젝트 시크릿으로 오탐되고, 실제 프로젝트에선
        # 수만 파일을 스캔하는 성능 문제가 있었다 — 소스 분석과 동일 기준으로 제외.
        if any(part in ("node_modules", ".git", "dist", "build") for part in p.parts):
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
    # 구조 재점검 발견: 여러 줄 조건식(Prettier 표준 포맷의 `if (\n !a ||\n !b\n)`,
    # 여러 줄 disabled={...})이 셀에 개행 그대로 들어가 표 행이 여러 줄로 쪼개지며
    # Markdown 표 구조 자체가 파손됐다 — 개행(및 주변 들여쓰기)을 공백 하나로 접는다.
    s = re.sub(r"\s*\n\s*", " ", s)
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


def _msg_id(m: dict, used: set) -> str:
    """메시지 카탈로그 행 ID. 구조 재점검 발견: 순번 기반(MSG-01, 02…)은 문구가
    하나만 추가/삭제돼도 전체가 재번호돼, As-Is 스냅샷(버전 간 비교)과 추적성
    매트릭스(문서가 MSG ID를 참조)의 취지와 충돌했다 — (문구|유형|근거 파일)
    해시 기반으로 바꿔 다른 문구가 바뀌어도 기존 행의 ID가 유지되게 한다.
    해시 접두어가 충돌하면(희귀) 결정적으로 자릿수를 늘려 구분한다."""
    h = hashlib.sha256(f'{m["text"]}|{m["kind"]}|{m["source"]}'.encode("utf-8")).hexdigest()
    n = 6
    while h[:n] in used and n < len(h):
        n += 2
    used.add(h[:n])
    return f"MSG-{h[:n]}"


def guard_label(g: str) -> str:
    if g == "public":
        return "공개"
    if g == "login":
        return "🔒 로그인"
    return f"🔒 {g.split(':', 1)[1]}" if g.startswith("role:") else g


def build_facts_md(root, routes, comps, apis, consts, rules, trans, msgs, state,
                   integ, snap, secrets) -> str:
    _msg_ids_used = set()  # 해시 접두어 충돌 감지용 (1-E ID 생성)
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
                  [[_msg_id(m, _msg_ids_used), m["text"], m["kind"], f'`{m["cond"]}`'
                    if m["cond"] != "-" else "-", f'`{m["source"]}`']
                   for m in msgs]) if msgs else "(문구 미발견)",
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
    # 구조 재점검 발견: 슬러그가 같아지는 경로(/a-b vs /a/b)가 같은 노드 id를 받아
    # flowgen에서 두 노드가 같은 좌표에 겹쳐 그려졌다 — _2, _3 접미사로 구분하고,
    # 같은 path가 여러 파일에 정의된 경우 노드는 1개만 만든다.
    path_id, used, nodes = {}, set(), []
    for r in routes:
        if r["path"] in path_id:
            continue
        base = re.sub(r"[^a-zA-Z0-9]+", "_", r["path"]).strip("_") or "root"
        nid, n = base, 2
        while nid in used:
            nid, n = f"{base}_{n}", n + 1
        used.add(nid)
        path_id[r["path"]] = nid
        guard = ("admin" if r["guard"].startswith("role:")
                 else "login" if r["guard"] == "login" else "public")
        nodes.append({"id": nid, "label": f'{r["component"]} {r["path"]}', "guard": guard})
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
    # 노드가 하나도 없으면 entry도 비운다 (이전엔 존재하지 않는 "root"를 넣어
    # flowgen이 빈 그래프에서 크래시하는 원인을 제공했다).
    entry = ([path_id["/"]] if "/" in path_id
             else [nodes[0]["id"]] if nodes else [])
    return {"nodes": nodes, "edges": uniq_edges, "entry": entry}


def main() -> int:
    ap = argparse.ArgumentParser(description="결정적 코드 사실 추출기 (1-A~1-H)")
    ap.add_argument("target", help="분석 대상 디렉토리 또는 파일")
    ap.add_argument("--output", help="사실 표 Markdown 출력 경로 (생략 시 stdout)")
    ap.add_argument("--emit-flow", help="flowgen용 흐름 스켈레톤 JSON 출력 경로")
    args = ap.parse_args()

    root = pathlib.Path(args.target)
    if root.is_file():
        # 구조 재점검 발견: 단일 파일 모드는 주석 블랭킹을 건너뛰어, 주석 처리된
        # 죽은 코드(`// fetch("/api/dead")`)가 실제 API/전환으로 오탐됐다 —
        # 디렉토리 모드(read_sources)와 동일하게 처리한다.
        text = root.read_text(encoding="utf-8")
        if root.name != "package.json":
            text = _blank_full_line_comments(text)
        files = {root.name: text}
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
