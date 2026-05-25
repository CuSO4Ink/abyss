# ABYSS.md

Abyss is a governed, local-first personal AI operating layer. It turns user intent into structured records, routes model output through explicit governance gates, and keeps every meaningful state transition auditable before anything becomes an action.

This file is the default cognition entrypoint for humans, internal Agents, external model platforms, and future Brain Agent work. Do not start by reading source code unless a code change or implementation-level investigation is required.

## 1. What Abyss is

Abyss is not a general chat bot and not an unrestricted autonomous executor. It is a CLI-first, user-in-the-loop orchestration system for personal AI workflows and gradual self-evolution.

Core identity:

```text
personalized
local-first
governed
observable
auditable
progressively self-evolving
```

The current repository contains the Abyss implementation, rules, prompts, architecture documents, and local runtime process structure. Personal user data is kept separate in the private `abyss-data` repository.

## 2. Current medium-term goal: Brain Agent

The current medium-term direction is to prepare Abyss for a Brain Agent.

The Brain Agent is not a super-agent that executes everything. It is a global cognition, task decomposition, direction alignment, and result integration layer.

The Brain Agent should eventually help Abyss:

```text
understand the whole system structure
maintain alignment with the global direction
read current system state
understand agent roles and outputs
turn long-term user intent into governable tasks
identify local changes that drift away from architecture
compress development results back into system knowledge
```

The Brain Agent must remain subordinate to the existing governance chain. It must not bypass Harness review, Owner approval, roadmap approval, ChangeSet validation, audit, or executor boundaries.

## 3. Five foundational architectures

Abyss currently organizes its future direction around five foundational architectures:

```text
FSM
Self Evolution
Abyss Insight
Skill
Memory / Storage
```

They answer different system questions:

```text
FSM: how system state advances
Self Evolution: how the system grows
Abyss Insight: how the system sees itself
Skill: how reusable capabilities are stabilized
Memory / Storage: how state, history, and experience are retained
```

The Brain Agent is expected to coordinate across these foundations rather than replace them.

## 4. Non-negotiable Global Rules

Abyss development and operation must respect these global rules:

1. Abyss is a governed local personal AI operating layer, not an unconstrained autonomous agent.
2. The Owner is the final authority for meaningful risk, direction changes, and execution approval.
3. LLM, Agent, and external model outputs are candidate material only; they are not facts, approvals, or actions.
4. The Brain Agent is responsible for cognition, coordination, task decomposition, direction alignment, and result integration; it must not directly execute, approve, or bypass governance.
5. External model platforms are replaceable expert resources; they do not own Abyss memory, direction, governance, or execution authority.
6. System cognition starts from `ABYSS.md` and follows progressive disclosure; source code is not the default entrypoint.
7. Contracts, capsules, and system maps should be read before source code; source code is the final evidence layer when contracts are insufficient or implementation changes are required.
8. Any system modification must follow the governed path: proposal, approval, workflow, ChangeSet, validation, Harness review, Owner approval, executor apply, report.
9. Any meaningful change must remain observable, auditable, and rollback-aware.
10. Any change that alters structure, behavior, capability, Agent roles, context selection, or user-facing commands must update the corresponding cognition layer documents and rules.

For the highest-level rules, read `ABYSS_CONSTITUTION.md`.

## 5. Progressive disclosure reading order

Abyss should be understood in layers. Start broad, then reveal deeper evidence only when needed.

Default order:

```text
L0. ABYSS.md
L1. ABYSS_CONSTITUTION.md and rules/system_brief.yaml
L2. abyss-data/user_data/projects/abyss-future-planning/Global Direction Brief.md
L3. SYSTEM_MAP.md
L4. rules/modules.yaml
L5. rules/capabilities.yaml, rules/agents.yaml, rules/context_manifest.yaml
L6. abyss_cli/ source code, only when contracts are insufficient or code changes are required
L7. .local/runtime/ and audit/, only for debugging, audit, or state reconstruction
```

The machine-readable version of this disclosure order lives in `rules/architecture_cognition.yaml`.

## 6. Default path for an Agent to understand Abyss

An Agent or external model platform should understand Abyss through this path:

```text
1. Read ABYSS.md.
2. Read ABYSS_CONSTITUTION.md for hard principles.
3. Read rules/system_brief.yaml for compact machine-readable baseline constraints.
4. Read the Global Direction Brief for the current strategic direction.
5. Read SYSTEM_MAP.md for commands, modules, data flow, and runtime records.
6. Read rules/modules.yaml for module boundaries and capability capsules.
7. Read role and context contracts only as needed.
8. Read source code only when implementing, debugging, or verifying a concrete behavior.
9. Read runtime records only when reconstructing current state, audit history, or failure causes.
```

## 7. Default path for an Agent to modify Abyss

Ordinary system changes should enter through the governed self-evolution path:

```text
evolution request
-> self-evolution analysis
-> proposal
-> explicit user approval
-> ROADMAP entry
-> workflow start
-> implementation ChangeSet
-> dry-run
-> Harness review
-> Owner approval
-> executor apply
-> integrity check
-> report
```

During explicitly authorized bootstrapping work, direct file edits may occur only within the scope authorized by the user in the current conversation and must remain subordinate to the Constitution, P0 external interface boundary, and human review for meaningful risk.

Agents must not treat discussion, suggestions, or draft plans as approval to modify files, approve roadmap items, approve changesets, execute code, or change governance.

## 8. Documentation and rule synchronization after changes

When a change affects system understanding, update the relevant cognition surface instead of leaving knowledge hidden in code or runtime records.

Synchronization checklist:

```text
Architecture or global direction changes:
- ABYSS.md
- ABYSS_CONSTITUTION.md, only for highest-level principles
- SYSTEM_MAP.md
- Global Direction Brief, if strategy changes

Module boundary or capability changes:
- rules/modules.yaml
- rules/capabilities.yaml
- rules/agents.yaml, if agent roles change
- rules/context_manifest.yaml, if context packaging changes

Operational or command changes:
- README.md
- SYSTEM_MAP.md
- relevant rules/*.yaml

Governance or execution boundary changes:
- ABYSS_CONSTITUTION.md
- rules/system_brief.yaml
- rules/governance.yaml
- rules/policy.yaml
```

Do not duplicate all details everywhere. Keep `ABYSS.md` as the cognition entrypoint, `README.md` as the installation and usage guide, `ABYSS_CONSTITUTION.md` as the highest-level law, `SYSTEM_MAP.md` as the architecture map, and `rules/*.yaml` as machine-readable rule sources.

## 9. External collaboration stance

External model platforms may help with analysis, implementation drafts, review, and candidate ChangeSets. They are temporary expert collaborators.

They must not be treated as:

```text
system truth
runtime state authority
approval authority
execution authority
audit authority
governance authority
```

External development results should return to Abyss as candidate material with:

```text
task understanding
modules touched
files touched
proposed changes
risk assessment
validation method
architecture alignment
open questions
recommended next step
```

Abyss remains responsible for governance, audit, state transitions, approval, and execution.
