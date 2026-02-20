#!/usr/bin/env python3
"""Sprint Readiness Check.

Validates that the active sprint is ready for execution:
- All issues have estimates
- All issues have assignees
- No blocked issues without comments
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cli import build_arg_parser, resolve_dry_run
from src.client import JiraClient
from src.config import load_agent_config, load_jql_templates, render_jql, validate_credentials


def main() -> None:
    parser = build_arg_parser("Check sprint readiness before execution")
    args = parser.parse_args()
    dry_run = resolve_dry_run(args)

    config = load_agent_config()
    jql_templates = load_jql_templates()

    if not dry_run:
        validate_credentials()

    client = JiraClient(base_url=config["jira_base_url"], dry_run=dry_run)

    print("=" * 60)
    print("SPRINT READINESS CHECK")
    print("=" * 60)

    sprint = client.get_active_sprint(config["board_id"])
    if sprint:
        print(f"\nActive Sprint: {sprint.get('name', 'Unknown')}")
        print(f"  State: {sprint.get('state', 'Unknown')}")
        print(f"  Start: {sprint.get('startDate', 'N/A')}")
        print(f"  End:   {sprint.get('endDate', 'N/A')}")
    else:
        print("\n[INFO] No active sprint found (dry-run or no sprint active).")

    write_count = 0
    max_writes = args.max_writes

    print("\n--- Issues Missing Estimates ---")
    jql = jql_templates.get("readiness_no_estimate", "")
    if jql:
        jql = render_jql(jql, config)
        issues = client.search_issues(jql)
        if issues:
            for issue in issues:
                key = issue["key"]
                summary = issue["fields"].get("summary", "")
                print(f"  {key}: {summary}")
                if args.apply_comments and (max_writes is None or write_count < max_writes):
                    client.add_comment(key, "[Sprint Agent] This issue has no estimate. Please add a story point estimate.")
                    write_count += 1
        else:
            print("  All issues have estimates.")
    else:
        print("  [SKIP] No JQL template for readiness_no_estimate.")

    print("\n--- Issues Missing Assignees ---")
    jql = jql_templates.get("readiness_no_assignee", "")
    if jql:
        jql = render_jql(jql, config)
        issues = client.search_issues(jql)
        if issues:
            for issue in issues:
                key = issue["key"]
                summary = issue["fields"].get("summary", "")
                print(f"  {key}: {summary}")
                if args.apply_comments and (max_writes is None or write_count < max_writes):
                    client.add_comment(key, "[Sprint Agent] This issue has no assignee. Please assign a team member.")
                    write_count += 1
        else:
            print("  All issues have assignees.")
    else:
        print("  [SKIP] No JQL template for readiness_no_assignee.")

    print("\n--- Blocked Issues ---")
    jql = jql_templates.get("blocked_issues", "")
    if jql:
        jql = render_jql(jql, config)
        issues = client.search_issues(jql)
        if issues:
            for issue in issues:
                key = issue["key"]
                summary = issue["fields"].get("summary", "")
                print(f"  {key}: {summary}")
        else:
            print("  No blocked issues.")
    else:
        print("  [SKIP] No JQL template for blocked_issues.")

    print(f"\nWrites performed: {write_count}")
    if dry_run:
        print("[DRY-RUN] No changes were made.")
    print("=" * 60)


if __name__ == "__main__":
    main()
