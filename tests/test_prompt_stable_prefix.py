from __future__ import annotations

import json

import abyss_cli.agent_runner as agent_runner
import abyss_cli.prompt_builder as prompt_builder


def _assert_before(text: str, earlier: str, later: str) -> None:
    assert earlier in text
    assert later in text
    assert text.index(earlier) < text.index(later)


def test_external_developer_prompt_places_stable_boundary_before_dynamic_task(mini_repo, monkeypatch):
    monkeypatch.setattr(
        prompt_builder,
        "build_context_pack",
        lambda **kwargs: {
            "id": "ctx_dynamic_001",
            "agent_id": "external_developer",
            "task_type": "external_collaboration",
            "files_included": [],
            "files_missing": [],
            "modules_included": [],
        },
    )
    monkeypatch.setattr(prompt_builder, "render_context_pack_summary", lambda pack: "summary")
    monkeypatch.setattr(prompt_builder, "render_context_pack_for_prompt", lambda pack: "## Repository Files\n\n[none]")

    path = prompt_builder.build_external_developer_prompt("dynamic objective", details="dynamic details")
    text = path.read_text(encoding="utf-8")

    _assert_before(text, "## Stable authority boundary", "## Run metadata")
    _assert_before(text, "## Stable required output", "## Task objective")
    _assert_before(text, "Do not bypass Harness, Owner, workflow, or executor boundaries.", "- prompt_package_id:")


def test_implementation_prompt_places_stable_contract_before_run_metadata_and_context(mini_repo, monkeypatch):
    target_path = mini_repo / "target_record.json"
    target_path.write_text(
        json.dumps(
            {
                "id": "evo_prop_dynamic",
                "roadmap_entry": "R123",
                "title": "dynamic target",
                "target_file": "abyss_cli/example.py",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(agent_runner, "resolve_evolution_target", lambda target: target_path)
    monkeypatch.setattr(
        agent_runner,
        "build_context_pack",
        lambda **kwargs: {
            "id": "ctx_dynamic_002",
            "agent_id": "implementation",
            "task_type": "implementation",
            "files_included": ["abyss_cli/example.py"],
            "files_missing": [],
            "modules_included": [],
        },
    )
    monkeypatch.setattr(agent_runner, "render_context_pack_summary", lambda pack: "Files included: abyss_cli/example.py")
    monkeypatch.setattr(agent_runner, "render_context_pack_for_prompt", lambda pack: "## Repository Files\n\n```python\npass\n```")
    monkeypatch.setattr(agent_runner, "_recent_implementation_evidence", lambda: [])
    monkeypatch.setattr(agent_runner, "_placeholder_format_feedback_constraints", lambda proposal_id: "")
    monkeypatch.setattr(
        agent_runner,
        "_safe_read",
        lambda path, limit=None: "ROLE PROMPT" if str(path).endswith("implementation_agent.md") else "STABLE TEXT",
    )

    spec = {"role_prompt": "prompts/agents/implementation_agent.md", "agent": "implementation"}
    prompt_path, _target_path, target_id, context_metadata = agent_runner._build_implementation_agent_prompt(spec, "latest")
    text = prompt_path.read_text(encoding="utf-8")

    assert target_id == "evo_prop_dynamic"
    assert context_metadata["context_pack_id"] == "ctx_dynamic_002"
    _assert_before(text, "## Stable agent registry spec", "## Run metadata")
    _assert_before(text, "## Stable implementation output contract", "- prompt_package_id:")
    _assert_before(text, "Do not produce `abyss-action` blocks.", "## Target approved evolution / roadmap record")
    _assert_before(text, "## Run metadata", "## Context Pack Summary")
    _assert_before(text, "## Target approved evolution / roadmap record", "## Repository Files")
