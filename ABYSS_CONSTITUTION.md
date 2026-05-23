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

## 7. Layered data architecture

Abyss separates information into three layers: the user data layer, the implementation layer, and the data storage layer. The user data layer is the default information surface, primarily aligned with the user's active Obsidian notes and current directions. The implementation layer and data storage layer should remain outside the user's default information retrieval scope. When archived material is needed, Abyss should retrieve a focused subset from storage and promote or materialize it into the user data layer with provenance, rather than exposing the storage layer directly.

## 8. Separated single-user Git sync

Abyss may use Git for single-user, multi-device synchronization, but the implementation repository and the personal data repository should remain separate. The system repository contains Abyss code, rules, prompts, and architecture. The private data repository contains the user's active data layer and storage layer. A new device should be able to install Abyss, configure the private data repository, and pull user data without mixing personal notes into the system implementation repository.

## 9. Intent before execution

User commands and system events are represented as structured Intents before they become prompts or actions.

## 10. Prompt Package as the core interface

Abyss does not simply forward raw user input to an LLM. It builds a Prompt Package containing intent, context, constraints, allowed actions, denied actions, and expected output format.

## 11. LLM output is candidate material

LLM output may contain answers, suggestions, action proposals, memory candidates, or rule-change candidates. It does not directly become truth, memory, policy, or execution.

## 12. Proposals before actions

Any requested file write, external side effect, Git operation, notification, or policy change must first be represented as an Action Proposal.

## 13. Deterministic policy gate

The MVP Harness makes deterministic decisions: `allow`, `review`, or `deny`.

## 14. Human review for meaningful risk

Risky actions, irreversible actions, policy changes, external effects, and Git publication require review.

## 15. Append-only audit principle

The audit log records intents, prompt packages, proposals, decisions, reviews, and executions. Historical audit entries should not be rewritten.

## 16. Local secrets stay local

Secrets, tokens, credentials, machine-local config, and caches must not enter syncable Git data.

## 17. Self-evolution is native, harnessed, and backlog-bound

Abyss may evolve itself only through native Abyss-controlled mechanisms: roadmap backlog selection, structured evolution records, deterministic checks, Harness / HarnessAgent review, audit evidence, and Git evidence. Backlog-listed bounded implementation slices may be executed through the governed path. Self-discovered non-backlog capabilities must remain proposals until the user explicitly approves them. Active policy changes always require human approval.

## 18. P0 incident: external client dependency

It is a P0 architecture incident if Abyss depends on an external LLM client, IM client, agent client, browser automation session, or vendor-specific assistant runtime as part of its core system operation. External clients may be optional triggers, notification channels, LLM providers, or human interaction surfaces, but they must never be required dependencies for the FSM, self-evolution runner, Harness, policy gate, audit trail, state transition, Git evidence, or execution authority.

A valid Abyss core workflow must be runnable from the Abyss repository and its declared local/runtime configuration using standard OS, Python, Git, and explicitly configured provider interfaces. If a workflow only works because an external LLM/Knot client supplies hidden tools, scheduling, memory, file mutation, approval, or execution authority, that workflow is invalid and must be redesigned as a native Abyss capability.
