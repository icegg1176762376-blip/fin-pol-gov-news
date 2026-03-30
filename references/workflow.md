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

If `fetch-web.py` returns `status: "filtered_empty"` for a topic, do not treat that as a search backend failure. It means raw results were found but the hard freshness/date checks excluded them. Keyword rules are now soft signals for ranking and review, not hard rejection rules.

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

### 5. Enrich only the highest-value items

After merge, review the candidate set and enrich only the items that need deeper reading before commentary.

Use `scripts/summarize-merged.py` if the merged JSON is too large to inspect directly.

Use `scripts/enrich-articles.py` when the merged summary is insufficient and a few top items need more context from article body text.

Do not enrich everything by default. Use it selectively for:
- top policy items
- ambiguous but potentially important announcements
- articles where the title/snippet is too shallow to support commentary
- items whose title, source label, or attribution look incomplete and need article-body confirmation

### 6. Generate the report directly with AI

The default path is now:
- fetch
- merge
- enrich
- AI report synthesis

The agent should read the merged and enriched data, then write the actual report from scratch using the reference template in `references/report-template.md`.
For stricter execution rules around input fields, normalization, commentary, time display, and no-guessing behavior, follow `references/report-generation-spec.md`.

The agent, not a formatter script, is responsible for:
- choosing the lead items
- explaining why they matter
- compressing routine notices
- grouping related developments into themes
- preserving links and source attribution
- normalizing incomplete or awkward titles when the underlying article text supports a clearer title
- normalizing source names when the feed label is too short, noisy, or inconsistent
- filling in missing summaries from the available snippet or enriched article text
- flagging uncertainty instead of guessing when the source material is incomplete

Treat AI-generated normalization conservatively:
- do not invent facts that are not present in the source text
- do not upgrade weak signals into confirmed policy conclusions
- when title, date, or source attribution is ambiguous, say so explicitly

### 7. Prepare delivery outputs only after the report is done

Use:
- `scripts/sanitize-html.py` to convert markdown to safe HTML email
- `scripts/generate-pdf.py` to produce a PDF
- `scripts/send-email.py` to send the result

These are publishing tools, not analysis tools.

### 8. Preferred email delivery path

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

## Decision guide

- If the user asks for "what happened today" or "produce a brief": collect, review, merge, enrich the top items if needed, then write the report directly with AI.
- If the user asks "why is source X missing": validate config, fetch narrowly, inspect raw output, then merge only if needed.
- If the user asks to improve ranking or classification: inspect `merge-sources.py`, then test with saved outputs.
- If the user asks to change final format or distribution: focus first on `references/report-template.md`, then `sanitize-html.py`, `generate-pdf.py`, and `send-email.py`.
