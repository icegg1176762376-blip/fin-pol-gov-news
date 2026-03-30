# Script Catalog

## Collection and normalization

### `scripts/fetch-rss.py`

Use for official RSS and Atom collection.

Best for:
- official government or regulator feeds
- freshness debugging
- source-level troubleshooting

Outputs structured source results with article lists.

### `scripts/fetch-web.py`

Use for topic-based search coverage driven by `topics.json`.

Best for:
- filling gaps not covered by RSS
- search-driven monitoring
- checking query/filter quality

May use Tavily, Brave, or generate a search interface depending on environment.

### `scripts/merge-sources.py`

Use to build a unified candidate set across collected outputs.

Responsibilities:
- field normalization
- scoring
- previous-digest penalty
- sent-article filtering
- duplicate removal
- topic grouping

This is an analysis input, not the final editorial output.

### `scripts/enrich-articles.py`

Use to fetch fuller body text for a small number of high-value merged items.

Best for:
- deeper commentary
- resolving ambiguous snippets
- confirming whether a top-ranked item deserves prominence

## Inspection and debugging

### `scripts/summarize-merged.py`

Use when merged JSON is too large to inspect directly. Produces a compact human-readable summary for AI review.

### `scripts/source-health.py`

Use to monitor per-source reliability over time and spot chronically unhealthy inputs.

### `scripts/validate-config.py`

Use before or after editing source/topic configuration, or when coverage seems broken.

### `scripts/config_loader.py`

Read when the issue is about defaults versus user overlay behavior or why a source/topic did not resolve the way you expected.

## Reporting and publishing

### `scripts/generate-report.py`

Use to turn merged JSON into markdown when you want a structured draft or a project-native report format.

The agent should still decide the editorial angle and final emphasis.

### `scripts/sanitize-html.py`

Use to convert markdown into safe HTML for email delivery.

### `scripts/generate-pdf.py`

Use to turn markdown into a styled PDF.

### `scripts/send-email.py`

Use to send the final HTML email, optionally with a PDF attachment.

## Legacy wrapper

### `scripts/run-pipeline.py`

Use only when the user explicitly wants one-command automation, unattended execution, or backward-compatible behavior.

Not recommended as the default agent path because it reduces opportunities for AI review between stages.
