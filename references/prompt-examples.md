# Prompt Examples

## Purpose

Use these examples as realistic task shapes for this skill. They show the intended agent behavior: choose only the needed scripts, pause for review, and let AI do the editorial work.

## 1. Daily brief from current sources

```text
Update today's finance-policy brief for Shenzhen, Beijing, Guangdong, PBC, and NFRA. Collect the most relevant items from the last 48 hours, review what was fetched, merge only the useful candidate sets, and write a concise brief that highlights what actually matters.
```

Expected behavior:
- validate config only if coverage looks suspicious
- fetch RSS and web as needed
- review raw results before merge
- merge into a candidate set
- selectively enrich only when top items need deeper reading
- use AI to prioritize, normalize, and comment
- produce markdown directly from merged and enriched data

## 2. Debug a missing source or weak coverage

```text
Check why Guangdong coverage is thin today. Inspect whether the issue is config, fetch behavior, or filtering. Show me what was collected before merge and explain what is actually going wrong.
```

Expected behavior:
- validate config
- inspect overlay behavior if relevant
- run targeted fetch rather than the whole workflow
- review raw outputs before merge
- explain the cause, not just the symptom

## 3. Merge review with AI commentary

```text
I already have rss.json and web.json. Merge them, then review the merged result like an editor. Tell me the top developments, what looks routine, and what deserves a one-sentence significance note.
```

Expected behavior:
- run `merge-sources.py`
- optionally run `summarize-merged.py`
- do not stop at merged output
- produce an editorial summary with prioritization and commentary

## 4. Deepen a few top items before writing

```text
Take the merged output, identify the 3 to 5 most important items, enrich only those with fuller text if needed, and then write a sharper brief with short commentary on why each one matters.
```

Expected behavior:
- inspect merged output first
- enrich selectively, not globally
- use enrichment to improve accuracy and commentary
- keep the final brief concise

## 5. Config change workflow

```text
I want to add a new official source and make sure it fits the current topic model. Validate the config, tell me any topic mapping issues, and explain what else should change before we use it in collection.
```

Expected behavior:
- run `validate-config.py`
- inspect `config_loader.py` behavior if overlays are involved
- explain required topic/source alignment
- avoid collection until config looks sound

## 6. Format and delivery workflow

```text
The markdown brief is final. Convert it into safe HTML for email, generate a PDF copy, and send it through Resend. Keep the reporting content unchanged.
```

Expected behavior:
- do not re-edit editorial content unless the user asks
- use `sanitize-html.py`, `generate-pdf.py`, and `send-email.py` as publishing tools
- prefer `send-email.py --provider resend` when Resend credentials are configured

## 7. Narrow institutional watch

```text
Only check the People's Bank of China and NFRA for the last 24 hours. I do not need a full daily brief, just the most relevant regulatory signals and a short interpretation.
```

Expected behavior:
- use the smallest possible collection path
- avoid unrelated regions or delivery steps
- emphasize regulatory signal over volume

## 8. Investigate ranking quality

```text
Review how merge scoring is surfacing stories today. Show me whether the highest-ranked items are actually the most important, and point out any cases where the scoring should not drive the editorial order.
```

Expected behavior:
- inspect `merge-sources.py`
- compare score-driven ordering with editorial significance
- explain mismatches clearly

## 9. Health and drift check

```text
Run a source health check on the latest RSS and web outputs, and tell me whether any sources or topic searches look unhealthy or noisy enough that we should adjust them.
```

Expected behavior:
- use `source-health.py`
- inspect source-level results
- recommend follow-up actions, not just counts

## 10. Avoid this pattern

Bad prompt shape:

```text
Run the whole pipeline and give me the output.
```

Why this is weak:
- it encourages blind automation
- it hides review checkpoints
- it under-specifies the editorial task

Preferred rewrite:

```text
Collect the latest candidate items, review what was fetched, merge the useful sets, and then write a concise finance-policy brief with commentary on the most important developments.
```
