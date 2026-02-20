import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_yaml(file_path: Path) -> Dict[str, Any]:
    with open(file_path, "r") as fh:
        return yaml.safe_load(fh) or {}


def load_agent_config(path: Optional[Path] = None) -> Dict[str, Any]:
    path = path or CONFIG_DIR / "agent.yml"
    cfg = load_yaml(path)
    required_keys = [
        "jira_base_url",
        "project_key",
        "board_id",
    ]
    missing = [k for k in required_keys if k not in cfg]
    if missing:
        print(f"ERROR: Missing required keys in {path}: {missing}", file=sys.stderr)
        sys.exit(1)
    cfg.setdefault("stale_days", 3)
    cfg.setdefault("confluence_space_key", None)
    cfg.setdefault("sprint_log_issue_key", None)
    return cfg


def load_jql_templates(path: Optional[Path] = None) -> Dict[str, str]:
    path = path or CONFIG_DIR / "jql.yml"
    data = load_yaml(path)
    return data.get("queries", {})


def render_jql(template: str, config: Dict[str, Any]) -> str:
    return template.format(
        project_key=config["project_key"],
        stale_days=config.get("stale_days", 3),
    )


def validate_credentials() -> None:
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_API_TOKEN")
    errors = []
    if not email:
        errors.append("JIRA_EMAIL")
    if not token:
        errors.append("JIRA_API_TOKEN")
    if errors:
        print(
            f"ERROR: Missing required environment variables: {', '.join(errors)}\n"
            "Set them before making API calls:\n"
            "  export JIRA_EMAIL='you@example.com'\n"
            "  export JIRA_API_TOKEN='your-api-token'",
            file=sys.stderr,
        )
        sys.exit(1)
