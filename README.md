# plainly

**An Output Style for Claude Code that makes Claude write for the human reading it.**

```
/plugin marketplace add branow/plainly
/plugin install plainly@plainly-marketplace
```

---

## The problem

LLM output isn't just wordy. It's *structurally* bloated. Claude restates your question, paraphrases the code you pasted, writes a 500-word answer to a one-line question, ends with a "summary" recap of what you just read. The default response is written as if no human will read it.

"Be concise" doesn't fix this. The problem isn't word choice — it's information architecture.

---

## Before / after

> **Prompt:** *Can you tell me what caused this deploy to fail?* (plus a 12-line deploy log showing pods crashing on Redis `ECONNREFUSED`, with the offending NetworkPolicy change already flagged in the log)

**Default Claude Code** — 155 words:

> The deploy failed because a **NetworkPolicy change blocked Redis access**.
>
> Specifically:
>
> 1. The `api-gateway` pods crashed immediately on startup with `ECONNREFUSED` trying to reach `redis-primary.cache.svc.cluster.local:6379`.
> 2. The root cause was a NetworkPolicy change — `api-gateway-egress` was updated ~14 minutes before the deploy by `@marek` (commit `8e2a1f3`), which **removed the egress rule that allowed port 6379 traffic to the `cache` namespace**.
> 3. Without that rule, the pods couldn't reach Redis and crashed in a `CrashLoopBackOff` loop.
>
> The deploy system auto-rolled back to `v4.18.1`, which would have restored connectivity since the NetworkPolicy change is unrelated to the app version — but the underlying policy change is still in place and will affect any future deploys until it's fixed.
>
> **To fix:** Restore the egress rule for port 6379 to the `cache` namespace in the `api-gateway-egress` NetworkPolicy, or coordinate with `@marek` to understand if the removal was intentional (and if so, update the app to not depend on Redis).

**plainly** — 58 words:

> The deploy failed because @marek's NetworkPolicy change (commit `8e2a1f3`, 14 min before deploy) removed the egress rule that allowed the api-gateway pods to reach Redis on port 6379, so every pod crashed on startup trying to connect to `redis-primary.cache.svc.cluster.local:6379`.
>
> Fix is to restore the egress rule in `api-gateway-egress` permitting TCP 6379 to the `cache` namespace, then redeploy v4.18.2.

Same root cause, same fix, **63% fewer words**. No restated question. No numbered tour of what you can read off the log yourself. No "to fix" header. The first sentence is the answer.

---

## What plainly does

Three rules carry most of the weight:

- **Slack-colleague framing.** "You answer a senior engineer on Slack" sets the voice. Colleagues don't write whitepapers.
- **The first sentence IS the answer.** Inverted-pyramid news rule. No preamble, no lead-in, no setup. Sentence one resolves the question.
- **4-sentence ceiling for chat replies.** Hard cap, with carved exceptions for depth requests, structured artifacts (review/proposal/doc), multi-source comparisons, and code.

Plus a short list of structural rules: no decorative comment banners in code, no demo/test blocks the spec didn't ask for, no emojis anywhere, no bold-as-header in chat.

---

## Proof — benchmark

Tested against four alternative styles (`baseline` = no system prompt, plus the three most-recommended community styles) on a 10-prompt corpus designed to surface verbose-LLM failure modes — preambles, duplication, info-dumps, over-structure, trailing summaries, restating pasted input.

### Headline numbers

```
┌──────────────────────────────────────────────────────┐
│  TOKENS SAVED      ████████████████████        62%   │
│  WORDS SAVED       ████████████████████        62%   │
│  TIME SAVED        ████████████████            49%   │
└──────────────────────────────────────────────────────┘
```

### Median reduction vs baseline, per metric

For each chat-prompt: `reduction = (baseline − style) / baseline`. Median across the 8 chat-style prompts. Positive = shorter / faster than baseline. Median is robust — a single explosive output can't drag it around.

Sonnet, via the raw Anthropic API (clean numbers — no hidden reasoning tokens):

```
Tokens saved vs default Claude — % shorter

  plainly   ████████████████████████████████████████  +62%
  ntcoding  █████████████████████████████████         +52%
  caveman   ██████████████████████                    +35%
  drona     █                                          +3%
```

```
Words you actually read — % shorter than default

  plainly   ████████████████████████████████████████  +62%
  ntcoding  ██████████████████████████████████        +53%
  caveman   ███████████████████████                   +37%
  drona     █                                          +3%
```

```
Time to get the answer — % faster than default

  plainly   ███████████████████████████████           +49%
  ntcoding  ████████████████████                      +32%
  caveman   ███████████████                           +24%
  drona                                                -4%
```

Tokens and words track tightly under plainly — the model isn't spending hidden reasoning to compensate for short visible output. The reader sees less *and* you're billed for less *and* the response arrives faster.

**plainly leads next-best (ntcoding) by ~10 percentage points on every metric, and runs ~60% shorter than baseline at roughly half the latency.** caveman cuts ~35% / ~24%. drona barely improves on the default at all.

Less to read, fewer tokens billed, less time waiting.

### Verified across all three Claude tiers (via Claude Code CLI)

plainly's reduction vs default, median per model:

| model  | words shorter | tokens shorter |
|--------|--------------:|---------------:|
| haiku  | **+63%** | +32% |
| sonnet | **+47%** | +50% |
| opus   | **+61%** | +56% |

Token numbers via the CLI are noisier than via raw API (the CLI bills hidden reasoning) but the direction is identical. plainly is the only style in the benchmark that never bloats output on any model. Run the benchmark yourself to verify: [`benchmark/`](./benchmark).

---

## How plainly differs from caveman and other anti-verbose tools

| | what it targets |
|---|---|
| **caveman** | Word-level grammar (drop articles, fragments OK, lexical compression) |
| **drona / ntcoding / "be concise" rules** | Tone and word choice (no sycophantic openers, no emojis, "thorough in reasoning, concise in output") |
| **plainly** | Information architecture (answer-first, no preamble, no input restating, no tour, no trailing summary, calibrated length) |

The other tools shorten what Claude already wrote. plainly changes *what Claude writes in the first place*.

---

## Methodology

Benchmark harness, 10-prompt corpus with hand-written ideal answers, deterministic scorer (semantic similarity + length match), and per-run results — all live in [`benchmark/`](./benchmark). Reproducible end-to-end: `cd benchmark && uv sync && uv run run-bench --score`.

---

## Credits

The styles compared in the benchmark — credit to the authors:

- [caveman](https://github.com/juliusbrussee/caveman) — Julius Brussee
- [drona / claude-token-efficient](https://github.com/drona23/claude-token-efficient) — drona23
- [ntcoding / claude-skillz · concise-output](https://github.com/NTCoding/claude-skillz/tree/main/concise-output) — NTCoding

The length-budget framing in plainly is grounded in:

- [How Users Read on the Web](https://www.nngroup.com/articles/how-users-read-on-the-web/) — Nielsen Norman Group
- [Applying Writing Guidelines to Web Pages](https://www.nngroup.com/articles/applying-writing-guidelines-web-pages/) — Nielsen Norman Group
