#!/usr/bin/env python3
"""Generate SVG repo cards for the GitHub profile README."""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent.parent
CARDS_DIR = REPO_DIR / "cards"

# Language colors from GitHub's linguist
LANG_COLORS = {
    "Shell": "#89e051",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "Ruby": "#701516",
    "Go": "#00ADD8",
    "Go Template": "#00ADD8",
    "JavaScript": "#f1e05a",
    "Rust": "#dea584",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Vim Script": "#199f4b",
    "Dockerfile": "#384d54",
    "Makefile": "#427819",
    "HCL": "#844fba",
    "Nix": "#7e7eff",
}

# Theme definitions
THEMES = {
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "title": "#0969da",
        "desc": "#656d76",
        "meta": "#656d76",
        "icon": "#656d76",
        "star": "#656d76",
    },
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "title": "#58a6ff",
        "desc": "#8b949e",
        "meta": "#8b949e",
        "icon": "#8b949e",
        "star": "#8b949e",
    },
}

CARD_WIDTH = 280
CARD_HEIGHT = 60

# Local repos guaranteed to always appear (basenames under /home/user/ that are git repos)
# These are discovered at runtime so the set stays fresh.
LOCAL_FS_REPOS = [
    ".ai-agent-alex", ".ai-agent-henry", ".ai-agent-jack", ".ai-agent-pamela", ".ai-agent-qlod",
    ".github", ".org",
    "agent-kenny", "agent-template", "agents", "ai-mktpl", "aitkit", "brew-meta-formula",
    "cept", "claude-code-sessions", "claude-utils", "claudesh", "cors-proxy", "dotfiles",
    "farish", "framework-touchpad-toggle", "git-wt", "github-actions", "github2",
    "govee-ble-plugs", "greasemonkey-scripts", "gs-stack-status", "homebrew-devsetup",
    "iac", "n8n", "obsidian-vaults", "op-exec", "public-scratch", "renovate-config",
    "scratch", "tilt", "workspaces",
]


def escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "\u2026"


def wrap_text(text: str, max_chars: int) -> list[str]:
    """Word-wrap text into lines."""
    if not text:
        return [""]
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines[:2]  # Max 2 lines


def generate_card_svg(repo: dict, theme_name: str) -> str:
    """Generate an SVG card for a repository."""
    t = THEMES[theme_name]
    name = repo["name"]
    desc = repo.get("description") or ""
    lang = repo.get("language") or ""
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    lang_color = LANG_COLORS.get(lang, "#8b949e")

    desc_lines = wrap_text(desc, 36)[:1]  # Only 1 line fits in 60px card
    desc_svg = ""
    for i, line in enumerate(desc_lines):
        y = 34 + i * 14
        desc_svg += (
            f'    <text x="20" y="{y}" fill="{t["desc"]}" '
            f'font-size="11" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
            f"{escape_xml(line)}</text>\n"
        )

    # Bottom metadata line
    meta_y = 50
    meta_parts = []
    x_offset = 20

    # Language dot + label (compact for smaller card)
    lang_svg = ""
    if lang:
        label_text = truncate(lang, 14)
        dot_cx = x_offset + 5
        dot_cy = meta_y - 4
        text_x = x_offset + 12
        lang_svg = (
            f'    <circle cx="{dot_cx}" cy="{dot_cy}" r="4" fill="{lang_color}" />\n'
            f'    <text x="{text_x}" y="{meta_y}" fill="{t["meta"]}" '
            f'font-size="10" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
            f"{escape_xml(label_text)}</text>\n"
        )
        x_offset += 12 + len(label_text) * 6 + 10

    # Stars (always shown)
    star_svg = (
        f'    <svg x="{x_offset}" y="{meta_y - 10}" width="11" height="11" viewBox="0 0 16 16" fill="{t["star"]}">'
        f'<path d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>'
        f"</svg>\n"
        f'    <text x="{x_offset + 13}" y="{meta_y}" fill="{t["meta"]}" '
        f'font-size="10" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
        f"{stars}</text>\n"
    )
    x_offset += 13 + len(str(stars)) * 6 + 10

    # Forks (always shown)
    fork_svg = (
        f'    <svg x="{x_offset}" y="{meta_y - 10}" width="11" height="11" viewBox="0 0 16 16" fill="{t["icon"]}">'
        f'<path d="M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h1.5v2.128a2.251 2.251 0 101.5 0V8.5h1.5a2.25 2.25 0 002.25-2.25v-.878a2.25 2.25 0 10-1.5 0v.878a.75.75 0 01-.75.75h-4.5A.75.75 0 015 6.25v-.878zm3.75 7.378a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm3-8.75a.75.75 0 100-1.5.75.75 0 000 1.5z"/>'
        f"</svg>\n"
        f'    <text x="{x_offset + 13}" y="{meta_y}" fill="{t["meta"]}" '
        f'font-size="10" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
        f"{forks}</text>\n"
    )

    # Repo icon (book)
    repo_icon = (
        f'    <svg x="14" y="8" width="14" height="14" viewBox="0 0 16 16" fill="{t["icon"]}">'
        f'<path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1h-8a1 1 0 00-1 1v6.708A2.486 2.486 0 014.5 9h8V1.5zm-8 11h8v1h-8a1 1 0 010-2z"/>'
        f"</svg>\n"
    )

    return f"""<svg width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="{CARD_WIDTH - 1}" height="{CARD_HEIGHT - 1}" rx="6" fill="{t['bg']}" stroke="{t['border']}" stroke-width="1" />
{repo_icon}
    <text x="34" y="18" fill="{t['title']}" font-size="12" font-weight="600" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif">{escape_xml(truncate(name, 28))}</text>
{desc_svg}{lang_svg}{star_svg}{fork_svg}</svg>
"""


def fetch_repo_data(repo_name: str) -> dict | None:
    """Fetch a single repo's data from GitHub API. Returns None on failure."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/nsheaps/{repo_name}"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print(f"Warning: gh CLI not found; cannot fetch {repo_name}", file=sys.stderr)
        return None
    if result.returncode != 0:
        print(f"Warning: could not fetch nsheaps/{repo_name}: {result.stderr.strip()}", file=sys.stderr)
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def fetch_repos() -> list[dict]:
    """Fetch repos from GitHub API using gh CLI, merging both endpoints.

    Always includes LOCAL_FS_REPOS as a guaranteed floor — any local repo not
    already in the API-fetched set is fetched individually and appended.
    """
    # Search API (non-fork org repos)
    try:
        search = subprocess.run(
            [
                "gh",
                "api",
                "search/repositories?q=user:nsheaps+fork:false&sort=updated&per_page=30",
                "--jq",
                ".items",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        search_repos = json.loads(search.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Warning: search API failed: {e}", file=sys.stderr)
        search_repos = []

    # Owner API (catches repos search misses, excludes forks)
    try:
        owner = subprocess.run(
            [
                "gh",
                "api",
                "users/nsheaps/repos?sort=updated&per_page=30&type=owner",
                "--jq",
                "[.[] | select(.fork == false)]",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        owner_repos = json.loads(owner.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Warning: owner API failed: {e}", file=sys.stderr)
        owner_repos = []

    # Merge: search results first, then fill from owner (deduped)
    seen = {r["full_name"] for r in search_repos}
    merged = list(search_repos)
    for r in owner_repos:
        if r["full_name"] not in seen:
            merged.append(r)
            seen.add(r["full_name"])

    # --- Guaranteed floor: always include LOCAL_FS_REPOS ---
    seen_names = {r["name"] for r in merged}
    for local_name in LOCAL_FS_REPOS:
        if local_name not in seen_names:
            print(f"Fetching missing local repo: nsheaps/{local_name}", file=sys.stderr)
            repo_data = fetch_repo_data(local_name)
            if repo_data:
                merged.append(repo_data)
                seen_names.add(local_name)
            else:
                # Minimal stub so a card still gets generated
                merged.append({
                    "name": local_name,
                    "full_name": f"nsheaps/{local_name}",
                    "description": "",
                    "language": "",
                    "stargazers_count": 0,
                    "forks_count": 0,
                    "html_url": f"https://github.com/nsheaps/{local_name}",
                    "pushed_at": "",
                    "fork": False,
                    "updated_at": "",
                })

    # Sort by updated_at descending; guaranteed repos without dates sort to the end
    merged.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    return merged  # Generate cards for all; README script selects/organises


def fetch_recent_commit_counts(repos: list[dict]) -> dict[str, int]:
    """Fetch recent commit counts for repos using GitHub GraphQL API.

    Returns a dict mapping full_name to commit count in the last 30 days.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    counts: dict[str, int] = {}

    # GraphQL allows ~30 repos per query; batch accordingly
    batch_size = 20
    for i in range(0, len(repos), batch_size):
        batch = repos[i : i + batch_size]
        parts = []
        for idx, repo in enumerate(batch):
            owner, name = repo["full_name"].split("/")
            alias = f"r{idx}"
            parts.append(
                f'{alias}: repository(owner: "{owner}", name: "{name}") {{\n'
                f"  defaultBranchRef {{\n"
                f"    target {{\n"
                f"      ... on Commit {{\n"
                f'        history(since: "{since}") {{\n'
                f"          totalCount\n"
                f"        }}\n"
                f"      }}\n"
                f"    }}\n"
                f"  }}\n"
                f"}}"
            )
        query = "query {\n" + "\n".join(parts) + "\n}"
        try:
            result = subprocess.run(
                ["gh", "api", "graphql", "-f", f"query={query}"],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            print("Warning: gh CLI not found; skipping commit count fetch", file=sys.stderr)
            break
        if result.returncode != 0:
            print(f"Warning: GraphQL query failed: {result.stderr}", file=sys.stderr)
            continue

        data = json.loads(result.stdout).get("data", {})
        for idx, repo in enumerate(batch):
            alias = f"r{idx}"
            repo_data = data.get(alias)
            if repo_data and repo_data.get("defaultBranchRef"):
                target = repo_data["defaultBranchRef"].get("target", {})
                count = target.get("history", {}).get("totalCount", 0)
            else:
                count = 0
            counts[repo["full_name"]] = count

    return counts


def main():
    repos = fetch_repos()
    CARDS_DIR.mkdir(exist_ok=True)

    # Fetch recent commit activity
    commit_counts = fetch_recent_commit_counts(repos)

    for repo in repos:
        name = repo["name"]
        for theme_name in THEMES:
            svg = generate_card_svg(repo, theme_name)
            path = CARDS_DIR / f"{name}-{theme_name}.svg"
            path.write_text(svg)
            print(f"Generated {path}")

    # Write repo manifest for README generation
    manifest = []
    for repo in repos:
        manifest.append(
            {
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description") or "",
                "language": repo.get("language") or "",
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "url": repo["html_url"],
                "pushed_at": repo.get("pushed_at", ""),
                "recent_commits": commit_counts.get(repo["full_name"], 0),
            }
        )
    (CARDS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Generated manifest with {len(manifest)} repos")


if __name__ == "__main__":
    main()
