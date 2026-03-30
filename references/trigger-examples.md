# Trigger Examples

## Should trigger this skill

- "Update today's Shenzhen, Beijing, Guangdong, PBC, and NFRA policy brief."
- "Collect the last 48 hours of official finance-policy news and tell me what actually matters."
- "Why did the Guangdong sources return so little content today?"
- "Merge the current RSS and web results, then write a concise editor-style summary."
- "Validate the source/topic config before I add a new regulator source."
- "Turn the finished markdown brief into email HTML and a PDF."
- "Send the final daily brief after converting it to HTML."

## Usually should not trigger this skill

- "Explain how Python defaultdict works."
- "Refactor this unrelated Flask route."
- "Translate this paragraph into English."
- "Write a generic summary of a document I already pasted here."

## Preferred execution pattern after triggering

1. Decide whether the task is collection, debugging, editorial analysis, or delivery.
2. Run only the scripts needed for that task.
3. Pause after fetch and after merge.
4. Use AI to prioritize and comment before producing final output.
