from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .agent_runner import run_agent, run_harness_changeset_review, run_harness_review
from .audit import append_event
from .brain import render_brain_brief
from .changeset import apply_changeset, dry_run_changeset, import_changeset, list_changesets, load_changeset, render_record, set_changeset_status
from .data_sync import data_pull, data_push, data_status, init_data_repo
from .direct_auth import authorize_direct_modification, direct_auth_status, init_direct_auth, list_direct_authorizations
from .disclosure import audit_context_manifest, build_disclosure_plan, render_disclosure_audit, render_disclosure_plan
from .evolution import approve_proposal, create_change_request, create_proposal_from_request, finalize_direct_modification_mode, governance_status, list_evolution_records, record_to_json, reject_proposal, run_evolution_smoke, show_evolution_record
from .external_collab import create_external_feedback_card, render_feedback_card_summary
from .fsm import fsm_tick, fsm_watch
from .harness import render_harness_json, render_harness_markdown
from .health import render_provider_health_json
from .integrity import run_checks
from .intent import INTENTS_DIR, create_intent
from .llm_executor import run_llm
from .owner import approve_owner_item, list_owner_items, reject_owner_item, render_owner_item
from .prompt_builder import build_external_developer_prompt, build_prompt
from .request_envelope import load_request_envelope, normalize_request_envelope, render_json as render_request_json, validate_request_envelope
from .request_rules import detect_governance_core_scope, governance_core_surfaces, list_request_type_definitions, validate_request_rules_config
from .rule_registry import list_rule_sources, render_rule_sources_json, render_validation_json, validate_rule_sources


from .result import import_result
from .review import REVIEWS_DIR, pending_reviews, set_review_status
from .insight import render_insight_snapshot_json
from .summary import render_summary
from .utils import latest_record, read_record, repo_root, resolve_record_arg, run_git
from .workflow import list_reports, list_workflows, load_report, render_json, retry_workflow, start_workflow, workflow_run_until_wait, workflow_tick, workflow_watch



def cmd_status(_: argparse.Namespace) -> None:
    print(f"Abyss MVP {__version__}")
    print("Governed AI orchestration system - CLI kernel")
    print(f"repo: {repo_root()}")
    print(run_git(["status", "--short", "--branch"], allow_fail=True))

def cmd_intent_new(args: argparse.Namespace) -> None:
    record = create_intent(args.goal, mode=args.mode)
    print(record["id"])
    path = INTENTS_DIR / f"{record['id']}.yaml"
    print(f"created: {path.relative_to(repo_root())}")


def cmd_intent_list(_: argparse.Namespace) -> None:
    for path in sorted(INTENTS_DIR.glob("*.yaml")) if INTENTS_DIR.exists() else []:
        record = read_record(path)
        print(f"{record.get('id')} [{record.get('status')}] {record.get('goal')}")


def cmd_prompt_build(args: argparse.Namespace) -> None:
    intent_path = resolve_record_arg(INTENTS_DIR, args.intent, "intent")
    path = build_prompt(intent_path, include_git_diff=args.git_diff, copy=args.copy)
    print(f"built: {path.relative_to(repo_root())}")
    if args.copy:
        print("copied to clipboard")


def cmd_prompt_build_external(args: argparse.Namespace) -> None:
    path = build_external_developer_prompt(args.objective, details=args.details or "", copy=args.copy)
    print(f"built external developer package: {path.relative_to(repo_root())}")
    if args.copy:
        print("copied to clipboard")


def cmd_result_import(args: argparse.Namespace) -> None:
    response_path = Path(args.path)
    if not response_path.is_absolute():
        response_path = (Path.cwd() / response_path).resolve()
    if not response_path.exists():
        raise SystemExit(f"Response file not found: {response_path}")

    intent_path = None
    if args.intent:
        intent_path = resolve_record_arg(INTENTS_DIR, args.intent, "intent")
    elif latest_record(INTENTS_DIR, "intent"):
        intent_path = latest_record(INTENTS_DIR, "intent")

    proposals = import_result(response_path, intent_path)
    print(f"imported result; action proposals found: {len(proposals)}")
    for proposal in proposals:
        print(f"- {proposal['id']} {proposal['policy']['risk']} {proposal['policy']['decision']} {proposal.get('capability')} {proposal.get('path')}")


def cmd_health_provider(args: argparse.Namespace) -> None:
    if not args.json:
        raise SystemExit("health provider requires --json flag")
    print(render_provider_health_json(args.provider))


def cmd_llm_run(args: argparse.Namespace) -> None:
    result_path, proposals = run_llm(args.prompt_package, args.provider)
    print(f"result saved: {result_path.relative_to(repo_root())}")
    print(f"imported result; action proposals found: {len(proposals)}")
    for proposal in proposals:
        print(f"- {proposal['id']} {proposal['policy']['risk']} {proposal['policy']['decision']} {proposal.get('capability')} {proposal.get('path')}")
    print("actions were proposed/imported only; no action was executed")


def cmd_review_list(_: argparse.Namespace) -> None:
    items = pending_reviews()
    if not items:
        print("no pending reviews")
        return
    for _, review in items:
        print(f"{review.get('id')} {review.get('risk')} action={review.get('action_id')} reason={review.get('reason')}")


def _resolve_review(value: str) -> Path:
    return resolve_record_arg(REVIEWS_DIR, value, "rev")


def cmd_review_approve(args: argparse.Namespace) -> None:
    review = set_review_status(_resolve_review(args.review), "approved")
    print(f"approved: {review.get('id')}")


def cmd_review_reject(args: argparse.Namespace) -> None:
    review = set_review_status(_resolve_review(args.review), "rejected")
    print(f"rejected: {review.get('id')}")


def cmd_check(_: argparse.Namespace) -> None:
    ok, messages = run_checks()
    for message in messages:
        print(message)
    append_event("integrity.check", "Integrity check completed", {"ok": ok, "messages": "; ".join(messages)})
    raise SystemExit(0 if ok else 1)


def cmd_fsm_tick(args: argparse.Namespace) -> None:
    tick = fsm_tick(reason=args.reason)
    print(f"{tick['id']} state={tick['state_after']} ok={tick['integrity_ok']}")
    for message in tick.get("messages", []):
        print(message)
    raise SystemExit(0 if tick.get("integrity_ok") else 1)


def cmd_fsm_watch(args: argparse.Namespace) -> None:
    fsm_watch(interval_seconds=args.interval, once=args.once)


def cmd_harness_export(args: argparse.Namespace) -> None:
    if args.format == "json":
        print(render_harness_json(), end="")
    else:
        print(render_harness_markdown())


def cmd_agent_run(args: argparse.Namespace) -> None:
    agent_run, specialized = run_agent(args.agent, target=args.target, provider=args.provider)
    print(f"agent run saved: {Path(agent_run['prompt_package']).relative_to(repo_root())}")
    print(f"result saved: {Path(agent_run['result_path']).relative_to(repo_root())}")
    if specialized:
        if specialized.get("schema") == "abyss.harness_review.v1":
            print(f"{specialized['schema']} {specialized['id']} verdict={specialized['verdict']} risk={specialized['risk_level']}")
        elif specialized.get("schema") == "abyss.change_set.v1":
            print(f"{specialized['schema']} {specialized['id']} status={specialized.get('status')} valid={specialized.get('validation', {}).get('ok')}")
        else:
            print(f"{specialized['schema']} {specialized['id']} verdict={specialized.get('verdict')} contract_valid={specialized.get('contract_valid')}")
    print("agent produced review/report/changeset proposal only; no action was executed")


def cmd_harness_review(args: argparse.Namespace) -> None:
    agent_run, review = run_harness_review(target=args.target, provider=args.provider)
    print(f"agent run: {agent_run['id']}")
    print(f"harness review: {review['id']} verdict={review['verdict']} risk={review['risk_level']} recommendation={review['recommendation']}")
    print(f"no_action_executed={review['no_action_executed']}")


def cmd_harness_review_changeset(args: argparse.Namespace) -> None:
    agent_run, review = run_harness_changeset_review(target=args.changeset, provider=args.provider)
    print(f"agent run: {agent_run['id']}")
    print(f"harness changeset review: {review['id']} target={review['target_id']} verdict={review['verdict']} risk={review['risk_level']} recommendation={review['recommendation']}")
    print(f"no_action_executed={review['no_action_executed']}")


def cmd_data_init(args: argparse.Namespace) -> None:
    config = init_data_repo(args.repo, path=args.path, branch=args.branch)
    print(f"configured data repo: {config['data_repo_path']}")


def cmd_data_status(_: argparse.Namespace) -> None:
    print(data_status())


def cmd_data_pull(_: argparse.Namespace) -> None:
    print(data_pull())


def cmd_data_push(args: argparse.Namespace) -> None:
    print(data_push(args.message))


def cmd_evolution_request(args: argparse.Namespace) -> None:
    record = create_change_request(args.summary, details=args.details or "")
    print(record["id"])
    print("status=inbox no_action_executed=True")


def cmd_evolution_list(_: argparse.Namespace) -> None:
    records = list_evolution_records()
    if not records:
        print("no evolution records")
        return
    for record in records:
        print(f"{record['kind']} {record['id']} [{record['status']}] {record['summary']} ({record['path']})")


def cmd_evolution_show(args: argparse.Namespace) -> None:
    path, record = show_evolution_record(args.record)
    print(f"path: {path.relative_to(repo_root())}")
    print(record_to_json(record))


def cmd_evolution_propose(args: argparse.Namespace) -> None:
    proposal = create_proposal_from_request(args.request)
    print(proposal["id"])
    print("status=needs_user_decision implementation_allowed=False no_action_executed=True")


def cmd_evolution_approve(args: argparse.Namespace) -> None:
    proposal = approve_proposal(args.proposal, add_to_roadmap=not args.no_roadmap)
    print(f"approved: {proposal['id']}")
    print(f"roadmap_entry={proposal.get('roadmap_entry')} implementation_allowed={proposal.get('implementation_allowed')}")


def cmd_evolution_reject(args: argparse.Namespace) -> None:
    proposal = reject_proposal(args.proposal, reason=args.reason or "")
    print(f"rejected: {proposal['id']}")
    print("implementation_allowed=False")


def cmd_evolution_status(_: argparse.Namespace) -> None:
    print(record_to_json(governance_status()))


def cmd_evolution_finalize(args: argparse.Namespace) -> None:
    state = finalize_direct_modification_mode(confirmed_by=args.confirmed_by)
    print("direct_modification_mode=disabled")
    print(record_to_json(state))


def cmd_evolution_smoke(args: argparse.Namespace) -> None:
    record = run_evolution_smoke(args.provider)
    print(f"{record['id']} status={record['status']} provider={record['provider']}")
    print(f"result: {Path(record['result_path']).relative_to(repo_root())}")
    print(f"no_action_executed={record['no_action_executed']}")
    raise SystemExit(0 if record["status"] == "passed" else 1)


def cmd_changeset_import(args: argparse.Namespace) -> None:
    source = Path(args.path)
    if not source.is_absolute():
        source = (Path.cwd() / source).resolve()
    record = import_changeset(source)
    print(f"imported: {record['id']} status={record.get('status')} valid={record.get('validation', {}).get('ok')}")


def cmd_changeset_list(_: argparse.Namespace) -> None:
    records = list_changesets()
    if not records:
        print("no changesets")
        return
    for record in records:
        line = f"{record.get('id')} [{record.get('status')}] roadmap={record.get('roadmap_id')} {record.get('summary', '')}"
        if record.get('status') == 'invalid':
            validation = record.get('validation')
            if isinstance(validation, dict):
                messages = validation.get('messages', [])
                if messages and isinstance(messages, list) and messages[0] != 'OK':
                    line += f" validation: {messages[0]}"
        print(line)


def cmd_changeset_show(args: argparse.Namespace) -> None:
    print(render_record(load_changeset(args.changeset)))


def cmd_changeset_approve(args: argparse.Namespace) -> None:
    record = set_changeset_status(args.changeset, "approved")
    print(f"approved: {record.get('id')}")


def cmd_changeset_reject(args: argparse.Namespace) -> None:
    record = set_changeset_status(args.changeset, "rejected", reason=args.reason or "")
    print(f"rejected: {record.get('id')}")


def cmd_changeset_dry_run(args: argparse.Namespace) -> None:
    report = dry_run_changeset(args.changeset)
    print(render_record(report))
    raise SystemExit(0 if report.get("ok") else 1)


def cmd_changeset_apply(args: argparse.Namespace) -> None:
    execution = apply_changeset(args.changeset)
    print(f"execution: {execution.get('id')} status={execution.get('status')}")
    raise SystemExit(0 if execution.get("status") == "succeeded" else 1)


def cmd_workflow_start(args: argparse.Namespace) -> None:
    workflow = start_workflow(args.proposal, provider=args.provider)
    print(render_json(workflow))


def cmd_workflow_tick(args: argparse.Namespace) -> None:
    print(render_json(workflow_tick(provider=args.provider, workflow_id=args.workflow)))


def cmd_workflow_run(args: argparse.Namespace) -> None:
    print(render_json(workflow_run_until_wait(provider=args.provider, workflow_id=args.workflow, max_steps=args.max_steps)))


def cmd_workflow_watch(args: argparse.Namespace) -> None:
    workflow_watch(provider=args.provider, workflow_id=args.workflow, interval_seconds=args.interval, once=args.once)


def cmd_workflow_retry(args: argparse.Namespace) -> None:
    print(render_json(retry_workflow(args.workflow, from_stage=args.from_stage)))

def cmd_workflow_supersede(args: argparse.Namespace) -> None:
    from .workflow import mark_workflow_superseded
    result = mark_workflow_superseded(
        args.workflow,
        corrected_changeset_id=args.changeset,
        corrected_workflow_id=args.corrected_workflow or "",
        confirmed_by="owner",
    )
    print(render_json(result))



def cmd_workflow_list(args: argparse.Namespace) -> None:
    workflows = list_workflows()
    if not workflows:
        print("no workflows")
        return
    status_filter = getattr(args, 'status', None)
    for workflow in workflows:
        status = workflow.get('status')
        last_event = (workflow.get('history') or [{}])[-1]
        details = last_event.get('details') or {}
        displayed_status = status
        if status == 'blocked' and last_event.get('event') == 'implementation_blocked' and details.get('category') == 'already_satisfied':
            displayed_status = 'satisfied_without_changes'
        if status_filter and displayed_status != status_filter:
            continue
        marker = ""
        if displayed_status == "done" and workflow.get("changeset_id"):
            marker = " [applied]"
        # Build metadata suffix for completed workflows
        metadata_parts = []
        if displayed_status == "done":
            changeset_id = workflow.get("changeset_id")
            report_id = workflow.get("report_id")
            if changeset_id:
                metadata_parts.append(f"changeset={changeset_id}")
            if report_id:
                metadata_parts.append(f"report={report_id}")
        metadata_suffix = " " + " ".join(metadata_parts) if metadata_parts else ""
        print(f"{workflow.get('id')} [{displayed_status}]{marker} roadmap={workflow.get('roadmap_id')} proposal={workflow.get('proposal_id')} {workflow.get('summary', '')}{metadata_suffix}")


def cmd_owner_inbox(args: argparse.Namespace) -> None:
    items = list_owner_items(include_closed=args.all)
    if not items:
        print("no owner inbox items")
        return
    for item in items:
        print(f"{item.get('id')} [{item.get('status')}] {item.get('type')} target={item.get('target_id')} workflow={item.get('workflow_id')} {item.get('title', '')}")


def cmd_owner_show(args: argparse.Namespace) -> None:
    from .owner import load_owner_item

    print(render_owner_item(load_owner_item(args.item)))


def cmd_owner_approve(args: argparse.Namespace) -> None:
    item = approve_owner_item(args.item, continue_workflow=not args.no_continue, provider=args.provider)
    print(render_owner_item(item))


def cmd_owner_reject(args: argparse.Namespace) -> None:
    item = reject_owner_item(args.item, reason=args.reason or "")
    print(render_owner_item(item))


def cmd_report_list(_: argparse.Namespace) -> None:
    reports = list_reports()
    if not reports:
        print("no workflow reports")
        return
    for report in reports:
        changeset_id = report.get('changeset_id', '')
        print(f"{report.get('id')} workflow={report.get('workflow_id')} roadmap={report.get('roadmap_id')} status={report.get('status')} changeset={changeset_id}")

def cmd_report_show(args: argparse.Namespace) -> None:
    print(render_json(load_report(args.report)))


def cmd_insight_snapshot(args: argparse.Namespace) -> None:
    if not args.json:
        raise SystemExit("insight snapshot requires --json flag")
    print(render_insight_snapshot_json())


def cmd_summary(args: argparse.Namespace) -> None:
    print(render_summary(include_check=args.check))


def cmd_brain_brief(args: argparse.Namespace) -> None:
    print(render_brain_brief(as_json=args.json))


def cmd_disclosure_audit(args: argparse.Namespace) -> None:
    audit = audit_context_manifest()
    if args.json:
        print(render_json(audit))
    else:
        print(render_disclosure_audit(audit))
    raise SystemExit(0 if audit.get("ok") else 1)


def cmd_disclosure_plan(args: argparse.Namespace) -> None:
    plan = build_disclosure_plan(args.task_type)
    if args.json:
        print(render_json(plan))
    else:
        print(render_disclosure_plan(plan))
    raise SystemExit(0 if plan.get("ok") else 1)


def cmd_direct_auth_init(args: argparse.Namespace) -> None:
    print(render_json(init_direct_auth(force=args.force, owner=args.owner)))


def cmd_direct_auth_authorize(args: argparse.Namespace) -> None:
    print(render_json(authorize_direct_modification(scope=args.scope, reason=args.reason, ttl_minutes=args.ttl_minutes, operator=args.operator)))


def cmd_direct_auth_list(args: argparse.Namespace) -> None:
    records = list_direct_authorizations(include_expired=args.all)
    if not records:
        print("no direct modification authorizations")
        return
    for record in records:
        print(f"{record.get('id')} [{record.get('status')}] scope={record.get('scope')} expires={record.get('expires_at')} reason={record.get('reason')}")


def cmd_direct_auth_status(_: argparse.Namespace) -> None:
    print(render_json(direct_auth_status()))


def cmd_external_import_result(args: argparse.Namespace) -> None:
    card = create_external_feedback_card(Path(args.path), task_id=args.task_id or "", source_platform=args.source_platform)
    print(render_feedback_card_summary(card))


def cmd_request_types(args: argparse.Namespace) -> None:
    errors = validate_request_rules_config()
    records = list_request_type_definitions(include_reserved=args.all)
    if args.json:
        print(render_request_json({
            "schema": "abyss.request_types_listing.v1",
            "ok": not errors,
            "errors": errors,
            "request_types": records,
            "no_action_executed": True,
            "no_approval_granted": True,
        }), end="")
        raise SystemExit(0 if not errors else 1)
    for record in records:
        print(f"{record.get('request_type')} [{record.get('status')}] route={record.get('default_route')} mutation={record.get('mutation_risk')}")
    if errors:
        for error in errors:
            print(error)
    raise SystemExit(0 if not errors else 1)


def cmd_request_normalize(args: argparse.Namespace) -> None:
    request_fields = {}
    for item in args.field or []:
        if "=" not in item:
            raise SystemExit(f"Invalid --field value, expected key=value: {item}")
        key, value = item.split("=", 1)
        request_fields[key] = value
    envelope = normalize_request_envelope(
        request_type=args.type,
        title=args.title,
        description=args.description or "",
        request_id=args.request_id or "",
        source=args.source,
        created_by=args.created_by,
        scope=args.scope or [],
        risk_level=args.risk_level,
        required_context=args.required_context or [],
        expected_artifacts=args.expected_artifact or [],
        validation_plan=args.validation or [],
        related_documents=args.related_document or [],
        notes=args.notes or "",
        request_fields=request_fields,
    )
    print(render_request_json(envelope), end="")
    validation = validate_request_envelope(envelope)
    raise SystemExit(0 if validation.get("ok") else 1)


def cmd_request_validate(args: argparse.Namespace) -> None:
    path = Path(args.path)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists():
        raise SystemExit(f"Request envelope file not found: {path}")
    envelope = load_request_envelope(path)
    validation = validate_request_envelope(envelope)
    if args.json:
        print(render_request_json(validation), end="")
    else:
        print(f"ok={validation.get('ok')}")
        for error in validation.get("errors", []):
            print(f"ERROR {error}")
        for warning in validation.get("warnings", []):
            print(f"WARNING {warning}")
        for field in validation.get("missing_required_fields", []):
            print(f"MISSING_FIELD {field}")
    raise SystemExit(0 if validation.get("ok") else 1)


def cmd_request_governance_core(args: argparse.Namespace) -> None:
    text_parts = [args.text or ""]
    for path_value in args.path or []:
        text_parts.append(path_value)
    detection = detect_governance_core_scope("\n".join(text_parts), paths=args.path or [])
    if args.json:
        print(render_request_json(detection), end="")
    else:
        print(f"requires_meta_governance={detection.get('requires_meta_governance')}")
        print(f"recommended_request_type={detection.get('recommended_request_type')}")
        print(f"recommended_route={detection.get('recommended_route')}")
        for keyword in detection.get("matched_keywords", []):
            print(f"MATCH_KEYWORD {keyword}")
        for surface, hits in detection.get("matched_surfaces", {}).items():
            print(f"MATCH_SURFACE {surface}: {', '.join(hits)}")
    raise SystemExit(0)


def cmd_request_governance_surfaces(args: argparse.Namespace) -> None:
    surfaces = governance_core_surfaces()
    if args.json:
        print(render_request_json({
            "schema": "abyss.governance_core_surfaces.v1",
            "surfaces": surfaces,
            "no_action_executed": True,
            "no_approval_granted": True,
        }), end="")
    else:
        for surface, paths in surfaces.items():
            print(f"{surface}: {', '.join(paths)}")
    raise SystemExit(0)

def cmd_rules_list(args: argparse.Namespace) -> None:
    if args.json:
        print(render_rule_sources_json())
    else:
        sources = list_rule_sources()
        if not sources:
            print("no rule sources declared")
            return
        for source in sources:
            print(f"{source.get('name')} files={','.join(source.get('source_files', []))} consumers={','.join(source.get('consumers', []))}")
    raise SystemExit(0)


def cmd_rules_validate(args: argparse.Namespace) -> None:
    if args.json:
        print(render_validation_json())
    else:
        result = validate_rule_sources()
        print(f"ok={result.get('ok')} entries_checked={result.get('entries_checked')}")
        for error in result.get("errors", []):
            print(f"ERROR {error}")
        for warning in result.get("warnings", []):
            print(f"WARNING {warning}")
    result = validate_rule_sources()
    raise SystemExit(0 if result.get("ok") else 1)



def build_parser() -> argparse.ArgumentParser:


    parser = argparse.ArgumentParser(prog="abyss", description="Abyss MVP CLI")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("status")
    p.set_defaults(func=cmd_status)

    p_intent = sub.add_parser("intent")
    intent_sub = p_intent.add_subparsers(required=True)
    p = intent_sub.add_parser("new")
    p.add_argument("goal")
    p.add_argument("--mode", default="assisted_prompt", choices=["assisted_prompt", "discussion_only", "git_diff_summary"])
    p.set_defaults(func=cmd_intent_new)
    p = intent_sub.add_parser("list")
    p.set_defaults(func=cmd_intent_list)

    p_prompt = sub.add_parser("prompt")
    prompt_sub = p_prompt.add_subparsers(required=True)
    p = prompt_sub.add_parser("build")
    p.add_argument("intent", help="intent id, filename, prefix, or latest")
    p.add_argument("--git-diff", action="store_true", help="include git diff context")
    p.add_argument("--copy", action="store_true", help="copy prompt package to clipboard on Windows")
    p.set_defaults(func=cmd_prompt_build)
    p = prompt_sub.add_parser("build-external", help="build a governed external model collaboration package")
    p.add_argument("objective", help="external model task objective")
    p.add_argument("--details", default="", help="additional task details or constraints")
    p.add_argument("--copy", action="store_true", help="copy prompt package to clipboard on Windows")
    p.set_defaults(func=cmd_prompt_build_external)

    p_result = sub.add_parser("result")
    result_sub = p_result.add_subparsers(required=True)
    p = result_sub.add_parser("import")
    p.add_argument("path")
    p.add_argument("--intent", default=None, help="intent id, filename, prefix, or latest")
    p.set_defaults(func=cmd_result_import)

    p_health = sub.add_parser("health")
    health_sub = p_health.add_subparsers(required=True)
    p = health_sub.add_parser("provider", help="call the configured real provider and report read-only health JSON")
    p.add_argument("--provider", default="cli", help="provider name configured in rules/llm_providers.yaml or .local/llm_providers.json")
    p.add_argument("--json", action="store_true", help="output as JSON (required)")
    p.set_defaults(func=cmd_health_provider)

    p_llm = sub.add_parser("llm")
    llm_sub = p_llm.add_subparsers(required=True)
    p = llm_sub.add_parser("run")
    p.add_argument("prompt_package", help="prompt package id, filename, path, prefix, or latest")
    p.add_argument("--provider", required=True, help="provider name configured in rules/llm_providers.yaml or .local/llm_providers.json")
    p.set_defaults(func=cmd_llm_run)

    p_review = sub.add_parser("review")
    review_sub = p_review.add_subparsers(required=True)
    p = review_sub.add_parser("list")
    p.set_defaults(func=cmd_review_list)
    p = review_sub.add_parser("approve")
    p.add_argument("review")
    p.set_defaults(func=cmd_review_approve)
    p = review_sub.add_parser("reject")
    p.add_argument("review")
    p.set_defaults(func=cmd_review_reject)

    p = sub.add_parser("check")
    p.set_defaults(func=cmd_check)

    p_fsm = sub.add_parser("fsm")
    fsm_sub = p_fsm.add_subparsers(required=True)
    p = fsm_sub.add_parser("tick")
    p.add_argument("--reason", default="manual")
    p.set_defaults(func=cmd_fsm_tick)
    p = fsm_sub.add_parser("watch")
    p.add_argument("--interval", type=int, default=300, help="seconds between ticks; minimum enforced by fsm module")
    p.add_argument("--once", action="store_true", help="run one watch tick and exit")
    p.set_defaults(func=cmd_fsm_watch)

    p_harness = sub.add_parser("harness")
    harness_sub = p_harness.add_subparsers(required=True)
    p = harness_sub.add_parser("export")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p.set_defaults(func=cmd_harness_export)
    p = harness_sub.add_parser("review")
    p.add_argument("target", nargs="?", default="latest", help="action proposal id, filename, prefix, or latest")
    p.add_argument("--provider", default=None, help="override provider configured for the harness agent")
    p.set_defaults(func=cmd_harness_review)
    p = harness_sub.add_parser("changeset-review")
    p.add_argument("changeset", nargs="?", default="latest", help="changeset id, filename, prefix, or latest")
    p.add_argument("--provider", default=None, help="override provider configured for the harness agent")
    p.set_defaults(func=cmd_harness_review_changeset)

    p_agent = sub.add_parser("agent")
    agent_sub = p_agent.add_subparsers(required=True)
    p = agent_sub.add_parser("run")
    p.add_argument("agent", choices=["harness", "self_evolution", "implementation"], help="agent id from rules/agents.yaml")
    p.add_argument("--target", default="latest", help="target record id, filename, prefix, or latest")
    p.add_argument("--provider", default=None, help="override provider configured for the agent")
    p.set_defaults(func=cmd_agent_run)

    p_data = sub.add_parser("data")
    data_sub = p_data.add_subparsers(required=True)
    p = data_sub.add_parser("init")
    p.add_argument("--repo", default=None, help="private user data Git repository URL; defaults to git@github-personal:CuSO4Ink/abyss-data.git")
    p.add_argument("--path", default=None, help="local clone path; defaults to ~/Documents/abyss-data")
    p.add_argument("--branch", default="main")
    p.set_defaults(func=cmd_data_init)
    p = data_sub.add_parser("status")
    p.set_defaults(func=cmd_data_status)
    p = data_sub.add_parser("pull")
    p.set_defaults(func=cmd_data_pull)
    p = data_sub.add_parser("push")
    p.add_argument("-m", "--message", default="sync abyss data")
    p.set_defaults(func=cmd_data_push)

    p_evolution = sub.add_parser("evolution")
    evolution_sub = p_evolution.add_subparsers(required=True)
    p = evolution_sub.add_parser("request")
    p.add_argument("summary")
    p.add_argument("--details", default="")
    p.set_defaults(func=cmd_evolution_request)
    p = evolution_sub.add_parser("list")
    p.set_defaults(func=cmd_evolution_list)
    p = evolution_sub.add_parser("show")
    p.add_argument("record", nargs="?", default="latest", help="request/proposal id, filename, prefix, or latest")
    p.set_defaults(func=cmd_evolution_show)
    p = evolution_sub.add_parser("propose")
    p.add_argument("request", help="request id, filename, prefix, or latest")
    p.set_defaults(func=cmd_evolution_propose)
    p = evolution_sub.add_parser("approve")
    p.add_argument("proposal", help="proposal id, filename, prefix, or latest")
    p.add_argument("--no-roadmap", action="store_true", help="approve the proposal record without adding it to ROADMAP.md")
    p.set_defaults(func=cmd_evolution_approve)
    p = evolution_sub.add_parser("reject")
    p.add_argument("proposal", help="proposal id, filename, prefix, or latest")
    p.add_argument("--reason", default="")
    p.set_defaults(func=cmd_evolution_reject)
    p = evolution_sub.add_parser("status")
    p.set_defaults(func=cmd_evolution_status)
    p = evolution_sub.add_parser("finalize-direct-mode")
    p.add_argument("--confirmed-by", default="user")
    p.set_defaults(func=cmd_evolution_finalize)
    p = evolution_sub.add_parser("smoke")
    p.add_argument("--provider", default="cli", help="standard LLM provider name")
    p.set_defaults(func=cmd_evolution_smoke)

    p_changeset = sub.add_parser("changeset")
    changeset_sub = p_changeset.add_subparsers(required=True)
    p = changeset_sub.add_parser("import")
    p.add_argument("path", help="path to an abyss.change_set.v1 JSON record")
    p.set_defaults(func=cmd_changeset_import)
    p = changeset_sub.add_parser("list")
    p.set_defaults(func=cmd_changeset_list)
    p = changeset_sub.add_parser("show")
    p.add_argument("changeset", help="changeset id, filename, prefix, or latest")
    p.set_defaults(func=cmd_changeset_show)
    p = changeset_sub.add_parser("approve")
    p.add_argument("changeset", help="changeset id, filename, prefix, or latest")
    p.set_defaults(func=cmd_changeset_approve)
    p = changeset_sub.add_parser("reject")
    p.add_argument("changeset", help="changeset id, filename, prefix, or latest")
    p.add_argument("--reason", default="")
    p.set_defaults(func=cmd_changeset_reject)
    p = changeset_sub.add_parser("dry-run")
    p.add_argument("changeset", help="changeset id, filename, prefix, or latest")
    p.set_defaults(func=cmd_changeset_dry_run)
    p = changeset_sub.add_parser("apply")
    p.add_argument("changeset", help="changeset id, filename, prefix, or latest")
    p.set_defaults(func=cmd_changeset_apply)

    p_workflow = sub.add_parser("workflow")
    workflow_sub = p_workflow.add_subparsers(required=True)
    p = workflow_sub.add_parser("start")
    p.add_argument("proposal", nargs="?", default="latest", help="approved proposal id, filename, prefix, or latest")
    p.add_argument("--provider", default="cli")
    p.set_defaults(func=cmd_workflow_start)
    p = workflow_sub.add_parser("tick")
    p.add_argument("workflow", nargs="?", default=None, help="workflow id, filename, prefix, or latest active workflow")
    p.add_argument("--provider", default=None)
    p.set_defaults(func=cmd_workflow_tick)
    p = workflow_sub.add_parser("run")
    p.add_argument("workflow", nargs="?", default=None, help="workflow id, filename, prefix, or latest active workflow")
    p.add_argument("--provider", default=None)
    p.add_argument("--max-steps", type=int, default=12)
    p.set_defaults(func=cmd_workflow_run)
    p = workflow_sub.add_parser("watch")
    p.add_argument("workflow", nargs="?", default=None, help="workflow id, filename, prefix, or latest active workflow")
    p.add_argument("--provider", default=None)
    p.add_argument("--interval", type=int, default=300)
    p.add_argument("--once", action="store_true")
    p.set_defaults(func=cmd_workflow_watch)
    p = workflow_sub.add_parser("retry")
    p.add_argument("workflow", help="workflow id, filename, prefix, or latest")
    p.add_argument("--from-stage", choices=["implementation", "changeset", "harness_review"], default="implementation")
    p.set_defaults(func=cmd_workflow_retry)
    p = workflow_sub.add_parser("supersede", help="mark a blocked/failed workflow as superseded by a corrected applied changeset (owner confirmation)")
    p.add_argument("workflow", help="workflow id, filename, prefix, or latest")
    p.add_argument("--changeset", required=True, help="applied corrected changeset id that completed the same roadmap item")
    p.add_argument("--corrected-workflow", default=None, help="optional workflow id that produced the corrected changeset")
    p.set_defaults(func=cmd_workflow_supersede)
    p = workflow_sub.add_parser("list")
    p.add_argument("--status", default=None, help="filter workflows by displayed status (e.g. done, failed, blocked, rejected, superseded, satisfied_without_changes, implementation_pending, waiting_owner_approval)")
    p.set_defaults(func=cmd_workflow_list)

    p_owner = sub.add_parser("owner")
    owner_sub = p_owner.add_subparsers(required=True)
    p = owner_sub.add_parser("inbox")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_owner_inbox)
    p = owner_sub.add_parser("show")
    p.add_argument("item", help="owner inbox item id, filename, prefix, or latest")
    p.set_defaults(func=cmd_owner_show)
    p = owner_sub.add_parser("approve")
    p.add_argument("item", help="owner inbox item id, filename, prefix, or latest")
    p.add_argument("--provider", default=None)
    p.add_argument("--no-continue", action="store_true", help="only approve; do not automatically continue workflow")
    p.set_defaults(func=cmd_owner_approve)
    p = owner_sub.add_parser("reject")
    p.add_argument("item", help="owner inbox item id, filename, prefix, or latest")
    p.add_argument("--reason", default="")
    p.set_defaults(func=cmd_owner_reject)

    p_report = sub.add_parser("report")
    report_sub = p_report.add_subparsers(required=True)
    p = report_sub.add_parser("list")
    p.set_defaults(func=cmd_report_list)
    p = report_sub.add_parser("show")
    p.add_argument("report", help="workflow report id, filename, prefix, or latest")
    p.set_defaults(func=cmd_report_show)

    p_direct_auth = sub.add_parser("direct-auth")
    direct_auth_sub = p_direct_auth.add_subparsers(required=True)
    p = direct_auth_sub.add_parser("init", help="initialize or rotate the local direct modification authorization secret")
    p.add_argument("--force", action="store_true", help="rotate an existing secret")
    p.add_argument("--owner", default="user")
    p.set_defaults(func=cmd_direct_auth_init)
    p = direct_auth_sub.add_parser("authorize", help="create a time-limited direct modification authorization ticket")
    p.add_argument("--scope", choices=["bootstrap_fix", "diagnostics", "emergency_repair"], required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--ttl-minutes", type=int, default=30)
    p.add_argument("--operator", default="user")
    p.set_defaults(func=cmd_direct_auth_authorize)
    p = direct_auth_sub.add_parser("list")
    p.add_argument("--all", action="store_true")
    p.set_defaults(func=cmd_direct_auth_list)
    p = direct_auth_sub.add_parser("status")
    p.set_defaults(func=cmd_direct_auth_status)

    p_external = sub.add_parser("external")
    external_sub = p_external.add_subparsers(required=True)
    p = external_sub.add_parser("import-result", help="import external model output as a candidate feedback card")
    p.add_argument("path", help="path to external model response markdown/text")
    p.add_argument("--task-id", default="", help="optional external task id or prompt package id")
    p.add_argument("--source-platform", default="external_model", help="external model platform name")
    p.set_defaults(func=cmd_external_import_result)

    p_insight = sub.add_parser("insight")
    insight_sub = p_insight.add_subparsers(required=True)
    p = insight_sub.add_parser("snapshot", help="emit a read-only insight snapshot as JSON")
    p.add_argument("--json", action="store_true", help="output as JSON (required)")
    p.set_defaults(func=cmd_insight_snapshot)

    p_brain = sub.add_parser("brain")
    brain_sub = p_brain.add_subparsers(required=True)
    p = brain_sub.add_parser("brief", help="render a read-only Brain Agent v0 status brief")
    p.add_argument("--json", action="store_true", help="render the brief as JSON")
    p.set_defaults(func=cmd_brain_brief)

    p_disclosure = sub.add_parser("disclosure")
    disclosure_sub = p_disclosure.add_subparsers(required=True)
    p = disclosure_sub.add_parser("audit", help="audit context_manifest disclosure levels without changing context pack behavior")
    p.add_argument("--json", action="store_true", help="render the audit as JSON")
    p.set_defaults(func=cmd_disclosure_audit)
    p = disclosure_sub.add_parser("plan", help="render the read-only disclosure plan for a task type")
    p.add_argument("task_type", help="task type from rules/context_manifest.yaml, or unknown for fallback")
    p.add_argument("--json", action="store_true", help="render the plan as JSON")
    p.set_defaults(func=cmd_disclosure_plan)

    p_request = sub.add_parser("request", help="work with normalized Request Envelope semantics")
    request_sub = p_request.add_subparsers(required=True)
    p = request_sub.add_parser("types", help="list canonical request types")
    p.add_argument("--all", action="store_true", help="include reserved request types")
    p.add_argument("--json", action="store_true", help="render the type list as JSON")
    p.set_defaults(func=cmd_request_types)
    p = request_sub.add_parser("normalize", help="build a Request Envelope candidate without creating a workflow")
    p.add_argument("--type", required=True, help="canonical request_type, e.g. maintenance_request")
    p.add_argument("--title", required=True, help="request title / user intent summary")
    p.add_argument("--description", default="")
    p.add_argument("--request-id", default="", help="explicit request id; omitted output is a candidate and not persisted")
    p.add_argument("--source", default="cli")
    p.add_argument("--created-by", default="owner")
    p.add_argument("--scope", action="append", default=[])
    p.add_argument("--risk-level", default="medium")
    p.add_argument("--required-context", action="append", default=[])
    p.add_argument("--expected-artifact", action="append", default=[])
    p.add_argument("--validation", action="append", default=[])
    p.add_argument("--related-document", action="append", default=[])
    p.add_argument("--field", action="append", default=[], help="type-specific required field as key=value; repeatable")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_request_normalize)
    p = request_sub.add_parser("validate", help="validate a Request Envelope JSON/YAML-compatible file")
    p.add_argument("path")
    p.add_argument("--json", action="store_true", help="render validation as JSON")
    p.set_defaults(func=cmd_request_validate)
    p = request_sub.add_parser("governance-core", help="detect whether text or paths touch governance-core surfaces")
    p.add_argument("--text", default="")
    p.add_argument("--path", action="append", default=[])
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_request_governance_core)
    p = request_sub.add_parser("governance-surfaces", help="list protected governance-core surfaces")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_request_governance_surfaces)
    p_rules = sub.add_parser("rules", help="work with the Rule Source Registry")
    rules_sub = p_rules.add_subparsers(required=True)
    p = rules_sub.add_parser("list", help="list declared rule sources")
    p.add_argument("--json", action="store_true", help="render the rule sources as JSON")
    p.set_defaults(func=cmd_rules_list)
    p = rules_sub.add_parser("validate", help="validate the rule source registry")
    p.add_argument("--json", action="store_true", help="render validation as JSON")
    p.set_defaults(func=cmd_rules_validate)


    p = sub.add_parser("summary")


    p.add_argument("--check", action="store_true", help="include integrity check result")
    p.set_defaults(func=cmd_summary)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
