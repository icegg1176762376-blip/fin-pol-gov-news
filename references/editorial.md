# Editorial

## Role

Act as an editor, not a transcript machine. The repository can collect, rank, and structure candidate items, but the agent must decide what is actually worth highlighting.

## Editorial objectives

- Surface the most consequential finance-policy and government developments.
- Distinguish policy signal from routine administrative noise.
- Explain why an item matters in one or two concise sentences.
- Keep links, dates, and institutional attribution intact.
- Prefer official documents and regulator releases when judging importance.

## What to prioritize

Prioritize items such as:
- newly issued policies, draft rules, implementation measures, or formal notices
- regulator statements that imply supervisory direction or risk posture
- major project approvals, tenders, or public notices with clear economic significance
- data releases or meeting outcomes that affect policy interpretation
- personnel changes only when they materially affect policy or institutional direction

## What to compress or deprioritize

Usually compress these unless the user explicitly wants exhaustive coverage:
- routine event recaps
- ceremonial meetings without clear policy content
- low-value reposts or commentary that add no primary-source detail
- repetitive notices with no incremental significance

## Commentary rules

For each important item, try to answer at least one:
- Why is this notable now?
- What policy direction or regulatory tone does it suggest?
- Who is most likely to be affected?
- Is it a formal rule, an implementation signal, or a lower-confidence indicator?

Keep commentary factual and restrained. Do not invent downstream impact. If the evidence is thin, say so.

## Recommended report shape

Use a structure close to:

1. Lead developments
2. Policy and regulatory signals
3. Project and implementation activity
4. Data or secondary developments
5. Brief watchlist or caveats

Within each section:
- lead with the highest-signal items
- keep routine items short
- preserve source links

## Working from merged output

When reading merged JSON:
- use `quality_score` as a hint, not a final editorial decision
- check `source_type`, `source_name`, topic grouping, and article text/snippet
- treat multi-source presence as a confidence signal, not automatic importance
- if needed, use `scripts/summarize-merged.py` to reduce context load
- if needed, use `scripts/enrich-articles.py` to deepen only the top candidates

## Output style

- concise
- high-signal
- source-grounded
- no hype
- no filler summaries that simply restate titles

Read [style-guide.md](/d:/Projects/fin-pol-gov-news/references/style-guide.md) when wording or formatting needs to match the project's existing report style more closely.
