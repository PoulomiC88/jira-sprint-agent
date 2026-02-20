#!/usr/bin/env python3
"""Daily Sprint Execution.

Runs daily checks on the active sprint:
- Identifies stale issues (no updates in N days)
- Flags in-progress issues without assignees
- Summarizes sprint progress
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cli import build_arg_parser, resolve_dry_run
from src.client import JiraClient
from src.config import load_agent_config, load_jql_templates, render_jql, validate_credentials


def main() -> None:
    parser = build_arg_parser("Run daily sprint execution checks")
    args = parser.parse_args()
    dry_run = resolve_dry_run(args)

    config = load_agent_config()
    jql_templates = load_jql_templates()

    if not dry_run:
        validate_credentials()

    client = JiraClient(base_url=config["jira_base_url"], dry_run=dry_run)

    print("=" * 60)
    print("DAILY SPRINT EXECUTION")
    print("=" * 60)

    sprint = client.get_active_sprint(config["board_id"])
    if sprint:
        print(f"\nActive Sprint: {sprint.get('name', 'Unknown')}")
    else:
        print("\n[INFO] No active sprint found (dry-run or no sprint active).")

    write_count = 0
    max_writes = args.max_writes

    print("\n--- Sprint Progress ---")
    jql = jql_templates.get("active_sprint_issues", "")
    if jql:
        jql = render_jql(jql, config)
        all_issues = client.search_issues(jql)
        done = [i for i in all_issues if i.get("fields", {}).get("status", {}).get("name") == "Done"]
        in_progress = [i for i in all_issues if i.get("fields", {}).get("status", {}).get("name") == "In Progress"]
        todo = [i for i in all_issues if i.get("fields", {}).get("status", {}).get("name") in ("To Do", "Open")]
        other = [i for i in all_issues if i not in done and i not in in_progress and i not in todo]
        total = len(all_issues)
        print(f"  Total: {total}")
        print(f"  Done: {len(done)}")
        print(f"  In Progress: {len(in_progress)}")
        print(f"  To Do: {len(todo)}")
        if other:
            print(f"  Other: {len(other)}")
        if total > 0:
            pct = len(done) / total * 100
            print(f"  Completion: {pct:.0f}%")
    else:
        print("  [SKIP] No JQL template for active_sprint_issues.")

    print(f"\n--- Stale Issues (>{config.get('stale_days', 3)} days without update) ---")
    jql = jql_templates.get("stale_issues", "")
    if jql:
        jql = render_jql(jql, config)
        issues = client.search_issues(jql)
        if issues:
            for issue in issues:
                key = issue["key"]
                summary = issue["fields"].get("summary", "")
                updated = issue["fields"].get("updated", "N/A")
                status = issue["fields"].get("status", {}).get("name", "Unknown")
                print(f"  {key}: {summary} (status={status}, updated={updated})")
                if args.apply_comments and (max_writes is None or write_count < max_writes):
                    client.add_comment(
                        key,
                        f"[Sprint Agent] This issue has not been updated in {config.get('stale_days', 3)}+ days. "
                        "Please provide a status update.",
                    )
                    write_count += 1
        else:
            print("  No stale issues found.")
    else:
        print("  [SKIP] No JQL template for stale_issues.")

    print("\n--- In Progress Without Assignee ---")
    jql = jql_templates.get("in_progress_no_assignee", "")
    if jql:
        jql = render_jql(jql, config)
        issues = client.search_issues(jql)
        if issues:
            for issue in issues:
                key = issue["key"]
                summary = issue["fields"].get("summary", "")
                print(f"  {key}: {summary}")
                if args.apply_comments and (max_writes is None or write_count < max_writes):
                    client.add_comment(key, "[Sprint Agent] This issue is In Progress but has no assignee.")
                    write_count += 1
        else:
            print("  All in-progress issues have assignees.")
    else:
        print("  [SKIP] No JQL template for in_progress_no_assignee.")

    print(f"\nWrites performed: {write_count}")
    if dry_run:
        print("[DRY-RUN] No changes were made.")
    print("=" * 60)


if __name__ == "__main__":
    main()
