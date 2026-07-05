#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
역기획 문서 렌더러 (reverse-spec / reverse-prd 공용)

Claude가 Step 1~3에서 구성한 Markdown 본문을 받아 PDF 또는 DOCX로 출력한다.
스킬 본문에 Python을 인라인하지 않고 이 스크립트를 호출하므로,
allowed-tools 를 `Bash(python ${CLAUDE_SKILL_DIR}/scripts/*)` 로 좁힐 수 있다.

사용법:
  python render.py --input doc.md --title "역기획 PRD" --outdir reverse-prd-output          # PDF+HTML 세트(기본)
  python render.py --input doc.md --format docx,html --title "역기획 정책서" --outdir out   # DOCX+HTML

옵션:
  --input   구성된 Markdown 본문 파일 경로 (필수)
  --format  쉼표 구분 다중 지정: pdf,html(기본) | docx | html 조합
  --title   문서 머리말/제목          (기본 "역기획 문서")
  --accent  강조색 hex                (기본 #1f4e79)
  --outdir  출력 디렉토리             (기본 reverse-spec-output)
  --name    파일명 접두어             (기본 reverse_spec)
  --lang    HTML/PDF lang 속성        (기본 ko; 영문 문서는 en)
"""
import argparse
import datetime
import pathlib
import re
import sys


def build_html(md_text: str, title: str, accent: str, lang: str = "ko") -> str:
    import markdown
    body = markdown.markdown(md_text, extensions=["tables", "toc", "fenced_code"])
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
  body {{ font-family: 'Noto Sans KR', sans-serif; font-size: 11pt; line-height: 1.8;
          color: #1a1a1a; margin: 0; padding: 0; }}
  h1 {{ font-size: 20pt; border-bottom: 2px solid {accent}; padding-bottom: 8px;
        margin-top: 40px; color: {accent}; }}
  h2 {{ font-size: 15pt; border-left: 4px solid {accent}; padding-left: 10px; margin-top: 30px; }}
  h3 {{ font-size: 12pt; color: #444; margin-top: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 10pt; }}
  th {{ background: {accent}; color: white; padding: 8px 12px; text-align: left; }}
  td {{ border: 1px solid #ccc; padding: 7px 12px; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #f5f7fa; }}
  code {{ background: #eef2f7; padding: 2px 5px; border-radius: 3px; font-size: 9.5pt; }}
  pre {{ background: #1e1e1e; color: #d4d4d4; padding: 14px; border-radius: 6px;
         font-size: 9pt; overflow-x: auto; }}
  pre code {{ background: transparent; color: inherit; padding: 0; }}
  blockquote {{ border-left: 4px solid #c47a00; background:#fff8ec; margin:16px 0;
               padding:8px 16px; color:#7a5200; }}
  /* 브라우저 화면 전용 여백 — weasyprint(PDF)는 print 매체라 무시하고 @page 여백을 쓴다 */
  @media screen {{
    body {{ max-width: 860px; margin: 0 auto; padding: 32px 24px; }}
  }}
  @page {{
    size: A4;
    margin: 20mm 18mm 20mm 20mm;
    @top-center {{ content: "{title}"; font-size: 9pt; color: #888; }}
    @bottom-right {{ content: counter(page) " / " counter(pages); font-size: 9pt; color: #888; }}
  }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def render_pdf(md_text: str, out_path: pathlib.Path, title: str, accent: str, lang: str) -> None:
    from weasyprint import HTML
    HTML(string=build_html(md_text, title, accent, lang)).write_pdf(str(out_path))


def render_html(md_text: str, out_path: pathlib.Path, title: str, accent: str, lang: str) -> None:
    # 미리보기/디버그용 정적 HTML (A4 @page 규칙은 브라우저에서 무시됨)
    out_path.write_text(build_html(md_text, title, accent, lang), encoding="utf-8")


_INLINE = re.compile(r"\*\*(.+?)\*\*|`(.+?)`")


def _clean_inline(text: str) -> str:
    """docx 평문용: **bold**/`code` 마크업 기호를 제거하고, 이스케이프된
    파이프(\\|)를 리터럴 |로 되돌린다 (extract.py의 _escape_cell과 짝을 이룸)."""
    text = _INLINE.sub(lambda m: m.group(1) or m.group(2), text)
    return text.replace("\\|", "|")


def _split_table_row(line: str) -> list:
    """GFM 파이프 테이블 행을 셀로 분리한다. 백틱(코드 스팬) 안의 파이프와
    백슬래시로 이스케이프된 파이프(\\|)는 구분자로 보지 않는다 — 기존의 단순
    line.split("|")는 이 두 경우를 무시해 JS `a || b` 같은 조건문이 들어간
    셀에서 뒤 컬럼(근거 파일 등)이 통째로 사라지는 버그가 있었다 (실전 검증 발견)."""
    cells, buf, in_backtick, i = [], [], False, 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if ch == "`":
            in_backtick = not in_backtick
            buf.append(ch)
        elif ch == "|" and not in_backtick:
            cells.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf))
    # 라인이 "| a | b |" 형태면 앞뒤 빈 셀(선행/후행 |)이 생기므로 제거
    stripped = line.strip()
    if stripped.startswith("|") and cells and cells[0].strip() == "":
        cells = cells[1:]
    if stripped.endswith("|") and cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [c.strip() for c in cells]


def render_docx(md_text: str, out_path: pathlib.Path, title: str) -> None:
    from docx import Document
    from docx.shared import Cm

    doc = Document()
    doc.core_properties.title = title
    sec = doc.sections[0]
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(2.0)

    # PDF의 @top-center 머리말과 동일하게 페이지 헤더에 문서 제목 표시
    header_p = sec.header.paragraphs[0]
    header_p.text = title
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    header_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    lines = md_text.splitlines()
    i = 0
    in_code = False
    code_buf: list[str] = []
    table_buf: list[str] = []

    def flush_table() -> None:
        # GFM 파이프 테이블: 2번째 행이 |---| 구분선
        rows = [r for r in table_buf if r.strip()]
        if len(rows) >= 2:
            header = _split_table_row(rows[0])
            data = [_split_table_row(r) for r in rows[2:]]
            t = doc.add_table(rows=1 + len(data), cols=len(header))
            t.style = "Table Grid"
            for j, h in enumerate(header):
                cell = t.rows[0].cells[j]
                cell.text = _clean_inline(h)
                if cell.paragraphs[0].runs:
                    cell.paragraphs[0].runs[0].bold = True
            for r_idx, row in enumerate(data):
                for j in range(len(header)):
                    val = row[j] if j < len(row) else ""
                    t.rows[r_idx + 1].cells[j].text = _clean_inline(val)
        table_buf.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 코드 펜스
        if stripped.startswith("```"):
            if in_code:
                doc.add_paragraph("\n".join(code_buf), style="Intense Quote")
                code_buf.clear()
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # 테이블 누적
        if stripped.startswith("|"):
            table_buf.append(line)
            i += 1
            continue
        elif table_buf:
            flush_table()

        if not stripped:
            i += 1
            continue

        # 헤딩
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            doc.add_heading(_clean_inline(m.group(2)), level=min(level, 4))
            i += 1
            continue

        # 인용
        if stripped.startswith(">"):
            p = doc.add_paragraph(_clean_inline(stripped.lstrip("> ").rstrip()))
            p.style = "Quote"
            i += 1
            continue

        # 불릿/체크리스트
        if re.match(r"^[-*]\s+", stripped):
            text = re.sub(r"^[-*]\s+", "", stripped)
            doc.add_paragraph(_clean_inline(text), style="List Bullet")
            i += 1
            continue

        # 일반 문단
        doc.add_paragraph(_clean_inline(stripped))
        i += 1

    if table_buf:
        flush_table()

    doc.save(str(out_path))


def main() -> int:
    ap = argparse.ArgumentParser(description="역기획 문서 렌더러 (pdf/docx/html)")
    ap.add_argument("--input", required=True, help="구성된 Markdown 본문 파일")
    ap.add_argument("--format", default="pdf,html",
                    help="쉼표 구분 다중 지정 가능: pdf,html(기본) / docx,html / pdf 등")
    ap.add_argument("--title", default="역기획 문서")
    ap.add_argument("--accent", default="#1f4e79")
    ap.add_argument("--outdir", default="reverse-spec-output")
    ap.add_argument("--name", default="reverse_spec")
    ap.add_argument("--lang", default="ko", help="HTML/PDF lang 속성 (ko|en 등)")
    args = ap.parse_args()

    formats = [f.strip() for f in args.format.split(",") if f.strip()]
    invalid = [f for f in formats if f not in ("pdf", "docx", "html")]
    if invalid:
        print(f"❌ 지원하지 않는 형식: {', '.join(invalid)} (pdf|docx|html)", file=sys.stderr)
        return 1

    md_text = pathlib.Path(args.input).read_text(encoding="utf-8")
    out_dir = pathlib.Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    for fmt in formats:  # 같은 타임스탬프로 세트 생성 (예: _104205.pdf + _104205.html)
        out_path = out_dir / f"{args.name}_{ts}.{fmt}"
        if fmt == "pdf":
            render_pdf(md_text, out_path, args.title, args.accent, args.lang)
        elif fmt == "docx":
            render_docx(md_text, out_path, args.title)
        else:
            render_html(md_text, out_path, args.title, args.accent, args.lang)
        print(f"✅ {fmt.upper()} 생성 완료: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
