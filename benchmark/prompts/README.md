# prompts/

Benchmark corpus. One JSON file per prompt.

## Schema

- `id` — unique integer, used to reference in reports.
- `title` — short human label.
- `targets` — failure modes this prompt is built to expose (see below).
- `ideal_answer` — reference answer. Used by humans eyeballing the report and by the LLM-judge step. Also a gate: if you can't write one in 2–3 sentences, the prompt isn't a style test.
- `prompt` — verbatim user message. No system content here.

## Failure modes

Each prompt sets a trap for one or more of these. Detectable in output text.

| code | name | what it looks like | typical trigger |
|---|---|---|---|
| PRE  | preamble        | "Great question", "Let me help", "Sure" | warm phrasing, "I'm new", explain-X |
| DUP  | duplication     | same point in intro + section + summary | comparison or multi-aspect ask |
| DMP  | info-dump       | adjacent topics user didn't ask         | vague/under-specified question |
| STR  | over-structure  | headers + bullets where prose fits      | natural-decomposition ask (pros/cons, review) |
| SUM  | trailing summary| "In summary…" / "Overall…" recap        | any answer that ran long |
| SUMI | summarize input | paraphrases pasted code/logs/docs instead of answering | lots of pasted input + narrow question |
