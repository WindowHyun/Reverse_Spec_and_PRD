# -*- coding: utf-8 -*-
"""flowgen.py 회귀 테스트 — 레이아웃 퇴화·크래시·중복 id 버그의 재현 케이스."""
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "reverse-prd" / "scripts" / "flowgen.py"

spec = importlib.util.spec_from_file_location("flowgen", SCRIPT)
flowgen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flowgen)


def svg_size(svg: str):
    m = re.search(r'viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"', svg)
    return float(m.group(1)), float(m.group(2))


# ── 도달 불가 노드가 노드당 한 컬럼씩 가로로 펼쳐지면 안 된다 ──

def test_detached_nodes_grouped_not_spread_horizontally():
    data = {
        "nodes": [{"id": i, "label": i} for i in ("home", "a", "b", "c", "d", "e")],
        "edges": [{"from": "home", "to": "a"}],
        "entry": ["home"],
    }
    w, h = svg_size(flowgen.build_svg(data))
    # 이전 버그: detached 4개가 각자 컬럼을 차지해 1656px 한 줄 SVG.
    # 수정 후: 진입 흐름 2컬럼 + detached 1컬럼 = 3컬럼 세로 적층.
    assert w < 1000, f"detached 노드가 가로로 펼쳐짐 (width={w})"
    assert h > 200, f"detached 노드가 세로로 적층되지 않음 (height={h})"


def test_detached_subgraph_keeps_left_to_right_flow():
    # detached 서브그래프(cart→checkout→orders)는 자체 좌→우 흐름을 가져야 한다
    data = {
        "nodes": [{"id": i, "label": i}
                  for i in ("home", "cart", "checkout", "orders")],
        "edges": [{"from": "cart", "to": "checkout"},
                  {"from": "checkout", "to": "orders"}],
        "entry": ["home"],
    }
    lay = flowgen.layout(data["nodes"], data["edges"], data["entry"])
    xs = {i: lay["pos"][i][0] for i in ("cart", "checkout", "orders")}
    assert xs["cart"] < xs["checkout"] < xs["orders"]


# ── 빈 nodes: ValueError 크래시가 아니라 명확한 에러로 종료해야 한다 ──

def test_empty_nodes_clean_error(tmp_path):
    f = tmp_path / "flow.json"
    f.write_text(json.dumps({"nodes": [], "edges": [], "entry": ["root"]}),
                 encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), "--input", str(f)],
                       capture_output=True, text=True)
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    assert "nodes가 비어" in r.stderr


# ── 중복 노드 id: 같은 좌표에 겹쳐 그리지 말고 첫 정의만 사용 ──

def test_duplicate_node_ids_deduped():
    data = {"nodes": [{"id": "a_b", "label": "/a-b"},
                      {"id": "a_b", "label": "/a/b"}],
            "edges": [], "entry": []}
    svg = flowgen.build_svg(data)
    assert svg.count("<rect") == 1


# ── 존재하지 않는 entry id로 전 노드가 detached 판정되면 안 된다 ──

def test_unknown_entry_id_falls_back():
    data = {"nodes": [{"id": "home", "label": "home"},
                      {"id": "next", "label": "next"}],
            "edges": [{"from": "home", "to": "next"}],
            "entry": ["typo_id"]}
    lay = flowgen.layout(data["nodes"], data["edges"], data["entry"])
    assert lay["pos"]["home"][0] < lay["pos"]["next"][0]


# ── 결정성: 같은 입력 → 같은 SVG ──

def test_deterministic_output():
    data = {"nodes": [{"id": "a", "label": "A", "guard": "login"},
                      {"id": "b", "label": "B"}],
            "edges": [{"from": "a", "to": "b", "label": "이동"}],
            "entry": ["a"]}
    assert flowgen.build_svg(data) == flowgen.build_svg(data)


# ── XSS: 라벨의 HTML 특수문자는 이스케이프돼야 한다 ──

def test_label_escaped():
    data = {"nodes": [{"id": "a", "label": '<script>"x"'}], "edges": []}
    svg = flowgen.build_svg(data)
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg
