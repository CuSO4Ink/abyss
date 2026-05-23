from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .agent_runner import run_agent, run_harness_review
from .audit import append_event
from .data_sync import data_pull, data_push, data_status, init_data_repo
from .evolution import create_change_request, create_proposal_from_request, list_evolution_records, record_to_json, run_evolution_smoke, show_evolution_record
from .fsm import fsm_tick, fsm_watch
from .harness import render_harness_json, render_harness_markdown
from .integrity import run_checks
from .intent import INTENTS_DIR, create_intent
from .llm_executor import run_llm
from .prompt_builder import build_prompt
from .result import import_result
from .review import REVIEWS_DIR, pending_reviews, set_review_status
from .utils import latest_record, read_record, repo_root, resolve_record_arg, run_git


def cmd_status(_: argparse.Namespace) -> None:
    print(f"Abyss MVP {__version__}")
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
        else:
            print(f"{specialized['schema']} {specialized['id']} verdict={specialized.get('verdict')} contract_valid={specialized.get('contract_valid')}")
    print("agent produced review/report only; no action was executed")


def cmd_harness_review(args: argparse.Namespace) -> None:
    agent_run, review = run_harness_review(target=args.target, provider=args.provider)
    print(f"agent run: {agent_run['id']}")
    print(f"harness review: {review['id']} verdict={review['verdict']} risk={review['risk_level']} recommendation={review['recommendation']}")
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


def cmd_evolution_smoke(args: argparse.Namespace) -> None:
    record = run_evolution_smoke(args.provider)
    print(f"{record['id']} status={record['status']} provider={record['provider']}")
    print(f"result: {Path(record['result_path']).relative_to(repo_root())}")
    print(f"no_action_executed={record['no_action_executed']}")
    raise SystemExit(0 if record["status"] == "passed" else 1)


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

    p_result = sub.add_parser("result")
    result_sub = p_result.add_subparsers(required=True)
    p = result_sub.add_parser("import")
    p.add_argument("path")
    p.add_argument("--intent", default=None, help="intent id, filename, prefix, or latest")
    p.set_defaults(func=cmd_result_import)

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

    p_agent = sub.add_parser("agent")
    agent_sub = p_agent.add_subparsers(required=True)
    p = agent_sub.add_parser("run")
    p.add_argument("agent", choices=["harness", "self_evolution"], help="agent id from rules/agents.yaml")
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
    p = evolution_sub.add_parser("smoke")
    p.add_argument("--provider", default="cli", help="standard LLM provider name")
    p.set_defaults(func=cmd_evolution_smoke)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()