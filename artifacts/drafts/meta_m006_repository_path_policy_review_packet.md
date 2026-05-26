# Meta M006 Repository Path Policy Review Packet

Roadmap item: R066
Proposal: evo_prop_20260526_164116_60ffba
Purpose: Prepare Owner-review material for repository path policy maintenance before any implementation.

## Boundary statement

This packet is read-only analysis material. It does not authorize implementation, self-approval, policy mutation, prompt mutation, governance mutation, same-cycle activation, executor application, scheduling, Git operations, or external side effects.

Any future repository path policy extraction or consolidation must enter a separate governed change path with explicit Owner approval, Harness review, rollback planning, validation evidence, and delayed activation in a later workflow cycle.

## 1. Current repository path policy surface inventory

The current repository path policy is distributed across several surfaces rather than centralized in one shared component.

### Context and disclosure surfaces

- `abyss_cli/context_pack.py`
  - Validates explicit target paths for context inclusion.
  - Rejects absolute paths, parent traversal, runtime/audit/user-data paths, and missing files.
  - Allows selected source, rule, artifact, and documentation roots for context disclosure.
- `abyss_cli/disclosure.py`
  - Classifies paths into progressive disclosure levels.
  - Defines source, runtime, and provider-workspace prefixes.
  - Audits context-manifest disclosure boundaries.
- `rules/context_manifest.yaml`
  - Declares task-type context requirements, forbidden paths, disclosure levels, and required files.
- `rules/architecture_cognition.yaml`
  - Defines the progressive disclosure model and explicitly excludes provider workspace from default context.

### Governance-core request and routing surfaces

- `abyss_cli/request_rules.py`
  - Defines governance-core surfaces and paths.
  - Detects governance-core scope from request text and paths.
  - Maps request types to context task types.
- `abyss_cli/request_envelope.py`
  - Validates normalized request semantics and governance-core warning conditions.
- `rules/request_types.v1.yaml`
  - Defines request types, meta-governance requirements, and hard boundaries.
- `rules/contracts/request_envelope.v1.yaml`
  - Defines request-envelope contract boundaries for governance-core and meta-evolution routing.
- `rules/schemas/request_envelope.v1.schema.json`
  - Defines structural validation for request envelopes.

### Executor and ChangeSet path surfaces

- `abyss_cli/changeset.py`
  - Normalizes target paths for executor operations.
  - Blocks parent traversal and disallowed roots.
  - Maintains an allowlist for ChangeSet filesystem operations.
  - Maintains an allowlist for check commands.
- `rules/capabilities.yaml`
  - Declares executor capabilities, allowed roots, blocked capabilities, and agent capabilities.
- `rules/policy.yaml`
  - Defines path constraints, sensitive patterns, safe create prefixes, and risk levels.

### Integrity and validation surfaces

- `abyss_cli/integrity.py`
  - Checks required repository structure.
  - Validates context-manifest path references.
  - Detects default inclusion of runtime or provider workspace paths where inappropriate.
  - Checks sensitive tracked paths.
  - Validates contracts, schemas, request rules, rule registry, module manifests, and disclosure audit output.
- `rules/rule_sources.v1.yaml`
  - Declares rule source files, consumers, and validation commands.
- `rules/contracts/rule_source_registry.v1.yaml`
  - Defines the rule source registry contract.
- `rules/schemas/rule_source_registry.v1.schema.json`
  - Defines the rule source registry schema.

### Documentation and cognition surfaces

- `ABYSS.md`
  - Defines global modification and progressive disclosure expectations.
- `ABYSS_CONSTITUTION.md`
  - Defines constitutional boundaries including external interface misuse, proposal-before-action, and self-evolution approval requirements.
- `SYSTEM_MAP.md`
  - Documents system directories, runtime paths, forbidden external-interface uses, and module responsibilities.
- `rules/modules.yaml`
  - Declares module capsules, boundaries, invariants, and validation expectations.

## 2. Is shared repository path policy extraction necessary?

A shared repository path policy helper may be useful, but it is not automatically required merely because path checks appear in multiple files.

### Arguments for extraction

- Multiple modules independently normalize and validate repository-relative paths.
- Similar blocked prefixes appear in more than one location, including `.git/`, `.local/`, `audit/`, `process/`, `storage/`, and `user_data/`.
- Context disclosure, executor safety, governance-core detection, and integrity checks all depend on path semantics.
- A shared helper could reduce drift between context-pack inclusion, ChangeSet execution validation, and integrity checks.
- A shared helper could make rollback and validation easier if it preserves all current behaviors and exposes task-specific policy profiles.

### Arguments against immediate extraction

- The current path checks serve different authorities and risk models.
  - Context disclosure decides what may be read for agent grounding.
  - ChangeSet validation decides what may be written by an approved executor.
  - Integrity checks detect repository drift and sensitive tracked paths.
  - Disclosure classification maps paths to cognition levels.
- Centralizing too early could accidentally merge read-disclosure policy with write-executor policy.
- Governance-core surfaces are sensitive; changing them may affect approval gates, context disclosure, executor boundaries, or constitutional behavior.
- Some duplication is intentional defensive redundancy across governance layers.
- Current policy is distributed but explicit; extraction could make behavior less visible if not documented and validated carefully.

### Recommendation

Do not implement extraction in this cycle. Treat extraction as a future governance-core maintenance candidate only if Owner explicitly approves a separate implementation proposal.

If extraction is pursued later, it should be minimal, behavior-preserving, and profile-based. It should not create a single permissive path validator shared by all call sites. Instead, it should expose narrowly named helpers for distinct purposes such as context-disclosure targets, ChangeSet filesystem targets, governance-core surface paths, integrity references, and disclosure-level classification.

## 3. Protected surfaces affected by any future extraction

Any future shared path policy extraction would touch or affect the following protected surfaces:

- `context_disclosure_policy`
  - Affected files: `abyss_cli/context_pack.py`, `abyss_cli/disclosure.py`, `rules/context_manifest.yaml`, `rules/architecture_cognition.yaml`.
  - Risk: over-disclosure, missing context, runtime/provider workspace leakage, or source access drift.
- `permission_boundaries`
  - Affected files: `abyss_cli/changeset.py`, `rules/capabilities.yaml`, `rules/policy.yaml`.
  - Risk: write access expansion, path traversal bug, blocked path regression, or check-command boundary drift.
- `governance_contracts`
  - Affected files: `rules/contracts/`, `rules/schemas/`, `rules/governance.yaml` where policy behavior is documented or validated.
  - Risk: contract mismatch or implied authority expansion.
- `approval_gates`
  - Affected files: `abyss_cli/workflow.py`, `abyss_cli/owner.py`, and any path policy that affects whether ChangeSets reach approval.
  - Risk: invalid ChangeSets reaching Owner review or valid ones being blocked incorrectly.
- `harness_policy`
  - Affected files: `abyss_cli/harness.py`, `abyss_cli/harness_review.py`, `rules/policy.yaml`.
  - Risk: Harness and executor disagreeing on allowed paths or operation risk.
- `self_evolution`
  - Affected files: `abyss_cli/evolution.py`, `abyss_cli/evolution_analysis.py`, request routing and proposal creation logic.
  - Risk: governance-core classification or roadmap-entry handling becomes too broad or too permissive.
- `global_rules` and `constitution_rules`
  - Affected files: `ABYSS.md`, `ABYSS_CONSTITUTION.md`, `SYSTEM_MAP.md` if behavior or boundaries change.
  - Risk: cognition layer drift from actual implementation.
- `external_ai_authority`
  - Affected files: external collaboration surfaces and context-pack disclosure controls.
  - Risk: external model packages receive too much repository or runtime context.
- `git_authority`
  - Affected files: data-sync and capability rules if path policy expands to Git-related paths.
  - Risk: repository/data boundary confusion.
- `memory_policy`
  - Affected files: request type rules and future memory-related paths.
  - Risk: user data, storage, or memory material entering implementation context incorrectly.

## 4. Behavior-preservation constraints for future implementation

Any future repository path policy extraction must satisfy these testable invariants:

1. No absolute path is accepted where current code requires repo-relative paths.
2. No parent traversal path containing `..` is accepted where current code rejects it.
3. `.local/`, `.git/`, `audit/`, `process/`, `storage/`, and `user_data/` remain blocked from default context and executor write targets except where explicitly and separately governed.
4. `.local/knot_provider_workspace/` remains excluded from default context.
5. `.local/runtime/` remains excluded from default context except for explicit runtime investigation or audit contexts.
6. ChangeSet filesystem writes remain limited to the existing allowed roots and explicitly allowed paths unless a later Owner-approved governance change expands them.
7. Context disclosure read eligibility must not be treated as executor write eligibility.
8. Executor write eligibility must not be treated as context disclosure read eligibility.
9. Disclosure-level classification remains stable for existing documented paths.
10. Governance-core surface detection remains conservative and must not lose any existing protected surface mapping.
11. Integrity checks continue to fail on missing required files, malformed contracts, malformed schemas, invalid context references, provider-workspace default context, runtime default context where prohibited, and sensitive tracked paths.
12. Rule source registry validation continues to cover all accepted rule sources.
13. Request envelope validation continues to warn when governance-core scope is routed through a non-meta-governance request type.
14. Existing allowed check commands remain allowlisted and no arbitrary shell execution becomes possible.
15. The public CLI behavior for `check`, `request types`, `rules validate`, `disclosure audit`, and workflow commands remains unchanged except for explicitly approved wording changes.
16. All changes remain auditable through ChangeSet, dry-run, Harness review, Owner approval, executor apply, integrity check, and report.

## 5. Risk assessment

### Status quo risks

- Duplicate path rules can drift over time.
- Similar blocked-prefix lists may be updated in one module but not another.
- Reviewers must inspect multiple files to understand repository path boundaries.
- New modules may reimplement path validation inconsistently.

Severity: L2 to L3 depending on the touched surface.

### Extraction risks

- Accidental authority merging between read-disclosure policy and write-executor policy.
- Over-broad helper names could encourage unsafe reuse.
- A central bug could affect multiple governance layers at once.
- Changing governance-core behavior in the same cycle as approval would violate delayed activation expectations.
- Refactoring path policy without exhaustive validation could silently alter context inclusion or executor write eligibility.

Severity: L3 because affected surfaces include context disclosure, permission boundaries, governance contracts, Harness policy, and approval flow.

### Risk-balanced approach

If future extraction is approved, prefer a small internal helper module or localized utility functions with separate policy profiles. Preserve call-site intent with explicit names and avoid a generic `is_safe_path` function.

## 6. Rollback plan skeleton for any future implementation

A future implementation proposal should include this rollback plan:

1. Capture pre-change behavior evidence.
   - Record outputs from `python -m abyss_cli check`.
   - Record outputs from `python -m abyss_cli request types --all --json`.
   - Record outputs from `python -m abyss_cli rules validate --json` if available in the approved command list.
   - Record relevant dry-run evidence for path-allowlist behavior.
2. Keep the extraction ChangeSet minimal and reviewable.
   - Avoid unrelated formatting changes.
   - Avoid broad rewrites of large orchestration functions.
3. If validation fails before apply, reject the ChangeSet and keep current code unchanged.
4. If validation fails after apply, use the ChangeSet diff and repository history to revert all touched files to the pre-change state.
5. Re-run the same validation commands after rollback.
6. Confirm that no runtime records, external messages, schedules, Git operations, or governance activation occurred as part of rollback.
7. Produce a workflow report that documents the rollback reason, files restored, and validation evidence.

## 7. Validation plan for any future implementation

A future extraction must include concrete validation evidence. At minimum:

- `python -m compileall -q abyss_cli`
- `python -m abyss_cli check`
- `python -m abyss_cli request types --all --json`
- `python -m abyss_cli rules validate --json` if included in the active allowlist for that workflow

Additional review checks should verify:

- Existing blocked prefixes remain blocked in each relevant policy context.
- Existing allowed source, rule, artifact, and documentation paths remain accepted where currently accepted.
- Context Broker still includes declared required files and still reports missing files.
- Disclosure audit still detects over-disclosure and provider-workspace default context problems.
- ChangeSet validation still rejects disallowed paths, parent traversal, missing old content, no-op replacement, unsupported operations, and non-allowlisted commands.
- Request governance-core detection still flags protected surfaces and required meta-governance review.
- No new broad shell, browser, service, external write, Git push, prompt.modify, policy.modify, governance.modify, or roadmap.modify authority is introduced.

## 8. Activation note

This review packet itself activates nothing. It only prepares Owner decision material.

If the Owner later approves a repository path policy extraction, the accepted change must not activate in the same workflow cycle that approves the governance-core change. The future ChangeSet may be reviewed, dry-run, and applied only through the governed chain. Any governance-core behavior change must become active only in a later cycle after validation and reporting.

## 9. Delayed activation requirements

Before any future repository path policy extraction becomes active:

1. Owner must explicitly approve the specific implementation proposal.
2. The implementation must be represented as a bounded ChangeSet or deterministic edit plan.
3. Harness review must assess safety, completeness, and behavior preservation.
4. Owner must approve the concrete ChangeSet after review.
5. Executor must apply only approved, allowlisted operations.
6. Integrity and compile checks must pass.
7. A workflow report must record the result.
8. Activation of any changed governance-core behavior must occur in a later workflow cycle, not the cycle that approved the change.

## 10. Owner decision options

The Owner may choose one of these next decisions:

- Preserve status quo: Keep path policy distributed and rely on existing validation.
- Approve analysis-only follow-up: Request a more detailed comparison matrix without implementation.
- Approve future bounded extraction proposal: Create a separate implementation target with explicit scope, affected files, validation plan, rollback plan, and delayed activation requirement.
- Reject extraction: Treat current duplication as intentional defensive separation.

Recommended next step: preserve status quo unless a concrete drift, bug, or maintenance failure is observed. If extraction is later requested, require a new approved proposal focused on behavior-preserving path policy consolidation with separate profiles for disclosure, executor, integrity, and governance-core detection.
