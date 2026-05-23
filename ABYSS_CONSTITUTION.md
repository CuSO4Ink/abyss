# Abyss Constitution

## 1. Harness first

Abyss is not an autonomous agent. It is a governed orchestration system. All meaningful actions must pass through a Harness policy decision.

## 2. Progressive disclosure

Abyss should expose only the information and controls needed for the current decision, while keeping deeper detail accessible on demand. Default paths should be simple; advanced paths should be opt-in.

## 3. High information density

Abyss should prefer compact, structured, decision-useful information over verbose or decorative output. Every prompt package, command output, review record, and audit entry should preserve key constraints, risks, identifiers, and next actions.

## 4. Low cognitive load

Abyss should reduce the amount of state, choice, and interpretation the user must hold in memory at once. Flows should make the next safe action obvious, especially during review and execution decisions.

## 5. Modular decoupling

Abyss should keep policy, prompts, execution, review, audit, and storage separated so each layer can evolve independently without hidden side effects.

## 6. Extensibility first

Abyss should design MVP mechanisms as stable seams for future agentic review, API executors, UI surfaces, richer storage, and additional capabilities. New capabilities should enter through declared schemas and gates rather than ad-hoc code paths.

## 7. Intent before execution

User commands and system events are represented as structured Intents before they become prompts or actions.

## 8. Prompt Package as the core interface

Abyss does not simply forward raw user input to an LLM. It builds a Prompt Package containing intent, context, constraints, allowed actions, denied actions, and expected output format.

## 9. LLM output is candidate material

LLM output may contain answers, suggestions, action proposals, memory candidates, or rule-change candidates. It does not directly become truth, memory, policy, or execution.

## 10. Proposals before actions

Any requested file write, external side effect, Git operation, notification, or policy change must first be represented as an Action Proposal.

## 11. Deterministic policy gate

The MVP Harness makes deterministic decisions: `allow`, `review`, or `deny`.

## 12. Human review for meaningful risk

Risky actions, irreversible actions, policy changes, external effects, and Git publication require review.

## 13. Append-only audit principle

The audit log records intents, prompt packages, proposals, decisions, reviews, and executions. Historical audit entries should not be rewritten.

## 14. Local secrets stay local

Secrets, tokens, credentials, machine-local config, and caches must not enter syncable Git data.

## 15. Self-evolution is proposal-only

Abyss may propose changes to prompts, policies, or its own architecture, but active policy changes require human approval.
