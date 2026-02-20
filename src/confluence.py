from typing import Optional


def generate_sprint_report_md(
    sprint_name: str,
    completed: list,
    not_completed: list,
    stale: list,
) -> str:
    lines = [f"# Sprint Report: {sprint_name}", ""]

    lines.append("## Completed Issues")
    if completed:
        for issue in completed:
            key = issue.get("key", "?")
            summary = issue.get("fields", {}).get("summary", "No summary")
            lines.append(f"- **{key}**: {summary}")
    else:
        lines.append("_No completed issues._")
    lines.append("")

    lines.append("## Not Completed")
    if not_completed:
        for issue in not_completed:
            key = issue.get("key", "?")
            summary = issue.get("fields", {}).get("summary", "No summary")
            status = issue.get("fields", {}).get("status", {}).get("name", "Unknown")
            lines.append(f"- **{key}**: {summary} (Status: {status})")
    else:
        lines.append("_All issues completed._")
    lines.append("")

    lines.append("## Stale Issues")
    if stale:
        for issue in stale:
            key = issue.get("key", "?")
            summary = issue.get("fields", {}).get("summary", "No summary")
            updated = issue.get("fields", {}).get("updated", "Unknown")
            lines.append(f"- **{key}**: {summary} (Last updated: {updated})")
    else:
        lines.append("_No stale issues._")
    lines.append("")

    return "\n".join(lines)


def publish_to_confluence(
    space_key: str,
    title: str,
    markdown_content: str,
    base_url: Optional[str] = None,
) -> None:
    print(f"  [stub] Would publish page '{title}' to Confluence space '{space_key}'")
    print(f"  [stub] Base URL: {base_url or 'not configured'}")
    print(f"  [stub] Content length: {len(markdown_content)} characters")
