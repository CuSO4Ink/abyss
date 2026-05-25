from abyss_cli.context_pack import detect_task_type, build_context_pack

samples = {
    "P1": "probe P1 roadmap: already-satisfied tiny display change recent workflow summary changeset_id",
    "P2": "probe P2 roadmap: single-file CLI help text micro change argparse help output",
    "P3": "probe P3 roadmap: two-module status display boundary workflow/summary status display",
    "P4": "probe P4 roadmap: governance-adjacent bounded validation wording workflow/summary status display without policy changes",
    "R030": "fix Context Broker coverage for robustness probe tasks context broker context pack manifest",
}

for name, text in samples.items():
    task_type = detect_task_type(text)
    pack = build_context_pack(
        agent_id="implementation",
        target_record={"summary": text},
        roadmap_id="TEST",
        proposal_id="TEST",
        task_type=task_type,
    )
    print(name)
    print("  task_type=", task_type)
    print("  files=", ", ".join(pack["files_included"]))
