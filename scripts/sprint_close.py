#!/usr/bin/env python3
"""Sprint Close.

Generates a sprint close report and optionally:
- Transitions remaining issues
- Publishes a Confluence report
- Logs a summary to the sprint log issue
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cli import build_arg_parser, resolve_dry_run
from src.client import JiraClient
from src.config import load_agent_config, load_jql_templates, render_jql, validate_credentials
from src.confluence import generate_sprint_report_md, publish_to_confluence


def main() -> None:
    parser = build_arg_parser("Generate sprint close report and optionally transition issues")
    args = parser.parse_args()
    dry_run = resolve_dry_run(args)

    config = load_agent_config()
    jql_templates = load_jql_templates()

    if not dry_run:
        validate_credentials()

    client = JiraClient(base_url=config["jira_base_url"], dry_run=dry_run)

    print("=" * 60)
    print("SPRINT CLOSE")
    print("=" * 60)

    sprint = client.get_active_sprint(config["board_id"])
    sprint_name = "Unknown Sprint"
    if sprint:
        sprint_name = sprint.get("name", "Unknown Sprint")
        print(f"\nActive Sprint: {sprint_name}")
        print(f"  State: {sprint.get('state', 'Unknown')}")
        print(f"  End Date: {sprint.get('endDate', 'N/A')}")
    else:
        print("\n[INFO] No active sprint found (dry-run or no sprint active).")

    write_count = 0
    max_writes = args.max_writes

    print("\n--- Completed Issues ---")
    done_issues = []
    jql = jql_templates.get("done_issues", "")
    if jql:
        jql = render_jql(jql, config)
        done_issues = client.search_issues(jql)
        if done_issues:
            for issue in done_issues:
                key = issue["key"]
                summary = issue["fields"].get("summary", "")
                print(f"  {key}: {summary}")
        else:
            print("  No completed issues.")
    else:
        print("  [SKIP] No JQL template for done_issues.")

    print("\n--- Incomplete Issues ---")
    not_done_issues = []
    jql = jql_templates.get("not_done_issues", "")
    if jql:
        jql = render_jql(jql, config)
        not_done_issues = client.search_issues(jql)
        if not_done_issues:
            for issue in not_done_issues:
                key = issue["key"]
                summary = issue["fields"].get("summary", "")
                status = issue["fields"].get("status", {}).get("name", "Unknown")
                print(f"  {key}: {summary} (Status: {status})")
                if args.apply_transitions and (max_writes is None or write_count < max_writes):
                    transitions = client.get_transitions(key)
                    backlog_transition = next(
                        (t for t in transitions if t.get("name", "").lower() in ("backlog", "to do")),
                        None,
                    )
                    if backlog_transition:
                        print(f"    -> Transitioning {key} to {backlog_transition['name']}")
                        client.transition_issue(key, backlog_transition["id"])
                        write_count += 1
        else:
            print("  All issues completed!")
    else:
        print("  [SKIP] No JQL template for not_done_issues.")

    stale_issues = []
    jql = jql_templates.get("stale_issues", "")
    if jql:
        jql = render_jql(jql, config)
        stale_issues = client.search_issues(jql)

    print("\n--- Sprint Report ---")
    report_md = generate_sprint_report_md(
        sprint_name=sprint_name,
        completed=done_issues,
        not_completed=not_done_issues,
        stale=stale_issues,
    )
    print(report_md)

    if config.get("confluence_space_key"):
        print("\n--- Confluence Publishing ---")
        publish_to_confluence(
            space_key=config["confluence_space_key"],
            title=f"Sprint Report: {sprint_name}",
            markdown_content=report_md,
            base_url=config.get("jira_base_url"),
        )

    if config.get("sprint_log_issue_key"):
        log_key = config["sprint_log_issue_key"]
        print(f"\n--- Logging to {log_key} ---")
        if args.apply_comments and (max_writes is None or write_count < max_writes):
            summary = (
                f"Sprint '{sprint_name}' closed. "
                f"Completed: {len(done_issues)}, "
                f"Incomplete: {len(not_done_issues)}, "
                f"Stale: {len(stale_issues)}."
            )
            client.add_comment(log_key, f"[Sprint Agent] {summary}")
            write_count += 1
        else:
            print(f"  [dry-run] Would log sprint summary to {log_key}")

    print(f"\nWrites performed: {write_count}")
    if dry_run:
        print("[DRY-RUN] No changes were made.")
    print("=" * 60)


if __name__ == "__main__":
    main()
