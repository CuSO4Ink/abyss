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

## 17. Self-evolution requires explicit roadmap approval

Abyss may not add self-evolution targets, feature backlog items, implementation slices, scheduled tasks, agent roles, integrations, or delivery commitments to `ROADMAP.md` unless the user explicitly approves each item one by one. Self-discovered capabilities may be proposed, but they must not be implemented or added to the approved roadmap without explicit user approval.

During the bootstrapping transition, direct and timely human-assistant modification is allowed only when the user explicitly authorizes the specific modification in the current conversation. This temporary mode must remain subordinate to the roadmap approval rule, the P0 external interface boundary, and human review for meaningful risk. It should be retired for ordinary system changes once the governed self-iteration chain is complete and explicitly accepted by the user.

## 18. P0 incident: external interface misuse

It is a P0 architecture incident if Abyss uses any external LLM client, Knot client, IM client, agent client, browser automation session, vendor-specific assistant runtime, or other external interface for anything other than unified standard LLM invocation.

The only allowed external interface role is:

```text
Abyss Prompt / Prompt Package
  -> external LLM invocation interface
  -> model response text
  -> Abyss result import
```

External interfaces may only send prompts or Prompt Packages to an LLM model and return the model response text to Abyss. They must not be used for scheduling, triggering core workflows, notification delivery, file mutation, command execution, approval, rejection, audit, memory, policy decisions, state transitions, Git operations, Harness decisions, or self-evolution execution.
