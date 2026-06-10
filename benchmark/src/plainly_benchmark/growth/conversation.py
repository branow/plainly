"""The scripted conversation replayed against every style.

One realistic working session of a backend engineer: debugging, design
questions, follow-ups, and a couple of turns that legitimately deserve a
long answer (a code request, a walk-me-through) so the comparison is fair
to both styles.
"""

TURNS = [
    "Our checkout service started timing out on ~2% of requests after yesterday's deploy. Where would you start?",
    "The deploy only bumped the postgres driver from 8.11 to 8.13 and added a new index migration. Does that change your guess?",
    "The migration added a partial index on orders(status) where status = 'pending'. Table has 40M rows. Could that have run CONCURRENTLY and still cause this?",
    "pg_stat_activity shows a few queries stuck on 'ShareLock on transaction'. What does that usually mean?",
    "OK so likely the migration held locks longer than we thought. How do I confirm it's resolved now versus still degrading?",
    "p99 is back to normal. Should we add a statement_timeout to the service's pool config so this fails fast next time?",
    "What's a sane statement_timeout for a checkout flow that normally completes queries in under 50ms?",
    "Now a different thing: we're adding a refunds endpoint. Should it be POST /orders/{id}/refunds or POST /refunds with order_id in the body?",
    "The payments team says refunds can be partial and can fail asynchronously at the provider. Does that change the resource design?",
    "How should the endpoint behave if a refund is requested twice for the same charge — 409, 200 with the existing refund, or create a second one?",
    "Write the idempotency middleware for this in Python. FastAPI, Redis for the key store, keys expire after 24h.",
    "What happens in your implementation if Redis is down — does the request fail or proceed without idempotency?",
    "We decided to fail closed. Is returning 503 with Retry-After acceptable for a payments endpoint?",
    "Switching topics: a teammate opened a PR replacing our hand-rolled retry loop with the tenacity library. Worth the new dependency?",
    "The retry loop is used in 14 places and three of them have subtly different backoff. Does that tip it?",
    "Walk me through how you'd review that PR step by step — what you'd check first and what would make you block it.",
    "One of the 14 call sites retries a non-idempotent POST. The PR keeps that behavior. Blocker or note?",
    "Good call. Next: our staging environment drifts from prod constantly. Mostly env vars and feature flags. Cheapest fix?",
    "We already use terraform for infra but flags live in LaunchDarkly. Can drift detection cover both?",
    "What metric would tell us staging drift is actually causing bugs, not just annoying people?",
    "Our on-call had 31 pages last week, 25 were auto-resolved within 5 minutes. How do we cut the noise without missing real incidents?",
    "If we add a 5-minute pending period before paging, what's the realistic worst case we'd eat on a true outage?",
    "Last topic: a junior asked why we use ULIDs instead of UUIDv4 for order ids. Best short explanation?",
    "They followed up: if ULIDs are sortable by time, doesn't that leak order volume to anyone who sees two ids?",
    "Summarize the decisions we made this session so I can post them in the team channel.",
]
