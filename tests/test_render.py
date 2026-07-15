# -*- coding: utf-8 -*-
"""render.py 회귀 테스트 — HTML/DOCX 변환 버그의 재현 케이스.

markdown / python-docx 필요 (PDF·weasyprint는 네이티브 의존성이 있어 CI에서 제외).
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "reverse-prd" / "scripts" / "render.py"

spec = importlib.util.spec_from_file_location("render", SCRIPT)
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)

markdown = pytest.importorskip("markdown")
docx = pytest.importorskip("docx")


def docx_block_order(path):
    from docx import Document
    from docx.text.paragraph import Paragraph
    doc = Document(str(path))
    order = []
    for child in doc.element.body.iterchildren():
        if child.tag.endswith("tbl"):
            order.append("TABLE")
        elif child.tag.endswith("p"):
            p = Paragraph(child, doc)
            if p.text.strip():
                order.append(p.text.strip())
    return order


# ── 코드펜스 안 ~~는 보존, 밖은 <del> 변환 ──

def test_strikethrough_only_outside_code_fences():
    md = "밖 ~~취소~~ 텍스트\n\n```js\nconst a = x ~~ y; ~~strike~~\n```\n"
    h = render.build_html(md, "t", "#123456")
    fence = h[h.find("<pre"):h.find("</pre>")]
    assert "~~strike~~" in fence and "<del>" not in fence
    assert "<del>취소</del>" in h


# ── 제목: <title> 요소 존재 + HTML/CSS 문맥별 이스케이프 ──

def test_title_escaped_in_both_contexts():
    h = render.build_html("본문", 't"quote', "#123456")
    assert "<title>t&quot;quote</title>" in h
    assert 'content: "t\\"quote"' in h


def test_title_style_breakout_blocked():
    # 제목의 </style> 가 스타일 블록을 조기 종료시켜 스크립트를 주입하면 안 된다
    h = render.build_html("본문", "제목</style><script>alert(1)</script>", "#123456")
    head = h[:h.find("</head>")]
    assert "</style><script>alert(1)</script>" not in head


# ── DOCX: 표 직후 코드펜스가 와도 블록 순서가 유지돼야 한다 ──

def test_docx_table_before_adjacent_code_fence(tmp_path):
    md = ("| A | B |\n|---|---|\n| 1 | 2 |\n"
          "```js\ncode_after_table();\n```\n문단\n")
    out = tmp_path / "t.docx"
    render.render_docx(md, out, "t")
    order = docx_block_order(out)
    assert order.index("TABLE") < order.index("code_after_table();")


# ── DOCX: 닫히지 않은 코드펜스 내용이 유실되면 안 된다 ──

def test_docx_unterminated_fence_not_lost(tmp_path):
    md = "문단\n```\n미종결 펜스 내용"
    out = tmp_path / "t.docx"
    render.render_docx(md, out, "t")
    assert "미종결 펜스 내용" in docx_block_order(out)


# ── 표 셀 분리: 코드 스팬 안 파이프·이스케이프 파이프는 구분자가 아니다 ──

def test_split_table_row():
    assert render._split_table_row("| a | `x || y` | b |") == ["a", "`x || y`", "b"]
    assert render._split_table_row("| a \\| b | c |") == ["a | b", "c"]
    assert render._split_table_row("| ``a | b`` |") == ["``a | b``"]


# ── 인라인 정리: 마크다운 기호 제거 + HTML 엔티티 복원 ──

def test_clean_inline():
    assert render._clean_inline("**굵게** `코드` [링크](http://x) ~~취소~~") == \
        "굵게 코드 링크 취소"
    assert render._clean_inline("&lt;div&gt; &amp; \\|") == "<div> & |"
