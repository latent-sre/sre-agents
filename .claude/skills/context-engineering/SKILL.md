---
name: context-engineering
description: >-
  Curate what enters the model's limited attention budget at each step — the discipline behind this
  fleet's progressive-disclosure design. Use when an agent's context is filling up, a task spans many
  files/logs/turns, or output quality is degrading as the transcript grows ("context rot"). Covers
  just-in-time retrieval, compaction, sub-agent context isolation, structured note-taking, and the
  least-context principle. From Anthropic's "Effective context engineering for AI agents."
metadata:
  domain: method
---

# Context engineering

The model has a **limited attention budget**; every token spent on noise is attention not spent on the
task. As capability grows, the lever isn't a cleverer prompt — it's *thoughtfully curating what's in
context at each step*. More tokens ≠ better: large or stale context degrades reasoning ("context rot").
*[sourced: Anthropic, "Effective context engineering for AI agents"]*

## The principle
Find the **smallest set of high-signal tokens** that lets the agent act correctly. Treat context like
least privilege: include what the step needs, nothing it doesn't.

## Techniques (use the lightest that works)
- **Just-in-time retrieval.** Pull the file, log slice, or metric *when you need it* — don't preload
  everything up front. Read the failing test, not the whole suite; `cf logs --recent`, not the firehose.
  *[sourced: Anthropic — JIT/agentic retrieval over load-everything]*
- **Progressive disclosure.** This is why skills load on demand: a short description sits in context;
  the full `SKILL.md` is read only when the task matches. Design new context the same way — a pointer
  now, the detail when warranted.
- **Compaction.** Near the limit, summarize the conversation's durable facts and reinitialize — carry
  the decisions and open threads, drop the chatter. *[sourced: Anthropic — compaction]*
- **Sub-agent context isolation.** Hand expensive, bounded fact-finding to a focused sub-agent that
  burns its own context and returns a **short summary** — the caller's window stays lean. This is
  exactly what `researcher` does; the `coordinator`/`incident-commander` emit a plan, not a transcript.
  *[sourced: Anthropic multi-agent research system]*
- **Structured note-taking / external memory.** Persist durable knowledge *outside* the window where
  it survives compaction — for us that's runbooks, postmortems, and the knowledge loop, not a giant
  scratchpad in-context.

## In this fleet
The architecture already embodies this: thin agents, skills loaded on demand, `researcher` as the
context-offload, `handoff-protocol` packaging the *minimal* cold-start context, gates carrying forward
only the evidence that matters. When a task is sprawling, apply the techniques above before reaching for
a bigger model or a longer prompt.

## Anti-patterns
- Dumping an entire file/log/repo into context "to be safe" — it dilutes attention and invites context rot.
- Carrying a completed sub-task's full transcript forward instead of its conclusion.
- Re-deriving facts already established earlier in the conversation.

## Handoffs
- → `researcher` to offload expensive fact-finding and get back a brief.
- → `handoff-protocol` to package the minimal context a receiving agent needs to start cold.
- → `parallelization` when isolated sub-agents are the right way to cover breadth without bloating one window.
