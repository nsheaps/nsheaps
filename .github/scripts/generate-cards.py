#!/usr/bin/env python3
"""Generate SVG repo cards for the GitHub profile README."""

import json
import os
import subprocess
import sys
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

CARD_WIDTH = 400
CARD_HEIGHT = 120


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

    desc_lines = wrap_text(desc, 52)
    desc_svg = ""
    for i, line in enumerate(desc_lines):
        y = 55 + i * 18
        desc_svg += (
            f'    <text x="20" y="{y}" fill="{t["desc"]}" '
            f'font-size="12.5" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
            f"{escape_xml(line)}</text>\n"
        )

    # Bottom metadata line
    meta_y = 100
    meta_parts = []
    x_offset = 20

    # Language badge (shields.io style)
    lang_svg = ""
    if lang:
        label_text = lang
        text_width = len(label_text) * 6.2 + 10
        badge_height = 20
        badge_y = meta_y - 14
        dot_cx = x_offset + 10
        dot_cy = badge_y + badge_height / 2
        text_x = x_offset + 18
        text_y = badge_y + 14
        badge_width = text_width + 14
        # Contrast color for text on the badge
        badge_bg = lang_color
        lang_svg = (
            f'    <rect x="{x_offset}" y="{badge_y}" width="{badge_width}" height="{badge_height}" rx="10" fill="{badge_bg}" opacity="0.15" />\n'
            f'    <circle cx="{dot_cx}" cy="{dot_cy}" r="4" fill="{badge_bg}" />\n'
            f'    <text x="{text_x}" y="{text_y}" fill="{t["meta"]}" '
            f'font-size="11" font-weight="500" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
            f"{escape_xml(label_text)}</text>\n"
        )
        x_offset += badge_width + 12

    # Stars (always shown)
    star_svg = (
        f'    <svg x="{x_offset}" y="{meta_y - 11}" width="14" height="14" viewBox="0 0 16 16" fill="{t["star"]}">'
        f'<path d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"/>'
        f"</svg>\n"
        f'    <text x="{x_offset + 17}" y="{meta_y}" fill="{t["meta"]}" '
        f'font-size="11" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
        f"{stars}</text>\n"
    )
    x_offset += 17 + len(str(stars)) * 7 + 16

    # Forks (always shown)
    fork_svg = (
        f'    <svg x="{x_offset}" y="{meta_y - 11}" width="14" height="14" viewBox="0 0 16 16" fill="{t["icon"]}">'
        f'<path d="M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h1.5v2.128a2.251 2.251 0 101.5 0V8.5h1.5a2.25 2.25 0 002.25-2.25v-.878a2.25 2.25 0 10-1.5 0v.878a.75.75 0 01-.75.75h-4.5A.75.75 0 015 6.25v-.878zm3.75 7.378a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm3-8.75a.75.75 0 100-1.5.75.75 0 000 1.5z"/>'
        f"</svg>\n"
        f'    <text x="{x_offset + 17}" y="{meta_y}" fill="{t["meta"]}" '
        f'font-size="11" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
        f"{forks}</text>\n"
    )

    # Repo icon (book)
    repo_icon = (
        f'    <svg x="20" y="16" width="16" height="16" viewBox="0 0 16 16" fill="{t["icon"]}">'
        f'<path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1h-8a1 1 0 00-1 1v6.708A2.486 2.486 0 014.5 9h8V1.5zm-8 11h8v1h-8a1 1 0 010-2z"/>'
        f"</svg>\n"
    )

    return f"""<svg width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="{CARD_WIDTH - 1}" height="{CARD_HEIGHT - 1}" rx="6" fill="{t['bg']}" stroke="{t['border']}" stroke-width="1" />
{repo_icon}
    <text x="42" y="30" fill="{t['title']}" font-size="14" font-weight="600" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif">{escape_xml(name)}</text>
{desc_svg}{lang_svg}{star_svg}{fork_svg}</svg>
"""


def fetch_repos() -> list[dict]:
    """Fetch repos from GitHub API using gh CLI, merging both endpoints."""
    # Search API (non-fork org repos)
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

    # Owner API (catches repos search misses, excludes forks)
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

    # Merge: search results first, then fill from owner (deduped)
    seen = {r["full_name"] for r in search_repos}
    merged = list(search_repos)
    for r in owner_repos:
        if r["full_name"] not in seen:
            merged.append(r)
            seen.add(r["full_name"])

    # Sort by updated_at descending, take top 30
    merged.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    return merged[:40]  # Generate cards for all, README script picks 30


def main():
    repos = fetch_repos()
    CARDS_DIR.mkdir(exist_ok=True)

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
            }
        )
    (CARDS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Generated manifest with {len(manifest)} repos")


if __name__ == "__main__":
    main()
