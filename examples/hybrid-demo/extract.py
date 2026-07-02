#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
하이브리드 역기획 데모용 결정적 추출기 (프로토타입).

LLM 없이 정규식/규칙만으로 코드에서 '사실'을 추출한다.
같은 입력 → 항상 같은 출력 (모든 목록은 정렬, 타임스탬프 없음).

사용법: python extract.py <소스_디렉토리> > facts.md
"""
import pathlib
import re
import sys


def read_sources(root: pathlib.Path) -> dict:
    files = {}
    for p in sorted(root.rglob("*")):
        if p.suffix in (".tsx", ".ts", ".jsx", ".js", ".vue", ".html", ".json") and p.is_file():
            files[str(p.relative_to(root))] = p.read_text(encoding="utf-8")
    return files


def extract_routes(files: dict) -> list:
    """router 파일의 { path: "...", element: <X/> } 및 RequireAuth 가드 추출."""
    routes = []
    for fname, src in files.items():
        if "createBrowserRouter" not in src and "<Route" not in src:
            continue
        # path/element 쌍 (RequireAuth 래핑 포함, 블록 단위로 분리)
        for block in re.split(r"\},\s*\{", src):
            m_path = re.search(r'path:\s*"([^"]+)"', block)
            if not m_path:
                continue
            m_elem = re.search(r"<(\w+)\s*/?>", block.replace("RequireAuth", "", 1)
                               if "RequireAuth" in block else block)
            guard = "공개"
            m_role = re.search(r'<RequireAuth\s+role="([^"]+)"', block)
            if m_role:
                guard = f"role={m_role.group(1)}"
            elif "<RequireAuth" in block:
                guard = "로그인 필요"
            routes.append({
                "path": m_path.group(1),
                "component": m_elem.group(1) if m_elem else "?",
                "guard": guard,
                "source": fname,
            })
    return sorted(routes, key=lambda r: r["path"])


def extract_components(files: dict) -> list:
    """export default function 컴포넌트와 소스 포함 여부."""
    defined = {}
    referenced = set()
    for fname, src in files.items():
        for m in re.finditer(r"export\s+default\s+function\s+(\w+)", src):
            defined[m.group(1)] = fname
        for m in re.finditer(r'import\s+(\w+)\s+from\s+"\./pages/(\w+)"', src):
            referenced.add(m.group(1))
    rows = []
    for name in sorted(referenced | set(defined)):
        rows.append({
            "name": name,
            "source": defined.get(name, "—"),
            "analyzed": name in defined,
        })
    return rows


def extract_api_calls(files: dict) -> list:
    """fetch(...) 호출과 메서드."""
    calls = []
    for fname, src in files.items():
        for m in re.finditer(r'fetch\(\s*"([^"]+)"(.*?)\)', src, re.S):
            method = "GET"
            m_method = re.search(r'method:\s*"(\w+)"', m.group(2))
            if m_method:
                method = m_method.group(1)
            calls.append({"endpoint": m.group(1), "method": method, "source": fname})
        # 주석으로 표기된 엔드포인트 (예: // POST /api/auth/login)
        for m in re.finditer(r"//\s*(GET|POST|PUT|DELETE)\s+(/\S+)", src):
            calls.append({"endpoint": m.group(2), "method": m.group(1),
                          "source": fname + " (주석)"})
    uniq = {(c["endpoint"], c["method"]): c for c in calls}
    return sorted(uniq.values(), key=lambda c: (c["endpoint"], c["method"]))


def extract_constants(files: dict) -> list:
    """UPPER_SNAKE 숫자 상수 (비즈니스 규칙 후보)."""
    consts = []
    for fname, src in files.items():
        for m in re.finditer(r"const\s+([A-Z][A-Z0-9_]+)\s*=\s*([\d_]+)", src):
            consts.append({"name": m.group(1), "value": m.group(2), "source": fname})
    return sorted(consts, key=lambda c: c["name"])


def extract_validations(files: dict) -> list:
    """검증 규칙: 사용자 노출 메시지가 있는 조건, min/max 속성, disabled 조건."""
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
        for m in re.finditer(r'if\s*\(!(\w+)\)\s*\{\s*alert\("([^"]+)"\)', src):
            rules.append({"kind": "필수값", "condition": f"{m.group(1)} 미입력",
                          "effect": f'알림 "{m.group(2)}" 후 중단', "source": fname})
    return sorted(rules, key=lambda r: (r["kind"], r["condition"]))


def md_table(headers: list, rows: list) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(v) for v in r) + " |")
    return "\n".join(out)


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    files = read_sources(root)
    routes = extract_routes(files)
    comps = extract_components(files)
    apis = extract_api_calls(files)
    consts = extract_constants(files)
    vals = extract_validations(files)

    print("## 라우트 맵 (파서 추출)")
    print()
    print(md_table(["Path", "컴포넌트", "보호", "근거 파일"],
                   [[r["path"], r["component"], r["guard"], f'`{r["source"]}`'] for r in routes]))
    print()
    print("## 컴포넌트 분석 범위 (파서 추출)")
    print()
    print(md_table(["컴포넌트", "소스 파일", "분석 가능"],
                   [[c["name"], f'`{c["source"]}`' if c["source"] != "—" else "—",
                     "✅ 소스 포함" if c["analyzed"] else "❌ import만 — [정보 없음]"]
                    for c in comps]))
    print()
    print("## API 호출 (파서 추출)")
    print()
    print(md_table(["엔드포인트", "메서드", "근거"],
                   [[f'`{a["endpoint"]}`', a["method"], f'`{a["source"]}`'] for a in apis]))
    print()
    print("## 비즈니스 상수 (파서 추출)")
    print()
    print(md_table(["상수", "값", "근거 파일"],
                   [[f'`{c["name"]}`', c["value"], f'`{c["source"]}`'] for c in consts]))
    print()
    print("## 검증/차단 규칙 (파서 추출)")
    print()
    print(md_table(["유형", "조건", "효과", "근거 파일"],
                   [[v["kind"], f'`{v["condition"]}`', v["effect"], f'`{v["source"]}`']
                    for v in vals]))
    print()
    print(f"<!-- 추출 통계: 라우트 {len(routes)} · 컴포넌트 {len(comps)} · "
          f"API {len(apis)} · 상수 {len(consts)} · 규칙 {len(vals)} -->")
    return 0


if __name__ == "__main__":
    sys.exit(main())
