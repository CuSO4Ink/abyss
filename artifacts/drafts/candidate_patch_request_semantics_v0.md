# Candidate Patch: Request Semantics / Rule Propagation V0

**Status:** Candidate patch / ungoverned draft  
**Created at:** 2026-05-25 23:16 +0800  
**Prepared by:** external assistant session  
**Governance status:** Not approved by Abyss self-evolution workflow  
**Mutation status:** Source tree already contains direct, ungoverned working-copy edits  

## 1. Demotion Statement

The current working-copy changes for Request Semantics / Rule Propagation V0 are hereby downgraded to a **candidate patch**.

They must not be treated as a completed or governance-compliant Abyss implementation, because they were introduced through direct external source mutation rather than through the Abyss self-evolution pipeline.

Correct interpretation:

```text
current diff = candidate material only
current diff != approved ChangeSet
current diff != Owner-approved workflow result
current diff != accepted Abyss self-evolution output
```

## 2. Reason for Demotion

The changes touched source, rules, schemas, and cognition documentation directly.

For Abyss semantics, this kind of work is mutation-bearing and should route through self-evolution governance:

```text
Request Envelope
→ proposal / workflow
→ ChangeSet
→ dry-run
→ Harness review
→ Owner approval
→ executor apply
→ check
```

The actual path used was:

```text
human conversation authorization
→ external assistant direct file mutation
→ local validation commands
→ summary report
```

That bypasses the system-internal governance record, even if the human user asked to proceed.

## 3. Candidate Request Classification

Recommended request classification for formal intake:

```yaml
schema: abyss.request_envelope.v1
request_type: feature_request
title: Request Semantics / Rule Propagation V0
status: candidate
requires_code_change: true
requires_cognition_update: true
requires_owner_approval: true
governance_route: proposal_then_self_evolution
risk_level: medium
```

Alternative classification if treated as internal hardening rather than new capability:

```yaml
request_type: maintenance_request
maintenance_kind: validation_hardening
governance_route: self_evolution
```

Recommended classification: **feature_request**, because the patch adds a new system-facing capability: canonical request semantics, request envelope normalization, request-related CLI surface, and context-routing integration.

## 4. Candidate Patch Intent

Introduce a V0 request semantics layer so Abyss can make request type explicit before context selection, validation, governance routing, and downstream coordination.

Core principle introduced by the candidate patch:

```text
request_id = identity tracking only
request_type = semantic authority for parsing, routing, validation, context selection, and governance behavior
```

## 5. Candidate Scope

### 5.1 Added rule source

```text
rules/request_types.v1.yaml
```

Candidate purpose:

- Define canonical V0 request types.
- Separate active request types from reserved request types.
- Assign default governance routes and hard boundaries.
- Encode whether code change, cognition update, validation plan, and Owner approval are required.
- Represent refactor as `maintenance_request` with `maintenance_kind=refactor`, not as a top-level `refactor_request`.

### 5.2 Added contract and schema

```text
rules/contracts/request_envelope.v1.yaml
rules/schemas/request_envelope.v1.schema.json
```

Candidate purpose:

- Define normalized Request Envelope structure.
- Make request semantics explicit before routing.
- Record hard boundaries:
  - normalization grants no execution authority;
  - normalization grants no approval authority;
  - mutation requests still require proposal, workflow, ChangeSet, dry-run, review, Owner approval, executor apply, and check;
  - natural-language classification is not authoritative in V0;
  - Brain Agent can prepare/recommend but cannot approve/execute;
  - external models cannot create executable tasks directly.

### 5.3 Added request rules access layer

```text
abyss_cli/request_rules.py
```

Candidate purpose:

- Provide one shared reader for request type rules.
- Avoid duplicate ad hoc parsing across Context Broker, Harness, Brain, Self Evolution, and CLI.
- Validate request rules configuration.
- Expose request type to context task mapping.

### 5.4 Added request envelope module

```text
abyss_cli/request_envelope.py
```

Candidate purpose:

- Build candidate Request Envelopes.
- Validate envelope structure and request-type-specific required fields.
- Load envelope files with UTF-8 / UTF-8-SIG / UTF-16 tolerance for Windows PowerShell redirection output.
- Keep normalization non-executing and non-approving.

### 5.5 Added CLI command group

```text
abyss_cli/__main__.py
```

Candidate purpose:

Add commands equivalent to:

```powershell
python -m abyss_cli request types
python -m abyss_cli request types --all
python -m abyss_cli request types --all --json
python -m abyss_cli request normalize --type maintenance_request --title "..."
python -m abyss_cli request validate path\to\request_envelope.json
```

### 5.6 Integrated Context Broker

```text
abyss_cli/context_pack.py
```

Candidate purpose:

- Detect `request_type` from Request Envelope-like target records.
- Prefer canonical request semantics over keyword fallback where available.
- Include request rules/contract/schema in context packages when request semantics are relevant.

### 5.7 Integrated Integrity Check

```text
abyss_cli/integrity.py
```

Candidate purpose:

- Include request semantics files in integrity coverage.
- Validate request rules configuration.
- Detect missing request semantics rules, contracts, or schemas.

### 5.8 Updated cognition/user-facing docs

```text
README.md
SYSTEM_MAP.md
```

Candidate purpose:

- Document request semantics V0 commands.
- Document request envelope boundaries.
- Document new source files and context-routing relationship.

## 6. Current Working-Copy File List

Tracked files modified:

```text
README.md
SYSTEM_MAP.md
abyss_cli/__main__.py
abyss_cli/context_pack.py
abyss_cli/integrity.py
```

Untracked files added:

```text
abyss_cli/request_envelope.py
abyss_cli/request_rules.py
rules/contracts/request_envelope.v1.yaml
rules/request_types.v1.yaml
rules/schemas/request_envelope.v1.schema.json
```

Diff stat for tracked files at demotion time:

```text
README.md                 |  26 +++++++++++-
SYSTEM_MAP.md             |  16 ++++++--
abyss_cli/__main__.py     | 102 ++++++++++++++++++++++++++++++++++++++++++++++
abyss_cli/context_pack.py |  20 ++++++++-
abyss_cli/integrity.py    |  13 ++++++
5 files changed, 169 insertions(+), 8 deletions(-)
```

Note: the stat above does not include untracked new files.

## 7. Candidate Validation Evidence

The direct implementation session reported successful local checks for:

```powershell
python -m abyss_cli request types --all
python -m abyss_cli request normalize ...
python -m abyss_cli request validate .local/tmp/request_envelope_test.json
python -m compileall abyss_cli
python -m abyss_cli check
```

Reported result:

```text
request validate => ok=True
python -m abyss_cli check => OK
```

Because these validations were performed outside the formal Abyss self-evolution workflow, they should be treated as **candidate evidence**, not as final acceptance evidence.

A formal workflow should rerun validation during dry-run and post-apply check.

## 8. Candidate Acceptance Criteria

A formally accepted version of this patch should satisfy:

1. Request type rules exist and are validated by integrity checks.
2. Request Envelope contract and schema exist and are referenced by the system map.
3. CLI can list request types, normalize a candidate envelope, and validate an envelope file.
4. Request normalization does not create workflow records, approve requests, or execute mutations.
5. Context Broker can use `request_type` when available.
6. Mutation-bearing request types continue to require proposal/workflow/ChangeSet/dry-run/Harness review/Owner approval/executor apply/check.
7. Documentation states the V0 non-goals and authority boundaries clearly.
8. `refactor_request` is not introduced as a top-level request type in V0.
9. The final accepted patch is represented by an approved ChangeSet, not by this raw working-copy diff.

## 9. Known Governance Gap

The patch currently exists in the working tree before formal approval.

This creates a governance ambiguity:

```text
source state contains candidate implementation
process state has not approved candidate implementation
```

Until resolved, downstream agents and humans should treat the implementation as provisional.

## 10. Recommended Next Steps

### Option A: Convert current diff into a formal self-evolution intake

1. Create a Request Envelope for this candidate patch.
2. Create a proposal describing motivation, scope, non-goals, risk, validation plan, and rollback plan.
3. Compile the current diff into a ChangeSet candidate.
4. Run dry-run validation.
5. Perform Harness review.
6. Ask Owner for explicit approval.
7. If approved, formally apply/accept the ChangeSet and rerun checks.
8. Record final audit/summary.

### Option B: Revert source changes and restart through self-evolution

1. Save this document as historical candidate material.
2. Revert the direct source/rules/docs modifications.
3. Start the Request Semantics V0 work through the official request/proposal/ChangeSet route.

### Recommended path

Use **Option A** if the current implementation is technically close to desired behavior and the priority is to preserve useful work while restoring governance.

Use **Option B** if the priority is a clean governance lineage with no pre-existing source mutation.

## 11. Explicit Non-Approval Statement

This document does not approve the patch.

This document only records that the existing direct modifications have been downgraded to candidate material pending Abyss self-evolution review and Owner decision.
