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
MAX_NODES = 60  # 과밀/거대 SVG 방지 — 초과 시 잘라내고 stderr에 경고

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
    # 존재하지 않는 id가 entry로 들어오면(오타 등) 전 노드가 도달 불가 판정을
    # 받아 레이아웃이 퇴화하므로, 실제 노드만 남기고 없으면 in-degree 0으로 폴백.
    entries = [i for i in entries if i in indeg]
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
    # 렌더링 검증 발견: 어떤 진입점으로도 도달 불가능한 고립 노드(외부와 끊긴
    # 사이클 등)를 depth 0으로 두면 실제 진입 화면과 같은 컬럼에 섞여, '섬'인데
    # 진입점처럼 보였다. 구조 재점검 추가 발견: 이전 구현은 도달 못한 노드를
    # "노드당 한 컬럼씩" 가로로 펼쳐(offset을 depth에 더함), detached 노드가
    # 많으면 한 줄짜리 초광폭 SVG가 됐다(동봉 mock-shop 스켈레톤만으로 2136px).
    # 수정: detached 서브그래프도 in-degree 0 노드를 시드로 같은 완화를 돌려
    # 자체 좌→우 흐름을 만들고, 시드가 없는 순수 사이클은 기준 컬럼에 모은다.
    unreached = [i for i in ids if i not in depth]
    if unreached:
        base = max(depth.values()) + 2 if depth else 0  # 진입 흐름과 한 컬럼 띄움
        unreached_set = set(unreached)
        for i in unreached:
            if indeg[i] == 0:
                depth[i] = base
        if not any(i in depth for i in unreached):
            depth[unreached[0]] = base  # 순수 사이클뿐이면 첫 노드를 시드로
        for _ in range(len(unreached)):
            changed = False
            for e in edges:
                if e["from"] in depth and e["to"] in unreached_set:
                    d = depth[e["from"]] + 1
                    if d > depth.get(e["to"], -1) and d < base + len(ids):
                        depth[e["to"]] = d
                        changed = True
            if not changed:
                break
        for i in unreached:
            depth.setdefault(i, base)

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
    # 중복 id는 같은 좌표에 겹쳐 그려지므로 첫 정의만 사용 (구조 재점검 발견)
    seen_ids, deduped = set(), []
    for n in nodes:
        if n["id"] in seen_ids:
            print(f"⚠️  중복 노드 id '{n['id']}' — 첫 정의만 사용", file=sys.stderr)
            continue
        seen_ids.add(n["id"])
        deduped.append(n)
    nodes = deduped
    if len(nodes) > MAX_NODES:
        print(f"⚠️  노드 {len(nodes)}개 중 {MAX_NODES}개만 표시 (과밀 방지) — "
              f"전체 목록은 사실 표(_facts.md)를 참조", file=sys.stderr)
        kept_ids = {n["id"] for n in nodes[:MAX_NODES]}
        nodes = nodes[:MAX_NODES]
        edges = [e for e in edges if e["from"] in kept_ids and e["to"] in kept_ids]
    lay = layout(nodes, edges, data.get("entry", []))
    pos = lay["pos"]

    # 엣지 지오메트리를 먼저 계산해 역방향(복귀) 우회 경로가 실제로 필요로 하는
    # 최대 y좌표를 구한다 — 이전에는 이 여유 공간을 고려하지 않고 컬럼 크기만으로
    # viewBox 높이를 정해, 노드가 많으면 우회 경로가 캔버스 밖으로 잘릴 수 있었다.
    edge_parts = []
    max_y_needed = lay["height"]
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
            max_y_needed = max(max_y_needed, dy + 16)
        else:                             # 같은 컬럼: 위/아래 직결
            sx = x1 + NODE_W / 2
            if ty > sy:
                path = f"M {sx} {y1 + NODE_H} L {sx} {y2}"
            else:
                path = f"M {sx} {y1} L {sx} {y2 + NODE_H}"
            lx, ly = sx + 6, (sy + ty) / 2
        dash = ' stroke-dasharray="5 4"' if e.get("dashed") else ""
        edge_parts.append(
            f'<path d="{path}" fill="none" stroke="#5a6672" '
            f'stroke-width="1.6" marker-end="url(#arrow)"{dash}/>')
        if e.get("label"):
            edge_parts.append(f'<text x="{lx}" y="{ly}" font-size="11" fill="#41505c" '
                              f'text-anchor="middle">{esc(e["label"])}</text>')

    height = max_y_needed
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {lay["width"]} {height}" '
        f'width="100%" style="max-width:{lay["width"]}px;font-family:\'Noto Sans KR\',sans-serif;">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#5a6672"/></marker></defs>',
    ]
    parts.extend(edge_parts)  # 엣지 먼저 (노드 아래 깔리도록)

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
    if not data.get("nodes"):
        # 구조 재점검 발견: 빈 nodes로 layout()의 max()가 ValueError로 죽었다.
        # extract.py는 라우트 0개여도 --emit-flow 시 빈 스켈레톤을 만들 수 있다.
        print("❌ nodes가 비어 있습니다 — 라우트가 추출되지 않아 흐름도를 만들 수 "
              "없습니다. flow.json에 노드를 채운 뒤 다시 실행하세요.", file=sys.stderr)
        return 1
    svg = build_svg(data)
    if args.output:
        # extract.py와 동일 이유로 출력 디렉토리를 생성한다(절차 첫 호출 크래시 방지).
        out_path = pathlib.Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(svg, encoding="utf-8")
        print(f"✅ SVG 생성 완료: {args.output}", file=sys.stderr)
    else:
        print(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
