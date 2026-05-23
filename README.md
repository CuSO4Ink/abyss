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

## Layered data architecture

Abyss separates information into three layers:

1. **User data layer** — the default user-facing knowledge surface, primarily aligned with active Obsidian notes, current directions, working summaries, and decision records.
2. **Implementation layer** — the hidden-by-default system internals: code, prompts, rules, harness logic, process records, audit, schemas, and executors.
3. **Data storage layer** — the hidden-by-default archive for inactive, dormant, bulky, historical, or not-currently-useful material.

The implementation layer and data storage layer should not appear in the user's default information retrieval scope. When archived material becomes relevant, Abyss should retrieve a focused subset from storage and promote or materialize it into the user data layer with provenance, rather than exposing storage directly.

The user data layer is **Obsidian-first**. Use Markdown notes, YAML frontmatter, Obsidian wiki links like `[[Project Name]]`, relative attachments under `_attachments/`, and `Home.md` as the human entry point for active areas.

The canonical structured rules live in `rules/data_layers.yaml`.

## Multi-device sync

Abyss uses a separated single-user GitHub sync model:

1. **System repository** — this repository. It contains Abyss implementation, rules, prompts, process structure, and architecture documentation.
2. **GitHub private data repository** — `CuSO4Ink/abyss-data`. It contains the real `user_data/` and `storage/archive/` content used across devices.

This keeps the system implementation safe to sync or publish without mixing in personal Obsidian notes or archives.

After creating the GitHub private repository, configure it once per device:

```powershell
abyss data init
```

By default this uses:

```text
git@github-personal:CuSO4Ink/abyss-data.git
```

Optional custom local path:

```powershell
abyss data init --path C:\Users\violinapeng\Documents\abyss-data
```

Daily sync commands:

```powershell
abyss data status
abyss data pull
abyss data push -m "update active notes"
```

The local sync configuration is stored in `.local/data_sync.json`, which is ignored by Git and must not contain tokens, passwords, or private keys.

The canonical structured rules live in `rules/sync.yaml`.

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
