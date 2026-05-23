# Abyss

Harness-first personal AI orchestration workspace.

Abyss MVP is a local, CLI-first orchestration layer. It turns user intent into structured Prompt Packages, routes outputs through a deterministic Harness, and records an auditable trail before anything becomes an action.

## MVP scope

This MVP intentionally does **not** implement a full chat UI, background agent, automatic API executor, or automatic external side effects.

It focuses on:

1. Intent creation
2. Prompt Package generation
3. Manual Client Executor workflow
4. LLM result import
5. Action Proposal parsing
6. Harness policy decisions
7. Review queue
8. Audit trail
9. Integrity checks

## Design principles

Abyss is guided by five system-level design principles:

1. Progressive disclosure
2. High information density
3. Low cognitive load
4. Modular decoupling
5. Extensibility first

The canonical structured rules live in `rules/design_principles.yaml`; the highest-level commitments live in `ABYSS_CONSTITUTION.md`.

## Quick start

Install once in editable mode so Abyss can be run from any directory:

```powershell
python -m pip install -e C:\Users\violinapeng\Documents\abyss
```

Then run either style from any directory:

```powershell
abyss status
python -m abyss_cli status
```

From this repository root, direct module execution also works without installation:

```powershell
python -m abyss_cli intent new "总结当前 git diff，生成组内同步说明"
python -m abyss_cli prompt build latest --copy
python -m abyss_cli check
```

## Manual LLM loop

1. Create an intent.
2. Build a prompt package.
3. Paste the generated prompt into Knot / Claude / ChatGPT / Cursor.
4. Save the LLM response to a local markdown file.
5. Import it:

```powershell
python -m abyss_cli result import path\to\response.md --intent latest
```

If the response contains action proposals, Abyss parses them into `process/actions/` and runs the Harness policy gate.

## Action proposal format

LLM responses may include fenced action proposals:

```yaml
```abyss-action
capability: fs.write
operation: create
path: artifacts/drafts/example.md
reason: Save a draft summary.
risk_estimate: L2
```
```

## Repository layout

```text
abyss/
├── ABYSS_CONSTITUTION.md
├── README.md
├── rules/
├── prompts/
├── process/
├── audit/
├── artifacts/
└── abyss_cli/
```

## Data format note

MVP structured records use `.yaml` filenames with JSON-compatible YAML content. This keeps the MVP dependency-free while preserving a future migration path to richer YAML.
