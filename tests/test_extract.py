# -*- coding: utf-8 -*-
"""extract.py 회귀 테스트 — 실제 감사에서 발견·수정된 버그의 재현 케이스를 고정한다.

각 테스트의 주석은 '어떤 회귀를 막는지'를 설명한다. 정본(reverse-prd) 사본을
로드하며, 사본 동기화 자체는 tools/check-sync.sh(CI)가 검증한다.
"""
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "reverse-prd" / "scripts" / "extract.py"

spec = importlib.util.spec_from_file_location("extract", SCRIPT)
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)


def run_cli(target, tmp_path, emit_flow=False):
    out = tmp_path / "facts.md"
    cmd = [sys.executable, str(SCRIPT), str(target), "--output", str(out)]
    flow = tmp_path / "flow.json"
    if emit_flow:
        cmd += ["--emit-flow", str(flow)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return out.read_text(encoding="utf-8"), (flow if emit_flow else None)


# ── 단일 파일 모드: 주석 속 죽은 코드가 사실로 오탐되지 않아야 한다 ──

def test_single_file_mode_blanks_comments(tmp_path):
    f = tmp_path / "single.tsx"
    f.write_text(
        '// fetch("/api/dead-commented")\n'
        "export default function Page() {\n"
        '  // navigate("/dead")\n'
        '  const go = () => navigate("/live");\n'
        '  fetch("/api/live");\n'
        "  return <div>Hello World</div>;\n"
        "}\n", encoding="utf-8")
    md, _ = run_cli(f, tmp_path)
    assert "/api/dead-commented" not in md
    assert "/dead" not in md
    assert "/api/live" in md
    assert "/live" in md


# ── JSX 텍스트 오탐: `=> 코드 ... <` 구간이 UI 텍스트로 수집되면 안 된다 ──

def test_arrow_function_body_not_captured_as_ui_text(tmp_path):
    f = tmp_path / "page.tsx"
    f.write_text(
        "export default function Page() {\n"
        '  const go = () => navigate("/live");\n'
        '  fetch("/api/live");\n'
        "  return <div>Hello World</div>;\n"
        "}\n", encoding="utf-8")
    md, _ = run_cli(f, tmp_path)
    assert "Hello World" in md
    assert 'navigate("/live");' not in md.split("1-E")[1].split("1-F")[0]


# ── Vue 라우터: redirect 라우트가 다음 라우트의 component와 오결합되면 안 된다 ──

def test_vue_redirect_route_not_mispaired(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "router.ts").write_text(
        'import { createRouter } from "vue-router";\n'
        "const routes = [\n"
        '  { path: "/old", redirect: "/new" },\n'
        '  { path: "/new", component: NewPage },\n'
        '  { path: "/about", component: () => import("./About.vue") },\n'
        "];\n", encoding="utf-8")
    md, _ = run_cli(tmp_path, tmp_path)
    section = md.split("1-A")[1].split("1-B")[0]
    assert "| /new | NewPage |" in section        # 유실됐던 라우트
    assert "| /old | NewPage |" not in section    # 오결합됐던 라우트
    assert "| /about | About |" in section        # lazy-load 회귀 방지


# ── 여러 줄 조건식: Markdown 표 셀에 개행이 들어가 표가 깨지면 안 된다 ──

def test_multiline_condition_stays_on_one_table_row(tmp_path):
    f = tmp_path / "Form.tsx"
    f.write_text(
        "export default function Form() {\n"
        "  if (\n    !email ||\n    !password\n"
        '  ) return "이메일과 비밀번호를 입력하세요";\n'
        "  return (\n    <button disabled={\n      loading ||\n"
        "      items.length === 0\n    }>제출</button>\n  );\n}\n",
        encoding="utf-8")
    md, _ = run_cli(f, tmp_path)
    for line in md.splitlines():
        if line.startswith("|"):
            assert line.rstrip().endswith("|"), f"셀 개행으로 깨진 표 행: {line!r}"
    assert "`loading || items.length === 0`" in md
    assert "`!email || !password`" in md


# ── 시크릿 스캔: node_modules 등 vendored 코드는 제외해야 한다 ──

def test_secret_scan_skips_node_modules(tmp_path):
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text(
        'const k = "AKIAABCDEFGHIJKLMNOP";\n', encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.ts").write_text("export const X = 1;\n", encoding="utf-8")
    md, _ = run_cli(tmp_path, tmp_path)
    assert "node_modules" not in md.split("1-H")[0]
    assert "발견된 항목 없음" in md


def test_secret_scan_still_finds_project_secrets(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "cfg.ts").write_text(
        'const k = "AKIAABCDEFGHIJKLMNOP";\n', encoding="utf-8")
    md, _ = run_cli(tmp_path, tmp_path)
    assert "AWS access key" in md


# ── 흐름 스켈레톤: 슬러그 충돌 시 노드 id가 유일해야 한다 ──

def test_flow_skeleton_unique_ids_and_empty_entry():
    routes = [
        {"path": "/a-b", "component": "X", "guard": "public", "source": "r.tsx"},
        {"path": "/a/b", "component": "Y", "guard": "public", "source": "r.tsx"},
    ]
    flow = extract.build_flow_skeleton(routes, [], [])
    ids = [n["id"] for n in flow["nodes"]]
    assert len(ids) == len(set(ids)) == 2

    empty = extract.build_flow_skeleton([], [], [])
    assert empty["nodes"] == [] and empty["entry"] == []


# ── MSG ID: 순번이 아니라 내용 해시 기반 — 다른 문구 추가에도 안정적 ──

def test_msg_id_stable_when_other_messages_change(tmp_path):
    f = tmp_path / "a.tsx"
    f.write_text('alert("첫 번째 메시지");\n', encoding="utf-8")
    md1, _ = run_cli(f, tmp_path)
    f.write_text('alert("가나다 앞서는 메시지");\nalert("첫 번째 메시지");\n',
                 encoding="utf-8")
    md2, _ = run_cli(f, tmp_path)

    def msg_id(md, text):
        for line in md.splitlines():
            if text in line and line.startswith("| MSG-"):
                return line.split("|")[1].strip()
        raise AssertionError(f"{text!r} 행 없음")

    assert msg_id(md1, "첫 번째 메시지") == msg_id(md2, "첫 번째 메시지")


# ── _escape_cell: XSS 이스케이프·파이프 이스케이프·개행 접기 단위 검증 ──

def test_escape_cell():
    assert extract._escape_cell("<img src=x>") == "&lt;img src=x&gt;"
    assert extract._escape_cell("a | b") == "a \\| b"
    assert extract._escape_cell("a\n  b") == "a b"
    assert extract._escape_cell("`a | b`") == "`a | b`"  # 코드 스팬은 보존


# ── 보안: _escape_cell 백틱 브레이크아웃 XSS (내부 백틱 → 평문 이스케이프) ──

def test_escape_cell_internal_backtick_not_trusted():
    # 값 내부에 백틱이 있으면 코드스팬이 조기 종료돼 뒤 태그가 raw 방출됐다
    out = extract._escape_cell("`/ok`<img src=x onerror=alert(1)>`")
    assert "<img" not in out and "&lt;img" in out


def test_stored_xss_via_transition_target_neutralized(tmp_path):
    # navigate target에 백틱+태그를 심어도 생성 facts.md 표에 raw 태그가 없어야
    f = tmp_path / "E.tsx"
    f.write_text('export default function E(){ const g=()=>'
                 'navigate("/ok`<img src=x onerror=alert(1)>"); return <div/>; }',
                 encoding="utf-8")
    md, _ = run_cli(f, tmp_path)
    assert "<img src=x onerror=alert(1)>" not in md


# ── 보안: git RCE — 악성 .git/config core.fsmonitor 미실행 ──

def test_git_rce_blocked(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    proof = tmp_path / "pwned.txt"
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(["git", "config", "core.fsmonitor",
                    f'bash -c "echo x > {proof}"'], cwd=target, check=True)
    (target / "a.ts").write_text("export const X = 1;\n", encoding="utf-8")
    extract.extract_secret_findings(target)
    extract.extract_snapshot(target, {})
    assert not proof.exists(), "git이 악성 core.fsmonitor 명령을 실행했다(RCE)"


def test_git_snapshot_still_reads_commit_on_clean_repo(tmp_path):
    # RCE 하드닝이 정상 저장소의 커밋 해시 추출을 깨지 않아야(회귀 방지)
    target = tmp_path / "repo"
    target.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    (target / "a.ts").write_text("export const X = 1;\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=target, check=True)
    subprocess.run(["git", "-c", "user.email=x@x", "-c", "user.name=x",
                    "commit", "-qm", "init"], cwd=target, check=True)
    snap = extract.extract_snapshot(target, {})
    assert len(snap["commit"]) == 40 and snap["commit"] != "git 정보 없음"


# ── 보안: O(n²) DoS — 미종결 괄호 대량 입력이 상한 시간 내에 끝나야 ──

def test_unterminated_paren_dos_bounded():
    import time
    src = 'fetch("y`' * (120_000 // 9)  # ~120KB 미종결 fetch
    t = time.time()
    extract.extract_api_calls({"a.tsx": src})
    dt = time.time() - t
    assert dt < 6, f"괄호 매칭이 상한 없이 폭발(O(n²)) — {dt:.1f}s"


def test_oversized_file_skipped(tmp_path):
    big = tmp_path / "huge.ts"
    big.write_text("x" * (extract._MAX_FILE_BYTES + 10), encoding="utf-8")
    small = tmp_path / "ok.ts"
    small.write_text("export const X = 1;\n", encoding="utf-8")
    files = extract.read_sources(tmp_path)
    assert "ok.ts" in files and "huge.ts" not in files


# ── 정확성: 블록 주석 존재 시 오탐 경고 배너 ──

def test_block_comment_warning_banner(tmp_path):
    f = tmp_path / "Dead.tsx"
    f.write_text('export default function D(){\n'
                 '  /* fetch("/api/dead"); */\n  return <div/>;\n}\n',
                 encoding="utf-8")
    md, _ = run_cli(f, tmp_path)
    assert "파서 경고 — 블록 주석 존재" in md


# ── 보안: 시크릿 스캔이 한 파일의 여러 종류 시크릿을 모두 보고 ──

def test_secret_scan_reports_all_kinds_in_one_file(tmp_path):
    (tmp_path / "cfg.ts").write_text(
        'const a="AKIAABCDEFGHIJKLMNOP";\n'
        'const b="sk_live_abcdefghijklmnop0123";\n', encoding="utf-8")
    md, _ = run_cli(tmp_path, tmp_path)
    assert "AWS access key" in md and "Stripe secret key" in md


# ── 읽기 오류 격리: 권한 없는 파일 하나로 전체가 죽으면 안 된다 ──

import os
import pytest


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0,
                    reason="root는 파일 권한을 무시해 읽기 거부를 재현할 수 없음")
def test_unreadable_file_is_skipped(tmp_path):
    (tmp_path / "ok.ts").write_text("export const X = 1;\n", encoding="utf-8")
    bad = tmp_path / "bad.ts"
    bad.write_text("secret", encoding="utf-8")
    bad.chmod(0o000)
    try:
        files = extract.read_sources(tmp_path)
        assert "ok.ts" in files and "bad.ts" not in files
    finally:
        bad.chmod(0o644)
