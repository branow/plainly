# plainly

A plugin that makes AI coding agents write for the human reading it.
Answer-first. No preamble. No tour. The reader's time is the metric.
~60% shorter responses, ~2× faster — the natural consequence.

```
/plugin marketplace add branow/plainly
/plugin install plainly@plainly-marketplace
```

---

## Before / After

> **Prompt:** *Can you tell me what caused this deploy to fail?* (plus a 12-line deploy log with pods crashing on Redis `ECONNREFUSED` and the NetworkPolicy change already flagged)

<table>
<tr>
<th width="50%">Default Claude — 155 words</th>
<th width="50%">plainly — 58 words</th>
</tr>
<tr>
<td valign="top">

The deploy failed because a **NetworkPolicy change blocked Redis access**.

Specifically:

1. The `api-gateway` pods crashed immediately on startup with `ECONNREFUSED` trying to reach `redis-primary.cache.svc.cluster.local:6379`.
2. The root cause was a NetworkPolicy change — `api-gateway-egress` was updated ~14 minutes before the deploy by `@marek` (commit `8e2a1f3`), which **removed the egress rule that allowed port 6379 traffic to the `cache` namespace**.
3. Without that rule, the pods couldn't reach Redis and crashed in a `CrashLoopBackOff` loop.

The deploy system auto-rolled back to `v4.18.1`, which would have restored connectivity since the NetworkPolicy change is unrelated to the app version — but the underlying policy change is still in place and will affect any future deploys until it's fixed.

**To fix:** Restore the egress rule for port 6379 to the `cache` namespace in the `api-gateway-egress` NetworkPolicy, or coordinate with `@marek` to understand if the removal was intentional (and if so, update the app to not depend on Redis).

</td>
<td valign="top">

The deploy failed because @marek's NetworkPolicy change (commit `8e2a1f3`, 14 min before deploy) removed the egress rule that allowed the api-gateway pods to reach Redis on port 6379, so every pod crashed on startup trying to connect to `redis-primary.cache.svc.cluster.local:6379`.

Fix is to restore the egress rule in `api-gateway-egress` permitting TCP 6379 to the `cache` namespace, then redeploy v4.18.2.

</td>
</tr>
</table>

---

## What plainly does

- **Slack-colleague framing** — colleagues don't write whitepapers
- **First sentence IS the answer** — inverted-pyramid news rule
- **4-sentence ceiling for chat** — hard cap, exceptions for depth/reviews/proposals/code
- **No decorative banners, demos, emojis, or bold-as-header** — noise removed

---

## Proof — benchmark

Tested against `baseline` (no system prompt) and three popular anti-verbose styles, on a 10-prompt corpus targeting verbose LLM failure modes (preambles, duplication, info-dumps, over-structure, trailing summaries, input restating).

```
┌──────────────────────────────────────────────────────┐
│  TOKENS SAVED      ████████████████████        62%   │
│  WORDS SAVED       ████████████████████        62%   │
│  TIME SAVED        ████████████████            49%   │
└──────────────────────────────────────────────────────┘
```

### Sonnet — raw Anthropic API

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

### All three Claude tiers — Claude Code CLI

| model  | words shorter | tokens shorter |
|--------|--------------:|---------------:|
| haiku  | **+63%** | +32% |
| sonnet | **+47%** | +50% |
| opus   | **+61%** | +56% |

Reproduce: [`benchmark/`](./benchmark).

---

## How plainly differs

| | what it targets |
|---|---|
| **caveman** | Word-level grammar — drop articles, fragments OK, lexical compression |
| **drona / ntcoding** | Tone and word choice — no sycophantic openers, no emojis, "concise in output" |
| **plainly** | Information architecture — answer-first, no preamble, no input restating, no tour, no trailing summary, calibrated length |

---

## Credits

**Compared styles:**
- [caveman](https://github.com/juliusbrussee/caveman) by Julius Brussee
- [drona / claude-token-efficient](https://github.com/drona23/claude-token-efficient) by drona23
- [ntcoding / claude-skillz · concise-output](https://github.com/NTCoding/claude-skillz/tree/main/concise-output) by NTCoding

**Research:**
- [How Users Read on the Web](https://www.nngroup.com/articles/how-users-read-on-the-web/) — Nielsen Norman Group
- [Applying Writing Guidelines to Web Pages](https://www.nngroup.com/articles/applying-writing-guidelines-web-pages/) — Nielsen Norman Group

---

## License

MIT — see [LICENSE](./LICENSE).
