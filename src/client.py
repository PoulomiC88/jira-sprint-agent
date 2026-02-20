import os
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests


class JiraClient:
    def __init__(self, base_url: str, dry_run: bool = True) -> None:
        self.base_url = base_url.rstrip("/")
        self.dry_run = dry_run
        self._session = requests.Session()
        email = os.environ.get("JIRA_EMAIL", "")
        token = os.environ.get("JIRA_API_TOKEN", "")
        self._has_credentials = bool(email and token)
        if self._has_credentials:
            self._session.auth = (email, token)
        self._session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if self.dry_run and not self._has_credentials:
            print(f"  [dry-run] GET {path} params={params}")
            return {}
        resp = self._session.get(self._url(path), params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_body: Optional[Dict[str, Any]] = None) -> Any:
        if self.dry_run:
            print(f"  [dry-run] POST {path} body={json_body}")
            return {}
        resp = self._session.post(self._url(path), json=json_body)
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return {}

    def _put(self, path: str, json_body: Optional[Dict[str, Any]] = None) -> Any:
        if self.dry_run:
            print(f"  [dry-run] PUT {path} body={json_body}")
            return {}
        resp = self._session.put(self._url(path), json=json_body)
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return {}

    def get_active_sprint(self, board_id: int) -> Optional[Dict[str, Any]]:
        path = f"/rest/agile/1.0/board/{board_id}/sprint"
        data = self._get(path, params={"state": "active"})
        sprints = data.get("values", [])
        if not sprints:
            return None
        return sprints[0]

    def search_issues(self, jql: str, max_results: int = 200) -> List[Dict[str, Any]]:
        path = "/rest/api/3/search"
        data = self._get(
            path,
            params={
                "jql": jql,
                "maxResults": max_results,
                "fields": "summary,status,assignee,priority,updated,story_points,"
                "created,resolutiondate,comment",
            },
        )
        return data.get("issues", [])

    def add_comment(self, issue_key: str, body: str) -> Dict[str, Any]:
        path = f"/rest/api/3/issue/{issue_key}/comment"
        return self._post(
            path,
            {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": body}],
                        }
                    ],
                }
            },
        )

    def transition_issue(self, issue_key: str, transition_id: str) -> Dict[str, Any]:
        path = f"/rest/api/3/issue/{issue_key}/transitions"
        return self._post(path, {"transition": {"id": transition_id}})

    def get_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        path = f"/rest/api/3/issue/{issue_key}/transitions"
        data = self._get(path)
        return data.get("transitions", [])

    def get_sprint_report(
        self, board_id: int, sprint_id: int
    ) -> Dict[str, Any]:
        path = f"/rest/agile/1.0/board/{board_id}/sprint/{sprint_id}/issue"
        return self._get(path)
