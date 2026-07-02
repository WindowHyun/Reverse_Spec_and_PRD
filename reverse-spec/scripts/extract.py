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
  facts.md   : 1-A~1-H 사실 표 (Markdown) — 문서의 사실 계층에 그대로 사용
  flow.json  : (선택) flowgen.py 입력용 흐름도 스켈레톤 — LLM이 라벨/점선 보강 후 사용
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

SRC_EXT = (".tsx", ".ts", ".jsx", ".js", ".vue", ".html")
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


def read_sources(root: pathlib.Path) -> dict:
    files = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in ("node_modules", ".git", "dist", "build") for part in p.parts):
            continue
        if p.suffix in SRC_EXT or p.name == "package.json":
            try:
                files[str(p.relative_to(root))] = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
    return files


# ── 1-A. 라우트 ──────────────────────────────────────────────

def extract_routes(files: dict) -> list:
    routes = []
    for fname, src in files.items():
        if "createBrowserRouter" in src or "createHashRouter" in src:
            for block in re.split(r"\},\s*\{", src):
                m_path = re.search(r'path:\s*"([^"]+)"', block)
                if not m_path:
                    continue
                stripped = block.replace("RequireAuth", "", 1) if "<RequireAuth" in block else block
                m_elem = re.search(r"<(\w+)\s*/?>", stripped)
                guard = "public"
                m_role = re.search(r'<RequireAuth\s+role="([^"]+)"', block)
                if m_role:
                    guard = f"role:{m_role.group(1)}"
                elif "<RequireAuth" in block:
                    guard = "login"
                routes.append({"path": m_path.group(1),
                               "component": m_elem.group(1) if m_elem else "?",
                               "guard": guard, "source": fname})
        # React Router JSX / Vue Router routes 배열
        for m in re.finditer(r'<Route\s+path="([^"]+)"\s+element=\{<(\w+)', src):
            routes.append({"path": m.group(1), "component": m.group(2),
                           "guard": "public", "source": fname})
        if "vue-router" in src or "createRouter" in src:
            for m in re.finditer(r"path:\s*['\"]([^'\"]+)['\"][^}]*?component:\s*(\w+)", src, re.S):
                routes.append({"path": m.group(1), "component": m.group(2),
                               "guard": "public", "source": fname})
    uniq = {(r["path"], r["source"]): r for r in routes}
    return sorted(uniq.values(), key=lambda r: r["path"])


# ── 1-B. 컴포넌트 ────────────────────────────────────────────

def extract_components(files: dict) -> list:
    defined, referenced = {}, set()
    for fname, src in files.items():
        for m in re.finditer(r"export\s+default\s+function\s+(\w+)", src):
            defined[m.group(1)] = fname
        for m in re.finditer(r"export\s+default\s+(\w+)\s*;", src):
            defined.setdefault(m.group(1), fname)
        for m in re.finditer(r'import\s+(\w+)\s+from\s+["\']\.{1,2}/', src):
            referenced.add(m.group(1))
    rows = []
    for name in sorted(referenced | set(defined)):
        rows.append({"name": name, "source": defined.get(name, ""),
                     "analyzed": name in defined})
    return rows


# ── 1-C. API / 상수 / 검증·차단 규칙 ─────────────────────────

def extract_api_calls(files: dict) -> list:
    calls = []
    for fname, src in files.items():
        for m in re.finditer(r'fetch\(\s*[\'"`]([^\'"`]+)[\'"`](.*?)\)', src, re.S):
            method = "GET"
            m_method = re.search(r'method:\s*[\'"](\w+)[\'"]', m.group(2))
            if m_method:
                method = m_method.group(1)
            calls.append({"endpoint": m.group(1), "method": method, "source": fname})
        for m in re.finditer(r"\baxios\.(get|post|put|patch|delete)\(\s*[\'\"`]([^\'\"`]+)", src):
            calls.append({"endpoint": m.group(2), "method": m.group(1).upper(), "source": fname})
        for m in re.finditer(r"//\s*(GET|POST|PUT|PATCH|DELETE)\s+(/\S+)", src):
            calls.append({"endpoint": m.group(2), "method": m.group(1),
                          "source": fname + " (주석)"})
    uniq = {(c["endpoint"], c["method"]): c for c in calls}
    return sorted(uniq.values(), key=lambda c: (c["endpoint"], c["method"]))


def extract_constants(files: dict) -> list:
    consts = []
    for fname, src in files.items():
        for m in re.finditer(r"const\s+([A-Z][A-Z0-9_]+)\s*=\s*([\d_.]+)", src):
            consts.append({"name": m.group(1), "value": m.group(2), "source": fname})
    return sorted(consts, key=lambda c: (c["name"], c["source"]))


def extract_rules(files: dict) -> list:
    rules = []
    for fname, src in files.items():
        for m in re.finditer(r'if\s*\(([^)]+)\)\s*return\s*"([^"]+)"', src):
            rules.append({"kind": "입력 검증", "condition": m.group(1).strip(),
                          "effect": f'메시지 "{m.group(2)}"', "source": fname})
        for m in re.finditer(r"min=\{(\w+)\}\s+max=\{([\w.]+)\}", src):
            rules.append({"kind": "범위 제한", "condition": f"min {m.group(1)} / max {m.group(2)}",
                          "effect": "입력값 범위 강제", "source": fname})
        for m in re.finditer(r"disabled=\{([^}]+)\}", src):
            rules.append({"kind": "동작 차단", "condition": m.group(1).strip(),
                          "effect": "버튼 비활성화", "source": fname})
        for m in re.finditer(r'if\s*\(!?(\w+)\)\s*\{\s*alert\("([^"]+)"\)', src):
            rules.append({"kind": "필수값", "condition": f"{m.group(1)} 조건 불충족",
                          "effect": f'알림 "{m.group(2)}" 후 중단', "source": fname})
    return sorted(rules, key=lambda r: (r["kind"], r["condition"], r["source"]))


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
    return sorted(uniq.values(), key=lambda t: (t["source"], t["target"]))


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
        for m in re.finditer(r'if\s*\(([^)]+)\)\s*return\s*"([^"]+)"', src):
            add(m.group(2), "에러", m.group(1).strip(), fname)
        for m in re.finditer(r'setError\(\s*"([^"]+)"\s*\)', src):
            add(m.group(1), "에러", "코드 분기", fname)
        for m in re.finditer(r'placeholder="([^"]+)"', src):
            add(m.group(1), "placeholder", "-", fname)
        for m in re.finditer(r'aria-label="([^"]+)"', src):
            add(m.group(1), "aria-label", "-", fname)
        # JSX/HTML 텍스트 노드 (중괄호 없는 순수 텍스트)
        for m in re.finditer(r">([^<>{}\n]+)<", src):
            t = m.group(1).strip()
            if t and not t.isascii() or (t and re.search(r"[A-Za-z]{2,}", t) and len(t) > 3):
                add(t, "UI 텍스트", "-", fname)
    seen, out = set(), []
    for m in sorted(msgs, key=lambda x: (x["source"], x["kind"], x["text"])):
        key = (m["text"], m["kind"], m["source"])
        if key not in seen:
            seen.add(key)
            out.append(m)
    return out


# ── 1-F. 상태 관리 ───────────────────────────────────────────

def extract_state(files: dict) -> list:
    usages = []
    for fname, src in files.items():
        for m in re.finditer(r"const\s*\{([^}]+)\}\s*=\s*(use[A-Z]\w*)\(\)", src):
            fields = ", ".join(sorted(f.strip() for f in m.group(1).split(",") if f.strip()))
            usages.append({"hook": m.group(2), "fields": fields, "source": fname})
        for m in re.finditer(r"createContext|createStore|defineStore|createSlice", src):
            usages.append({"hook": f"({m.group(0)} 정의)", "fields": "-", "source": fname})
    return sorted(usages, key=lambda u: (u["hook"], u["source"]))


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
        for pattern, tool in TRACKING_PATTERNS:
            for m in re.finditer(pattern, src):
                tracking.append({"event": m.group(1), "tool": tool, "source": fname})
    tracking = sorted({(t["event"], t["tool"], t["source"]): t for t in tracking}.values(),
                      key=lambda t: (t["tool"], t["event"]))
    return {"third_party_deps": deps, "tracking": tracking}


# ── 1-H. As-Is 스냅샷 ────────────────────────────────────────

def extract_snapshot(root: pathlib.Path, files: dict) -> dict:
    commit, when = "git 정보 없음", "-"
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h|%ci"], cwd=root,
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and "|" in out.stdout:
            commit, when = out.stdout.strip().split("|", 1)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {"commit": commit, "commit_time": when, "files": sorted(files)}


# ── 출력 ─────────────────────────────────────────────────────

def md_table(headers: list, rows: list) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(v).replace("|", "\\|") for v in r) + " |")
    return "\n".join(out)


def guard_label(g: str) -> str:
    if g == "public":
        return "공개"
    if g == "login":
        return "🔒 로그인"
    return f"🔒 {g.split(':', 1)[1]}" if g.startswith("role:") else g


def build_facts_md(root, routes, comps, apis, consts, rules, trans, msgs, state,
                   integ, snap) -> str:
    s = ["<!-- scripts/extract.py 출력 — 결정적 사실 계층. LLM은 이 표를 근거로만 해석한다. -->",
         "", "## 1-H. As-Is 스냅샷 (비교 기준선)", "",
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

    md = build_facts_md(root, routes, comps, apis, consts, rules, trans, msgs,
                        state, integ, snap)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
