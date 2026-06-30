"""Tests for Implementation Agent output-quality hardening.

These tests do not invoke a real provider and do not grant any execution or
approval authority. They only verify that the static role prompt and generated
prompt package contain the bounded contract guidance needed to reduce invalid
Implementation Agent output.
"""

from __future__ import annotations

from pathlib import Path

import abyss_cli.agent_runner as runner


REPO = Path(__file__).resolve().parents[1]


def test_static_implementation_prompt_contains_output_preflight_contract():
    text = (REPO / "prompts" / "agents" / "implementation_agent.md").read_text(encoding="utf-8")

    assert "## Internal preflight before output" in text
    assert "Target clarity" in text
    assert "Context sufficiency" in text
    assert "Contract completeness" in text
    assert "Patch locality" in text
    assert "Boundary safety" in text
    assert "Failure feedback" in text
    assert "Never force an edit-plan by guessing" in text
    assert "Treat `abyss-edit-plan` as a contract, not prose" in text
    assert "output `abyss-context-request` instead of a partial edit plan" in text
    assert "output `abyss-context-request` instead of a ChangeSet" in text


def test_generated_implementation_prompt_package_repeats_runtime_hardening(mini_repo, monkeypatch):
    target = mini_repo / "artifacts" / "drafts" / "target_record.json"
    target.write_text(
        "{\n"
        "  \"id\": \"evo_prop_prompt_hardening\",\n"
        "  \"roadmap_entry\": \"R_PROMPT\",\n"
        "  \"summary\": \"prompt hardening target\"\n"
        "}\n",
        encoding="utf-8",
    )
    role_prompt = mini_repo / "prompts" / "agents" / "implementation_agent.md"
    role_prompt.parent.mkdir(parents=True, exist_ok=True)
    role_prompt.write_text("# Role Prompt Stub\n", encoding="utf-8")

    monkeypatch.setattr(runner, "resolve_evolution_target", lambda value: target)
    monkeypatch.setattr(runner, "_latest_context_request_files", lambda proposal_id: [])
    monkeypatch.setattr(
        runner,
        "build_context_pack",
        lambda **kwargs: {
            "id": "ctx_prompt_hardening",
            "task_type": "implementation",
            "files_included": ["abyss_cli/example.py"],
            "files_missing": [],
            "modules_included": ["example"],
        },
    )
    monkeypatch.setattr(runner, "render_context_pack_summary", lambda pack: "Files included: abyss_cli/example.py")
    monkeypatch.setattr(runner, "render_context_pack_for_prompt", lambda pack: "## Repository Files\nabyss_cli/example.py\n")
    monkeypatch.setattr(runner, "_recent_implementation_evidence", lambda: {"invalid_changesets": [{"id": "chg_bad", "messages": ["placeholder_content"]}]})
    monkeypatch.setattr(runner, "_placeholder_format_feedback_constraints", lambda proposal_id: "")
    monkeypatch.setattr(runner, "append_event", lambda *args, **kwargs: None)

    prompt_path, _, _, metadata = runner._build_implementation_agent_prompt(
        {"role_prompt": "prompts/agents/implementation_agent.md"},
        target="evo_prop_prompt_hardening",
    )

    text = prompt_path.read_text(encoding="utf-8")
    assert metadata["context_pack_id"] == "ctx_prompt_hardening"
    assert "Implementation output preflight" in text
    assert "target clarity" in text
    assert "context sufficiency" in text
    assert "contract completeness" in text
    assert "patch locality" in text
    assert "boundary safety" in text
    assert "output `abyss-context-request` instead of guessing" in text
    assert "do not repeat it" in text
    assert "Treat `abyss-edit-plan` as a contract, not prose" in text
    assert "output `abyss-context-request` instead of a partial edit plan" in text
    assert "Do not approve, reject, apply, run commands, or claim execution" in text
