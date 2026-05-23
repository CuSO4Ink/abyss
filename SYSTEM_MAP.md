# Abyss System Map

## Entry commands

```powershell
abyss status
abyss intent new "<goal>"
abyss intent list
abyss prompt build latest --copy
abyss result import <response.md> --intent latest
abyss review list
abyss review approve <review>
abyss review reject <review>
abyss check
abyss data init|status|pull|push
```

## Core modules

- `abyss_cli/__main__.py` — CLI routing and command handlers.
- `abyss_cli/intent.py` — creates structured Intents.
- `abyss_cli/prompt_builder.py` — builds Prompt Packages from intents and context.
- `abyss_cli/result.py` — imports LLM output and extracts action proposals.
- `abyss_cli/policy.py` — interprets `rules/policy.yaml`; no independent policy truth.
- `abyss_cli/review.py` — manages pending human reviews.
- `abyss_cli/audit.py` — appends local runtime audit events.
- `abyss_cli/data_sync.py` — connects the private GitHub data repository.
- `abyss_cli/integrity.py` — checks repository structure and safety invariants.

## Data flow

```text
user goal
  -> intent record
  -> prompt package
  -> manual LLM response
  -> result import
  -> action proposal
  -> policy decision from rules/policy.yaml
  -> allow / review / deny
  -> audit event
```

## System directories

- `abyss_cli/` — implementation code.
- `rules/` — rule truth sources; especially `rules/policy.yaml`.
- `prompts/` — system and mode prompt templates.
- `artifacts/drafts/` — low-risk generated drafts.
- `process/*/.gitkeep` — process directory skeleton only.
- `audit/README.md` — audit directory skeleton documentation only.
- `ABYSS_CONSTITUTION.md`, `README.md`, `SYSTEM_MAP.md`, `pyproject.toml` — system docs/config.

## Runtime record directories

Runtime records are local machine state and do not belong in system Git.

- `.local/runtime/process/intents/`
- `.local/runtime/process/prompt_packages/`
- `.local/runtime/process/imports/`
- `.local/runtime/process/actions/`
- `.local/runtime/process/reviews/`
- `.local/runtime/audit/audit.md`

Future option:

- `abyss-data/runtime/` for selected syncable runtime records.

## User data directories

System repo keeps only placeholders/README files here.
Real synced user data lives in the private GitHub data repo.

- `user_data/` — Obsidian-first active notes: Markdown, wiki links, frontmatter.
- `user_data/Home.md` — human entry point for active areas.
- `user_data/_attachments/` — relative note assets.
- `storage/archive/` — inactive archived material.
- default private data repo: `git@github-personal:CuSO4Ink/abyss-data.git`
- default local data path: `~/Documents/abyss-data`

## Forbidden

- Do not commit real `process/*` runtime records to the system repo.
- Do not commit `audit/audit.md` to the system repo.
- Do not duplicate policy logic between `policy.py` and `rules/policy.yaml`.
- Do not put secrets, tokens, credentials, keys, or local caches in Git.
- Do not expose implementation or archive layers in default user retrieval.
- Do not put real Obsidian notes or bulk archives into the system repo.
