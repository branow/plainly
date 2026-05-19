# styles/

Each `*.md` file is a system prompt under test. The runner sends the file's contents as the `system` field of the API call. Empty file = no system prompt.

## Styles

### `baseline.md`

Empty. Control — no system prompt. Whatever the model produces with its built-in defaults.

### `drona.md`

Source: [drona23/claude-token-efficient](https://github.com/drona23/claude-token-efficient) — `CLAUDE.md`.
Repo URL: <https://github.com/drona23/claude-token-efficient/blob/main/CLAUDE.md>

7-line `CLAUDE.md` config aimed at terse responses on heavy workflows. Gentle nudge — no sycophantic openers, no emojis, "thorough in reasoning, concise in output", verify before asserting. Smallest intervention in the set.

Verbatim copy of upstream, no edits.

### `ntcoding.md`

Source: [NTCoding/claude-skillz](https://github.com/NTCoding/claude-skillz) — `concise-output/SKILL.md`.
Repo URL: <https://github.com/NTCoding/claude-skillz/tree/main/concise-output>
Directory listing: <https://claude-plugins.dev/skills/@NTCoding/claude-skillz/concise-output>

Claude Code skill targeting signal-over-noise. Rules split between documentation and conversational output. Includes four verbose-vs-concise before/after examples baked into the prompt as in-context training. Carves out *when detail is appropriate* (error analysis, debugging, teaching trade-offs) versus *when brevity is mandatory* (READMEs, commit messages, plans, status updates).

Verbatim copy of upstream `SKILL.md` including YAML frontmatter, no edits.

### `plainly.md`

This project. Three core moves:

1. **Slack-colleague framing.** "You answer a senior engineer on Slack" — sets voice and brevity expectations.
2. **First sentence IS the answer.** Inverted-pyramid news rule. No preamble, no lead-in.
3. **Hard ceiling: 4 sentences for chat.** Exceptions carved for depth requests, structured artifacts (review/proposal/doc), multi-source comparison, and multi-file code.

Plus language-agnostic code carve-outs (multi-file split, rules-as-data, no banners, no demo blocks) and explicit bans (no emojis anywhere, no bold-as-header in chat).

Iterated through many benchmark-driven revisions. Length-budget framing grounded in:

- [How Users Read on the Web](https://www.nngroup.com/articles/how-users-read-on-the-web/) — NN/g
- [Applying Writing Guidelines to Web Pages](https://www.nngroup.com/articles/applying-writing-guidelines-web-pages/) — NN/g
- [AI Chatbot Response Length Limits](https://aerochat.ai/blog/ai-chatbot-response-length-limits) — AeroChat

### `caveman.md`

Source: [JuliusBrussee/caveman](https://github.com/juliusbrussee/caveman) — Claude Code plugin.
Plugin SKILL: <https://github.com/juliusbrussee/caveman/blob/main/plugins/caveman/skills/caveman/SKILL.md>
Activate hook: <https://github.com/juliusbrussee/caveman/blob/main/src/hooks/caveman-activate.js>
Per-prompt hook: <https://github.com/juliusbrussee/caveman/blob/main/src/hooks/caveman-mode-tracker.js>

Reconstructed from what the caveman plugin actually injects when `level=full`. Two parts merged into one file:

1. Lines 1-52 — the **SessionStart** output from `caveman-activate.js`: SKILL.md body with YAML frontmatter stripped, the intensity table filtered to keep only the `full` row, and example lines filtered to keep only the `full:` entry. Exactly what the plugin writes once per session.
2. Line 55 — the **UserPromptSubmit additionalContext** from `caveman-mode-tracker.js`, the short reinforcement the plugin re-appends on every user prompt.

Mechanism: grammar transformation — drop articles, fragments OK, "talk like caveman". Distinct from the other two anti-verbose styles.

Caveat: in real Claude Code the SessionStart text lands as a SystemReminder and the per-prompt text is appended to each user message. Our single-shot API call collapses both into the system-prompt slot. Same text, different position. Closest fair approximation for a system-prompt-only benchmark.

## Adding a new style

Drop a new `*.md` file in this directory. The filename stem is the style id (`uv run run-bench --styles your-style`). The runner picks it up automatically; no code change needed.

If the file is sourced from elsewhere, add an entry here with the upstream URL and a one-line description of its mechanism, so future readers know where it came from.
