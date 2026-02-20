#!/usr/bin/env python3
"""Workflow Guardrails.

Enforces workflow rules on sprint issues:
- Detects backward transitions (e.g., Done -> In Progress)
- Flags issues that skip statuses
- Optionally comments on violating issues
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cli import build_arg_parser, resolve_dry_run
from src.client import JiraClient
from src.config import load_agent_config, load_jql_templates, render_jql, validate_credentials

STATUS_ORDER = {
    "Open": 0,
    "To Do": 0,
    "In Progress": 1,
    "In Review": 2,
    "Done": 3,
}


def check_backward_transitions(issues: list) -> list:
    violations = []
    for issue in issues:
        key = issue["key"]
        fields = issue.get("fields", {})
        status_name = fields.get("status", {}).get("name", "Unknown")
        comments = fields.get("comment", {}).get("comments", [])

        for comment in comments:
            body_content = comment.get("body", {}).get("content", [])
            for block in body_content:
                for item in block.get("content", []):
                    text = item.get("text", "")
                    if "moved from" in text.lower() or "transitioned from" in text.lower():
                        violations.append(
                            {
                                "key": key,
                                "status": status_name,
                                "detail": text.strip(),
                            }
                        )
    return violations


def detect_unassigned_in_progress(issues: list) -> list:
    results = []
    for issue in issues:
        fields = issue.get("fields", {})
        status = fields.get("status", {}).get("name", "")
        assignee = fields.get("assignee")
        if status == "In Progress" and not assignee:
            results.append(issue)
    return results


def main() -> None:
    parser = build_arg_parser("Enforce workflow guardrails on sprint issues")
    args = parser.parse_args()
    dry_run = resolve_dry_run(args)

    config = load_agent_config()
    jql_templates = load_jql_templates()

    if not dry_run:
        validate_credentials()

    client = JiraClient(base_url=config["jira_base_url"], dry_run=dry_run)

    print("=" * 60)
    print("WORKFLOW GUARDRAILS")
    print("=" * 60)

    sprint = client.get_active_sprint(config["board_id"])
    if sprint:
        print(f"\nActive Sprint: {sprint.get('name', 'Unknown')}")
    else:
        print("\n[INFO] No active sprint found (dry-run or no sprint active).")

    write_count = 0
    max_writes = args.max_writes

    print("\n--- Checking All Sprint Issues ---")
    jql = jql_templates.get("active_sprint_issues", "")
    if jql:
        jql = render_jql(jql, config)
        issues = client.search_issues(jql)
        print(f"  Found {len(issues)} issues in active sprint.")

        print("\n--- Backward Transition Violations ---")
        violations = check_backward_transitions(issues)
        if violations:
            for v in violations:
                print(f"  {v['key']} (status={v['status']}): {v['detail']}")
                if args.apply_comments and (max_writes is None or write_count < max_writes):
                    client.add_comment(
                        v["key"],
                        "[Sprint Agent] Potential backward transition detected. "
                        "Please verify this status change is intentional.",
                    )
                    write_count += 1
        else:
            print("  No backward transition violations detected.")

        print("\n--- Unassigned In-Progress Issues ---")
        unassigned = detect_unassigned_in_progress(issues)
        if unassigned:
            for issue in unassigned:
                key = issue["key"]
                summary = issue["fields"].get("summary", "")
                print(f"  {key}: {summary}")
                if args.apply_comments and (max_writes is None or write_count < max_writes):
                    client.add_comment(
                        key,
                        "[Sprint Agent] This issue is In Progress but has no assignee. "
                        "Please assign someone.",
                    )
                    write_count += 1
        else:
            print("  All in-progress issues have assignees.")

        print("\n--- Status Distribution ---")
        status_counts: dict = {}
        for issue in issues:
            status = issue.get("fields", {}).get("status", {}).get("name", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
    else:
        print("  [SKIP] No JQL template for active_sprint_issues.")

    print(f"\nWrites performed: {write_count}")
    if dry_run:
        print("[DRY-RUN] No changes were made.")
    print("=" * 60)


if __name__ == "__main__":
    main()
