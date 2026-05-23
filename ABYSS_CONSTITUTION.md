# Abyss Constitution

## 1. Harness first

Abyss is not an autonomous agent. It is a governed orchestration system. All meaningful actions must pass through a Harness policy decision.

## 2. Intent before execution

User commands and system events are represented as structured Intents before they become prompts or actions.

## 3. Prompt Package as the core interface

Abyss does not simply forward raw user input to an LLM. It builds a Prompt Package containing intent, context, constraints, allowed actions, denied actions, and expected output format.

## 4. LLM output is candidate material

LLM output may contain answers, suggestions, action proposals, memory candidates, or rule-change candidates. It does not directly become truth, memory, policy, or execution.

## 5. Proposals before actions

Any requested file write, external side effect, Git operation, notification, or policy change must first be represented as an Action Proposal.

## 6. Deterministic policy gate

The MVP Harness makes deterministic decisions: `allow`, `review`, or `deny`.

## 7. Human review for meaningful risk

Risky actions, irreversible actions, policy changes, external effects, and Git publication require review.

## 8. Append-only audit principle

The audit log records intents, prompt packages, proposals, decisions, reviews, and executions. Historical audit entries should not be rewritten.

## 9. Local secrets stay local

Secrets, tokens, credentials, machine-local config, and caches must not enter syncable Git data.

## 10. Self-evolution is proposal-only

Abyss may propose changes to prompts, policies, or its own architecture, but active policy changes require human approval.
