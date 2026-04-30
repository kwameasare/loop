# Memory

Loop separates memory into three explicit tiers. Each tier has different
durability, scope, and isolation guarantees.

```python
memory = Memory(
    user="postgres",          # durable, per end-user
    session=Memory.ttl("24h"), # ephemeral, per conversation
    scratch=Memory.in_run(),   # per-turn, dropped after `complete`
)
```

## User tier

Stored in Postgres. Keyed by `(workspace_id, agent_id, user_id)`.
Durable forever unless the workspace owner deletes it. This is where you
keep things like a customer's preferred language, plan tier, or saved
addresses.

## Session tier

Stored in Redis. Keyed by `(workspace_id, agent_id, conversation_id)`.
Defaults to a 24-hour TTL — long enough for a chat thread, short enough
that you don't accidentally turn it into a parallel database.

## Scratch tier

In-process, per-turn only. Cleared at the start of every `execute()`
call. Use it for things like "I just looked up the customer's email,
keep it handy for the next tool call in the same turn."

## What goes where

| Need | Tier |
| --- | --- |
| Customer's plan tier | user |
| The current chat history | session |
| A retrieved KB chunk you'll cite later this turn | scratch |
| The list of orders you fetched in iteration 1 | scratch |
| An OAuth refresh token | user, **with secret tag** |

The runtime persists user/session diffs at the end of every turn. Scratch
is never persisted.
