---
name: fin-pol-gov-news
description: Collect, triage, analyze, and deliver China finance-policy and government news using this repository. Use when the user wants to monitor Shenzhen, Beijing, Guangdong, PBC, NFRA, or related official policy sources; inspect or improve the fetch/merge/report workflow; validate source/topic config; produce a daily brief with AI-written prioritization and commentary; or prepare markdown, HTML email, PDF, or sendable output from gathered results.
---

# Fin-Pol-Gov News

Use this skill to run an AI-led newsroom workflow. Do not default to a fully automated pipeline. Treat the scripts in this repo as tools the agent can call selectively while keeping editorial judgment in the loop.

## Default workflow

1. Clarify the task shape: collection, debugging, analysis, report generation, or delivery.
2. Validate config first when sources/topics may have changed.
3. Collect candidate items with only the scripts needed for the task.
4. Review intermediate outputs before merging or reporting.
5. Merge and normalize only when a unified candidate set is useful.
6. Let AI prioritize, synthesize, and comment on significance before producing the final report.
7. Generate markdown, HTML, PDF, or email only after editorial review.

## Hard rules

- Do not treat `scripts/run-pipeline.py` as the default entrypoint. It is a legacy automation shortcut, not the preferred agent workflow.
- Do not mechanically mirror every merged item into the final report.
- Always add human-meaningful prioritization: what matters, why it matters, and what can be deprioritized.
- Prefer official government or regulator sources when weighing significance.
- Keep original links and note uncertainty when classification or impact is ambiguous.

## Task routing

- For end-to-end agent workflow, read [workflow.md](/d:/Projects/fin-pol-gov-news/references/workflow.md).
- For how to write summaries, significance notes, and policy commentary, read [editorial.md](/d:/Projects/fin-pol-gov-news/references/editorial.md).
- For which script to use for which task, read [script-catalog.md](/d:/Projects/fin-pol-gov-news/references/script-catalog.md).
- For concrete triggering examples and anti-examples, read [trigger-examples.md](/d:/Projects/fin-pol-gov-news/references/trigger-examples.md).
- For realistic user-task phrasings and preferred agent behavior, read [prompt-examples.md](/d:/Projects/fin-pol-gov-news/references/prompt-examples.md).
- For wording and formatting norms in the final brief, read [style-guide.md](/d:/Projects/fin-pol-gov-news/references/style-guide.md).

## Expected behavior

- Start from the smallest useful step instead of running everything.
- Pause after fetch and after merge to inspect outputs.
- Use `scripts/summarize-merged.py` to shrink large merged JSON before reasoning when helpful.
- Use `scripts/enrich-articles.py` only for high-value items that need deeper reading.
- Use delivery scripts only after the markdown report is editorially complete.
- Prefer the delivery chain `sanitize-html.py` -> optional `generate-pdf.py` -> `send-email.py --provider resend` when the user wants email distribution.
