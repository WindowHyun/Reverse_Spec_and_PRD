# Skills — Reverse-Engineering Spec & PRD Generators

**English** · [한국어](README.ko.md)

A collection of [Claude Code](https://code.claude.com/docs) skills that statically
analyze finished frontend code (HTML/JS/TS/Vue/React) and reconstruct the planning
documents behind it ("reverse planning" / 역기획).

| Skill | Output | Core question | Primary readers |
|-------|--------|---------------|-----------------|
| [`reverse-spec`](reverse-spec/SKILL.md) | Reverse **policy spec** (rules/policy-centric) | "How does it behave?" | Dev · QA |
| [`reverse-prd`](reverse-prd/SKILL.md) | Reverse **PRD** (requirements/goal-centric) | "What was built and why?" | PM · Design |

Both skills share one code-parsing spec ([`reference.md`](reverse-prd/reference.md)) and one
document renderer ([`scripts/render.py`](reverse-prd/scripts/render.py)). Run both on the same
codebase to get a **PRD (why/what) + policy spec (how)** set.

---

## What a "skill" is here (and why it's portable)

Each skill is a `SKILL.md` instructions file plus three plain local Python scripts:

1. **`SKILL.md`** — the procedure (YAML frontmatter + Markdown), following a hybrid principle:
   *parsers extract the facts, the LLM writes only the interpretation*.
2. **`scripts/extract.py`** — deterministic fact extractor (routes, APIs, messages, state,
   integrations, snapshot — same code always yields the same fact tables).
3. **`scripts/flowgen.py`** — user-flow SVG generator (renders in both HTML and PDF).
4. **`scripts/render.py`** — Markdown → PDF+HTML pair (or DOCX) renderer.

That means the skill is **natively** a Claude Code Agent Skill, but the same `SKILL.md`
body works as a *custom prompt / custom command / rules file* in other AI tools, and the
scripts run from any shell. The setup recipes below show how to register it in each tool.

### Dependencies (for document rendering)

```bash
pip install weasyprint markdown python-docx
```

HTML output needs only `markdown`; PDF needs `weasyprint`; DOCX needs `python-docx`.
On macOS, use `python3`/`pip3` if `python`/`pip` don't exist.

**Platform note for PDF (WeasyPrint needs the native Pango library — pip alone is not enough):**

- **Windows**: install [MSYS2](https://www.msys2.org/), then in the MSYS2 UCRT64 shell run
  `pacman -S mingw-w64-ucrt-x86_64-pango`. (Official WeasyPrint guidance — see
  [installation docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).)
  If that's not an option, use `--format docx,html` instead of PDF.
- **macOS**: `brew install weasyprint` (pulls in Pango automatically).
- **Linux**: usually works after `pip install`; install `pango` via your package manager if not.

---

## Setup per tool

> Examples below install `reverse-prd`; repeat for `reverse-spec`.

### 1. Claude Code (terminal CLI) — native Agent Skill ✅

```bash
# Personal (all projects)
cp -r reverse-prd reverse-spec ~/.claude/skills/
# …or project-local (team-shared, committed to the repo)
mkdir -p .claude/skills && cp -r reverse-prd reverse-spec .claude/skills/
```

Invoke with `/reverse-prd`, or just ask in natural language ("make a reverse PRD from
`src/`") — Claude auto-loads it when your request matches the `description`. Skills are picked
up mid-session (no restart). The directory name becomes the command name.
Docs: <https://code.claude.com/docs/en/skills>

### 2. Claude CLI — same as Claude Code

There is no separate "Claude CLI" product: the terminal tool is **Claude Code**, run via the
`claude` command. Use the section 1 steps. (Don't confuse it with the Anthropic API SDK.)

### 3. Claude Desktop app — upload as a ZIP

The Claude chat app supports custom Skills, but via **upload**, not a folder on disk:

```bash
# macOS/Linux — zip the skill folder (it must contain SKILL.md)
cd reverse-prd && zip -r ../reverse-prd.zip . && cd ..
# Windows (PowerShell)
Compress-Archive -Path reverse-prd\* -DestinationPath reverse-prd.zip
```

Then in the app: **Settings → Capabilities → Skills → Upload skill**, and select the ZIP.
Requires a paid plan with code execution enabled. Note: in the desktop ZIP form the `name`
field is **required** (lowercase letters/numbers/hyphens, ≤64 chars, and it may not contain the
words "claude" or "anthropic"). To add MCP servers instead, use **Settings → Developer → Edit
Config** (`claude_desktop_config.json`).
Docs: <https://support.claude.com/en/articles/12512180-use-skills-in-claude>

### 4. OpenAI Codex CLI — custom prompt + helper script

Codex turns Markdown files in `~/.codex/prompts/` into slash commands:

```bash
mkdir -p ~/.codex/prompts
cp reverse-prd/SKILL.md ~/.codex/prompts/reverse-prd.md
```

Invoke with `/reverse-prd` in the Codex CLI or IDE extension. For always-on guidance instead,
put the procedure in an `AGENTS.md` at your repo root. Run the renderer directly from Codex's
shell: `python reverse-prd/scripts/render.py …`.
Heads-up: OpenAI marks custom prompts as **deprecated** in favor of Codex Skills — both still
work today. Docs: <https://developers.openai.com/codex/custom-prompts>

### 5. Gemini CLI (Google) — TOML custom command

Gemini custom commands are TOML files with a `prompt` field:

```bash
mkdir -p ~/.gemini/commands
cat > ~/.gemini/commands/reverse-prd.toml <<'EOF'
description = "Reverse-engineer a PRD from code, render to PDF/DOCX."
prompt = """
Follow this procedure to produce a reverse-engineering PRD from the target code.
Target path: {{args}}

<paste the body of reverse-prd/SKILL.md here, or summarize its steps>
Then render with: python reverse-prd/scripts/render.py --input <body.md> --format pdf
"""
EOF
```

Invoke with `/reverse-prd src/`. `{{args}}` receives whatever you type after the command.
For always-on context use `GEMINI.md`; for MCP use `~/.gemini/settings.json`.
Docs: <https://geminicli.com/docs/cli/custom-commands/>

### 6. Google Antigravity (agentic IDE) — Workflow (best match)

The closest thing to a slash-command skill is an Antigravity **Workflow**:

```bash
mkdir -p .agent/workflows
cp reverse-prd/SKILL.md .agent/workflows/reverse-prd.md
```

Invoke `/reverse-prd` in the Agent panel. Antigravity also has **Skills**
(commonly `.agent/skills/<name>/SKILL.md`, but the exact path varies across IDE/CLI and
versions — verify against your build), **Rules** (`GEMINI.md` / `AGENTS.md` / `.agent/rules/`),
and MCP config at `~/.gemini/config/mcp_config.json`.
Docs: <https://antigravity.google/docs/rules-workflows>

### Quick comparison

| Tool | Mechanism | Put the file at | Format | Invoke |
|------|-----------|-----------------|--------|--------|
| Claude Code | Agent Skill | `~/.claude/skills/<n>/SKILL.md` or `.claude/skills/<n>/SKILL.md` | YAML+MD | `/<n>` or auto |
| Claude CLI | = Claude Code | same | same | same |
| Claude Desktop | Skill (ZIP upload) | Settings → Capabilities → Skills | YAML+MD (zipped) | auto |
| Codex CLI | Custom prompt | `~/.codex/prompts/<n>.md` | MD | `/<n>` |
| Gemini CLI | Custom command | `~/.gemini/commands/<n>.toml` | TOML | `/<n>` |
| Antigravity | Workflow / Skill | `.agent/workflows/<n>.md` | MD | `/<n>` |

> **Gotchas.** Codex custom prompts are deprecated (use Codex Skills going forward).
> Antigravity skill directories differ across CLI vs IDE and versions — confirm your build's
> path. Claude Desktop Skills are per-user ZIP uploads, not synced to Claude Code or the API.
> For non-Claude tools, paste/adapt the `SKILL.md` body into that tool's prompt/command and run
> `render.py` from its shell.

---

## Usage (Claude Code)

```bash
/reverse-prd                          # analyze current dir, PDF output
/reverse-prd src/index.html           # a specific file
/reverse-prd src/ --format docx       # whole directory + Word output
/reverse-spec . --format pdf --lang en
```

Output lands in `./reverse-prd-output/` (or `reverse-spec-output/`). **Every run produces a
PDF + HTML pair by default** (same timestamp, e.g. `reverse_prd_….pdf` + `reverse_prd_….html`) —
the HTML opens instantly in a browser, the PDF is for sharing/printing. `--format docx,html`
swaps the PDF for Word.

---

## How it works

1. **Phase 1 — Parse (deterministic):** `scripts/extract.py` extracts facts — routes,
   components, API calls, constants, rules, transitions, user-facing strings, state usage,
   integrations/tracking, and an as-is snapshot (rules in
   [`reference.md`](reverse-prd/reference.md)). Same code → same facts, every run.
   Codebases over ~30 source files are split into modules and extracted via subagents.
2. **Phase 2 — Interpret (LLM):** infer flow / purpose / policy or requirements —
   grounded strictly in the extracted fact tables.
3. **Phase 3 — Compose:** lay content into the policy-spec or PRD outline;
   `scripts/flowgen.py` renders the user-flow SVG (visible in both HTML and PDF).
4. **Phase 4 — Render:** `scripts/render.py` converts Markdown → a **PDF + HTML pair**
   (or DOCX).

### Accuracy principles

Static analysis is honest about its limits:

- `[추정]` / *[assumed]* — intent, goals, background, personas with no direct code basis.
- `[정보 없음 — 별도 확인 필요]` / *[no info — verify separately]* — items absent from the
  code, including **components that are only imported but whose source isn't in scope**.
- Secrets (API keys/passwords) are never embedded in the document — only flagged as a warning.

---

## Repository layout

```
.
├── reverse-spec/            # reverse policy-spec skill
│   ├── SKILL.md
│   ├── reference.md         # shared code-parsing rules
│   └── scripts/             # extract.py (facts) · flowgen.py (flow SVG) · render.py (PDF/HTML/DOCX)
├── reverse-prd/             # reverse PRD skill (same structure)
│   ├── SKILL.md
│   ├── reference.md
│   └── scripts/
├── docs/
│   └── skill-mcp-review.md  # official-docs-based Skill/MCP compliance review
├── tools/
│   └── check-sync.sh        # verifies the shared-file copies are identical
└── examples/
    ├── mock-shop/           # demo mock e-commerce app (React Router)
    ├── reverse-prd-output/  # sample PRD from mock-shop (PDF+HTML pair, body md, flow JSON/SVG)
    ├── review-output/       # this review report rendered as a PDF+HTML pair
    └── hybrid-demo/         # hybrid-extraction proof of concept (determinism demo)
```

> `reference.md` and `scripts/render.py` are kept as **identical copies** in both skills (a
> skill can only reference files inside its own directory via `${CLAUDE_SKILL_DIR}`). Edit one,
> copy to the other, then verify with `bash tools/check-sync.sh` before committing.

---

## Current validation status

`extract.py`'s determinism is proven only on the bundled mock-shop example (hash-verified
across runs). It's regex-based, so file-based routing (Next.js/Nuxt), Vue `<script setup>`,
CSS-in-JS, and non-standard state patterns may be missed — see `reference.md` §1-I for the
built-in low-fact-count warning. The large-codebase split mode is written as a procedure but
hasn't been exercised on a real 30+ file project yet. Try it on your own codebase and sanity-check
the extraction stats before relying on it for anything beyond a first draft.

## See also

- Official-docs-based compliance review: [`docs/skill-mcp-review.md`](docs/skill-mcp-review.md)
- Sample output preview: `examples/reverse-prd-output/reverse_prd_mock-shop_sample.html`
