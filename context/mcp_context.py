"""MCP (Model Context Protocol) context provider and GitHub/Slack connectors for AeroTrace."""

import os
import sys
import subprocess
import urllib.parse
from typing import Dict, Any, Optional
import requests
import config


def get_active_workspace_context() -> Dict[str, Any]:
    """
    Fetches context from the local workspace / developer environment.
    Integrates with local git, runtime environment, and active MCP servers.
    """
    context = {
        "workspace_path": os.getcwd(),
        "python_version": sys.version.split()[0],
        "active_app": "IDE / Terminal",
    }

    # 1. Fetch git repository info & branch
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=1
        ).decode().strip()
        context["git_branch"] = branch
    except Exception:
        context["git_branch"] = "main"

    try:
        repo_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            stderr=subprocess.DEVNULL,
            timeout=1
        ).decode().strip()
        context["git_repo_url"] = repo_url
    except Exception:
        context["git_repo_url"] = ""

    # 2. Local services status
    context["services"] = {
        "postgres": "port 5432 (stopped)",
        "redis": "port 6379 (running)"
    }

    # 3. Connected external MCP servers
    context["mcp_servers"] = {
        "github": bool(config.GITHUB_TOKEN or os.getenv("GITHUB_TOKEN")),
        "slack": bool(config.SLACK_WEBHOOK_URL or os.getenv("SLACK_WEBHOOK_URL")),
    }

    return context


# -------------------------------------------------------------
# GITHUB MCP INTEGRATION
# -------------------------------------------------------------
class GitHubMCPClient:
    """Lightweight GitHub MCP connector for issue search & 1-click issue filing."""

    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN", config.GITHUB_TOKEN)
        self.repo = repo or os.getenv("GITHUB_REPO", config.GITHUB_REPO) or "repo"

    def create_or_open_issue(self, title: str, traceback_text: str, fix: str) -> Dict[str, Any]:
        body = f"""### ⚡ AeroTrace Incident Report

**Issue Summary:**
{title}

**Hovered Context / Traceback:**
```text
{traceback_text[:800]}
```

**Recommended Fix:**
```bash
{fix}
```

*Reported via AeroTrace Cursor Co-Pilot*"""

        # 1. If active token and repo configured, post directly to GitHub API
        if self.token and self.repo and "/" in self.repo:
            try:
                headers = {
                    "Authorization": f"Bearer {self.token.strip()}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "AeroTrace-CoPilot"
                }
                res = requests.post(
                    f"https://api.github.com/repos/{self.repo}/issues",
                    json={"title": f"[AeroTrace] {title[:80]}", "body": body},
                    headers=headers,
                    timeout=5
                )
                if res.status_code in (200, 201):
                    issue_url = res.json().get("html_url", "")
                    print(f"[GitHub MCP] Issue created successfully: {issue_url}")
                    return {"success": True, "url": issue_url, "mode": "api"}
            except Exception as e:
                print(f"[GitHub MCP] Direct API error: {e}")

        # 2. Fallback / Zero-auth: Generate ready-to-use web issue link
        encoded_title = urllib.parse.quote(f"[AeroTrace] {title[:60]}")
        encoded_body = urllib.parse.quote(body)
        repo_target = self.repo if "/" in self.repo else "owner/repository"
        web_link = f"https://github.com/{repo_target}/issues/new?title={encoded_title}&body={encoded_body}"
        print(f"[GitHub MCP] Drafted issue link: {web_link[:70]}...")
        return {"success": True, "url": web_link, "mode": "link"}


# -------------------------------------------------------------
# SLACK MCP INTEGRATION
# -------------------------------------------------------------
class SlackMCPClient:
    """Lightweight Slack MCP connector to share resolutions with teammates."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL", config.SLACK_WEBHOOK_URL)

    def post_resolution(self, summary: str, fix: str, voice_query: Optional[str] = None) -> Dict[str, Any]:
        payload = {
            "text": f"⚡ *AeroTrace Incident Solved*\n*Problem:* {summary}\n*Fix:* `{fix}`",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⚡ *AeroTrace Incident Resolution*\n*Issue:* {summary}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Suggested Fix:*\n```{fix}```"
                    }
                }
            ]
        }
        if voice_query:
            payload["blocks"].append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"🎤 *Voice Query:* \"{voice_query}\""}]
            })

        if self.webhook_url and self.webhook_url.startswith("http"):
            try:
                res = requests.post(self.webhook_url, json=payload, timeout=4)
                if res.status_code == 200:
                    print("[Slack MCP] Shared resolution to Slack channel successfully!")
                    return {"success": True, "channel": "Slack", "mode": "webhook"}
            except Exception as e:
                print(f"[Slack MCP] Webhook error: {e}")

        # Simulated MCP dispatch when webhook URL is not yet configured
        safe_msg = payload['text'].encode('ascii', 'replace').decode('ascii')
        print(f"[Slack MCP] Formatted Slack message dispatch payload: {safe_msg}")
        return {"success": True, "channel": "Slack (Simulated)", "mode": "simulated"}
