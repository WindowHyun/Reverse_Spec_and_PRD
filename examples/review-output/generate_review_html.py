# -*- coding: utf-8 -*-
import markdown, pathlib

src = pathlib.Path("/home/user/Skills/docs/skill-mcp-review.md")
md = src.read_text(encoding="utf-8")
body = markdown.markdown(md, extensions=['tables', 'toc', 'fenced_code'])

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
  body {{ font-family: 'Noto Sans KR', sans-serif; font-size: 11pt; line-height: 1.8;
          color: #1a1a1a; max-width: 860px; margin: 0 auto; padding: 32px; background:#fff; }}
  h1 {{ font-size: 20pt; border-bottom: 2px solid #1f4e79; padding-bottom: 8px; margin-top: 40px; color: #1f4e79; }}
  h2 {{ font-size: 15pt; border-left: 4px solid #2e75b6; padding-left: 10px; margin-top: 30px; }}
  h3 {{ font-size: 12pt; color: #444; margin-top: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 10pt; }}
  th {{ background: #1f4e79; color: white; padding: 8px 12px; text-align: left; }}
  td {{ border: 1px solid #ccc; padding: 7px 12px; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #f4f8fc; }}
  code {{ background: #eef2f7; padding: 2px 5px; border-radius: 3px; font-size: 9.5pt; }}
  pre {{ background: #1e1e1e; color: #d4d4d4; padding: 14px; border-radius: 6px;
         font-size: 9pt; overflow-x: auto; }}
  pre code {{ background: transparent; color: inherit; padding: 0; }}
  blockquote {{ border-left: 4px solid #2e75b6; background:#f4f8fc; margin:16px 0; padding:8px 16px; color:#34495e; }}
  a {{ color: #1f4e79; }}
</style>
</head>
<body>
{body}
</body>
</html>"""

out = pathlib.Path("/home/user/Skills/examples/review-output")
out.mkdir(parents=True, exist_ok=True)
p = out / "skill_mcp_review_sample.html"
p.write_text(html, encoding="utf-8")
print(f"OK: {p}")
