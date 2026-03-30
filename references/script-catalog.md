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

When a topic returns `status: "filtered_empty"`, read its `diagnostics` block:
- `raw_results_total` shows whether search found anything
- `rejection_counts` shows why items failed hard date/freshness checks
- `keyword_signal_counts` shows how many accepted items matched positive or negative topic keywords
- `review_candidates` gives a small sample for AI inspection

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

### `scripts/check-env.py`

Use to confirm which API credentials are actually visible to the current Python process.

Best for:
- diagnosing why `fetch-web.py` cannot see search API keys
- diagnosing why `send-email.py` cannot see Resend credentials
- checking whether a project `.env` file is being loaded

Related file:
- `.env.example` shows the supported environment variable names

### `scripts/config_loader.py`

Read when the issue is about defaults versus user overlay behavior or why a source/topic did not resolve the way you expected.

## Reporting and publishing

### `scripts/sanitize-html.py`

Use to convert markdown into safe HTML for email delivery.

### `scripts/generate-pdf.py`

Use to turn markdown into a styled PDF.

### `scripts/send-email.py`

Use to send the final HTML email, optionally with a PDF attachment.

Preferred provider for this skill:
- `resend` when `RESEND_API_KEY` and sender configuration are available

Typical flow:
- `sanitize-html.py` converts markdown to HTML
- `generate-pdf.py` optionally creates an attachment
- `send-email.py --provider resend` sends the HTML body and optional PDF

