#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
유저플로우 SVG 생성기 (reverse-spec / reverse-prd 공용).

화면 전환 데이터(JSON)를 받아 인라인 SVG 흐름도를 출력한다.
- JS/외부 네트워크 불필요 → 브라우저(HTML)와 weasyprint(PDF) 모두에서 렌더링됨
- 같은 입력 JSON → 항상 같은 SVG (결정적)

입력 JSON 형식:
{
  "nodes": [
    {"id": "home", "label": "홈 /", "guard": "public"},
    {"id": "checkout", "label": "결제 /checkout", "guard": "login"},
    {"id": "admin", "label": "관리자 /admin", "guard": "admin"}
  ],
  "edges": [
    {"from": "home", "to": "products", "label": "탐색"},
    {"from": "cart", "to": "checkout", "label": "결제하기", "note": "빈 장바구니 차단"}
  ],
  "entry": ["home"]          // 선택: 진입점 (생략 시 in-degree 0인 노드)
}

guard 값: public(회색) | login(파랑) | admin(주황)

사용법:
  python flowgen.py --input flow.json --output flow.svg
  python flowgen.py --input flow.json >> body.md   (md에 직접 삽입)
"""
import argparse
import json
import pathlib
import sys

NODE_W, NODE_H = 168, 52
GAP_X, GAP_Y = 72, 36
PAD = 24

GUARD_STYLE = {
    "public": {"fill": "#f4f6f8", "stroke": "#8a97a3", "badge": ""},
    "login":  {"fill": "#e8f0fa", "stroke": "#2e75b6", "badge": "🔒"},
    "admin":  {"fill": "#fdf1e2", "stroke": "#c47a00", "badge": "🔒 admin"},
}


def layout(nodes: list, edges: list, entries: list) -> dict:
    """진입점부터 최장 경로 깊이 = 컬럼. 컬럼 내 순서는 JSON 정의 순서."""
    ids = [n["id"] for n in nodes]
    out_edges = {}
    indeg = {i: 0 for i in ids}
    for e in edges:
        out_edges.setdefault(e["from"], []).append(e["to"])
        if e["to"] in indeg:
            indeg[e["to"]] += 1
    if not entries:
        entries = [i for i in ids if indeg[i] == 0] or ids[:1]

    depth = {i: 0 for i in entries}
    # 최장 경로 깊이 (사이클 방지 위해 노드 수만큼만 완화)
    for _ in range(len(ids)):
        changed = False
        for e in edges:
            if e["from"] in depth:
                d = depth[e["from"]] + 1
                if d > depth.get(e["to"], -1) and d < len(ids):
                    depth[e["to"]] = d
                    changed = True
        if not changed:
            break
    for i in ids:
        depth.setdefault(i, 0)

    cols = {}
    for n in nodes:  # JSON 순서 유지 → 결정적
        cols.setdefault(depth[n["id"]], []).append(n["id"])

    pos = {}
    for c, members in cols.items():
        for r, nid in enumerate(members):
            x = PAD + c * (NODE_W + GAP_X)
            y = PAD + r * (NODE_H + GAP_Y)
            pos[nid] = (x, y)
    width = PAD * 2 + (max(cols) + 1) * (NODE_W + GAP_X) - GAP_X
    height = PAD * 2 + max(len(m) for m in cols.values()) * (NODE_H + GAP_Y) - GAP_Y
    return {"pos": pos, "width": width, "height": height}


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def build_svg(data: dict) -> str:
    nodes = data["nodes"]
    edges = data.get("edges", [])
    lay = layout(nodes, edges, data.get("entry", []))
    pos = lay["pos"]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lay["width"]} {lay["height"]}" '
        f'width="100%" style="max-width:{lay["width"]}px;font-family:\'Noto Sans KR\',sans-serif;">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#5a6672"/></marker></defs>',
    ]

    # 엣지 먼저 (노드 아래 깔리도록)
    for e in edges:
        if e["from"] not in pos or e["to"] not in pos:
            continue
        x1, y1 = pos[e["from"]]
        x2, y2 = pos[e["to"]]
        sy = y1 + NODE_H / 2
        ty = y2 + NODE_H / 2
        if x2 > x1:                       # 정방향: 오른쪽 → 왼쪽 변
            sx, tx = x1 + NODE_W, x2
            mx = (sx + tx) / 2
            path = f"M {sx} {sy} C {mx} {sy}, {mx} {ty}, {tx} {ty}"
            # 수평 이동은 선 위, 대각 이동은 곡선 중간 높이에 라벨 (수평 라벨과 겹침 방지)
            lx, ly = mx, (sy - 8) if sy == ty else (sy + ty) / 2 - 4
        elif x2 < x1:                     # 역방향(복귀): 아래로 우회
            sx, tx = x1 + NODE_W / 2, x2 + NODE_W / 2
            dy = max(y1, y2) + NODE_H + 18
            path = f"M {sx} {y1 + NODE_H} C {sx} {dy}, {tx} {dy}, {tx} {y2 + NODE_H}"
            lx, ly = (sx + tx) / 2, dy + 4
        else:                             # 같은 컬럼: 위/아래 직결
            sx = x1 + NODE_W / 2
            if ty > sy:
                path = f"M {sx} {y1 + NODE_H} L {sx} {y2}"
            else:
                path = f"M {sx} {y1} L {sx} {y2 + NODE_H}"
            lx, ly = sx + 6, (sy + ty) / 2
        dash = ' stroke-dasharray="5 4"' if e.get("dashed") else ""
        parts.append(f'<path d="{path}" fill="none" stroke="#5a6672" '
                     f'stroke-width="1.6" marker-end="url(#arrow)"{dash}/>')
        if e.get("label"):
            parts.append(f'<text x="{lx}" y="{ly}" font-size="11" fill="#41505c" '
                         f'text-anchor="middle">{esc(e["label"])}</text>')

    # 노드
    for n in nodes:
        x, y = pos[n["id"]]
        st = GUARD_STYLE.get(n.get("guard", "public"), GUARD_STYLE["public"])
        parts.append(f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" rx="8" '
                     f'fill="{st["fill"]}" stroke="{st["stroke"]}" stroke-width="1.6"/>')
        label = esc(n["label"])
        cy = y + NODE_H / 2
        if st["badge"]:
            parts.append(f'<text x="{x + NODE_W / 2}" y="{cy - 3}" font-size="12.5" '
                         f'font-weight="bold" fill="#22303c" text-anchor="middle">{label}</text>')
            parts.append(f'<text x="{x + NODE_W / 2}" y="{cy + 14}" font-size="10" '
                         f'fill="{st["stroke"]}" text-anchor="middle">{esc(st["badge"])}</text>')
        else:
            parts.append(f'<text x="{x + NODE_W / 2}" y="{cy + 4}" font-size="12.5" '
                         f'font-weight="bold" fill="#22303c" text-anchor="middle">{label}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="유저플로우 SVG 생성기")
    ap.add_argument("--input", required=True, help="흐름 정의 JSON 파일")
    ap.add_argument("--output", help="출력 SVG 경로 (생략 시 stdout)")
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
    svg = build_svg(data)
    if args.output:
        pathlib.Path(args.output).write_text(svg, encoding="utf-8")
        print(f"✅ SVG 생성 완료: {args.output}", file=sys.stderr)
    else:
        print(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
