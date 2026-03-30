# Workflow

## Goal

Run this repository as an AI-guided editorial system, not as a blind batch pipeline. The scripts prepare and transform data; the agent decides what to run, when to stop, and how to interpret the results.

## Default agent-first path

### 1. Validate or inspect configuration when needed

Use `scripts/validate-config.py` when:
- sources or topics were edited
- expected items are missing
- a new source/topic is being added

Read `scripts/config_loader.py` when the issue is about overlay behavior or precedence between defaults and user config.
Use `scripts/check-env.py` when API-backed scripts cannot see expected credentials from shell config, OpenClaw config, or `.env`.

Recommended setup:
- copy `.env.example` to `.env` in the project root
- fill in only the keys needed for your workflow
- run `python scripts/check-env.py` before debugging backend-specific failures

### 2. Collect only the needed raw candidates

Use `scripts/fetch-rss.py` when official feeds are the priority or when debugging source freshness and feed behavior.

Use `scripts/fetch-web.py` when search-based coverage is needed for topics that are not well covered by RSS.

Do not automatically run both if the task is narrow. Prefer targeted collection.

Save intermediate outputs explicitly, for example:

```bash
python scripts/fetch-rss.py --defaults config/defaults --hours 48 --output tmp/rss.json
python scripts/fetch-web.py --defaults config/defaults --freshness pd --output tmp/web.json
```

### 3. Pause for fetch review

Before merging, inspect what was actually collected.

Check for:
- sources with zero or obviously bad results
- topics with noise-heavy web matches
- gaps in expected coverage
- standout items worth following closely

Use `scripts/source-health.py` if the task involves reliability, drift, or repeated failures across runs.

### 4. Merge only when a unified candidate set is useful

Use `scripts/merge-sources.py` to:
- normalize fields
- score items
- deduplicate
- merge cross-source variants
- group by topic

Do not treat merge output as the final report. Treat it as a ranked candidate set for editorial review.

### 5. Pause for editorial review

After merge, the agent should decide:
- what the top developments are
- which items are routine notices rather than meaningful policy signals
- what themes connect the day's developments
- what deserves brief commentary or impact framing

Use `scripts/summarize-merged.py` if the merged JSON is too large to inspect directly.

### 6. Enrich only the highest-value items

Use `scripts/enrich-articles.py` when the merged summary is insufficient and a few top items need more context from article body text.

Do not enrich everything by default. Use it selectively for:
- top policy items
- ambiguous but potentially important announcements
- articles where the title/snippet is too shallow to support commentary

### 7. Draft the report with AI-led synthesis

The agent writes the real report. Scripts can help with formatting, but the agent must still:
- choose the lead items
- explain why they matter
- compress routine items
- preserve links and source attribution

Use `scripts/generate-report.py` only when its markdown structure helps as a starting point or output formatter. It should not replace editorial judgment.

### 8. Prepare delivery outputs only after the report is done

Use:
- `scripts/sanitize-html.py` to convert markdown to safe HTML email
- `scripts/generate-pdf.py` to produce a PDF
- `scripts/send-email.py` to send the result

These are publishing tools, not analysis tools.

### 9. Preferred email delivery path

When the user wants email delivery, the preferred path is:

1. Finalize the markdown brief.
2. Convert markdown to HTML with `scripts/sanitize-html.py`.
3. Optionally generate a PDF with `scripts/generate-pdf.py`.
4. Send the HTML body with `scripts/send-email.py`, preferably through Resend when configured.

Example:

```bash
python scripts/sanitize-html.py --input tmp/report.md --output tmp/report.html
python scripts/generate-pdf.py --input tmp/report.md --output tmp/report.pdf
python scripts/send-email.py --provider resend --to user@example.com --subject "金融政策日报" --html tmp/report.html --attach tmp/report.pdf
```

Without a PDF attachment:

```bash
python scripts/sanitize-html.py --input tmp/report.md --output tmp/report.html
python scripts/send-email.py --provider resend --to user@example.com --subject "金融政策日报" --html tmp/report.html
```

Resend configuration:
- set `RESEND_API_KEY` or pass `--resend-api-key`
- set `RESEND_FROM` or pass `--from`

## Legacy automation

`scripts/run-pipeline.py` still exists as a convenience wrapper for unattended or historical runs:
- fetch RSS
- fetch web
- merge
- write meta

Do not use it as the default skill path unless the user explicitly asks for one-command automation or scheduled batch behavior.

## Decision guide

- If the user asks for "what happened today" or "produce a brief": collect, review, merge, editorial review, report.
- If the user asks "why is source X missing": validate config, fetch narrowly, inspect raw output, then merge only if needed.
- If the user asks to improve ranking or classification: inspect `merge-sources.py`, then test with saved outputs.
- If the user asks to change final format or distribution: focus on `generate-report.py`, `sanitize-html.py`, `generate-pdf.py`, and `send-email.py`.
