from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .audit import append_event
from .data_sync import data_pull, data_push, data_status, init_data_repo
from .integrity import run_checks
from .intent import INTENTS_DIR, create_intent
from .prompt_builder import build_prompt
from .result import import_result
from .review import pending_reviews, set_review_status
from .utils import latest_record, read_record, repo_root, resolve_record_arg, run_git


def cmd_status(_: argparse.Namespace) -> None:
    print(f"Abyss MVP {__version__}")
    print(f"repo: {repo_root()}")
    print(run_git(["status", "--short", "--branch"], allow_fail=True))


def cmd_intent_new(args: argparse.Namespace) -> None:
    record = create_intent(args.goal, mode=args.mode)
    print(record["id"])
    print(f"created: process/intents/{record['id']}.yaml")


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


def cmd_review_list(_: argparse.Namespace) -> None:
    items = pending_reviews()
    if not items:
        print("no pending reviews")
        return
    for _, review in items:
        print(f"{review.get('id')} {review.get('risk')} action={review.get('action_id')} reason={review.get('reason')}")


def _resolve_review(value: str) -> Path:
    return resolve_record_arg(repo_root() / "process" / "reviews", value, "rev")


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


def cmd_data_init(args: argparse.Namespace) -> None:
    config = init_data_repo(args.repo, path=args.path, branch=args.branch)
    print(f"configured data repo: {config['data_repo_path']}")


def cmd_data_status(_: argparse.Namespace) -> None:
    print(data_status())


def cmd_data_pull(_: argparse.Namespace) -> None:
    print(data_pull())


def cmd_data_push(args: argparse.Namespace) -> None:
    print(data_push(args.message))


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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()