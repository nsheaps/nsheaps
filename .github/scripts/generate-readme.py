#!/usr/bin/env python3
"""Generate the profile README.md from card SVGs and repo manifest."""

import json
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent.parent
CARDS_DIR = REPO_DIR / "cards"

# Category definitions: (heading, list of repo names)
CATEGORIES = {
    "AI & Agent Tooling": [
        "agent-team",
        "claude-team",
        "agent",
        "mcp",
        "claude-utils",
        ".claude",
        "vscode-claude-log-plugin",
        "ai-mktpl",
        "aitkit",
    ],
    "DevOps & Infrastructure": [
        "iac",
        "portainer-stacks",
        "tiltenv",
        "n8-renovate",
    ],
    "GitHub Actions & Automation": [
        "github-actions",
        "pull-from-upstream",
        "renovate-config",
    ],
    "Developer Tools": [
        "private-pages",
        "cors-proxy",
        "op-exec",
        "git-wt",
        "gs-stack-status",
        "homebrew-devsetup",
        "dotfiles",
    ],
    "Web & Extensions": [
        "cept",
        "greasemonkey-scripts",
        "chrome-ext-github-swapper",
    ],
}


def generate_repo_card_html(repo: dict) -> str:
    """Generate HTML for a single repo card with dark/light mode."""
    name = repo["name"]
    url = repo["url"]
    return f"""<a href="{url}">
        <picture>
          <source media="(prefers-color-scheme: dark)" srcset="cards/{name}-dark.svg">
          <img src="cards/{name}-light.svg" alt="{name}" width="400">
        </picture>
      </a>"""


def generate_category_section(heading: str, repos: list[dict]) -> str:
    """Generate a category section with cards in a grid."""
    lines = [f"### {heading}\n"]
    lines.append('<table><tr>')

    for i, repo in enumerate(repos):
        if i > 0 and i % 2 == 0:
            lines.append("</tr><tr>")
        lines.append(f"<td>\n      {generate_repo_card_html(repo)}\n    </td>")

    lines.append("</tr></table>\n")
    return "\n".join(lines)


def main():
    manifest_path = CARDS_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    repo_map = {r["name"]: r for r in manifest}

    # Collect all categorized repo names
    categorized = set()
    for names in CATEGORIES.values():
        categorized.update(names)

    # Build uncategorized list from manifest (repos not in any category, excluding hidden/meta repos)
    skip_repos = {
        "nsheaps",
        ".github",
        ".org",
        ".ai-agent-jack",
        ".ai-agent-henry",
        "workspaces",
        "obsidian-vaults",
        "n8-renovate",
        "github2",
        "tmux-ui",
        "webrtc-graph-demo",
    }
    uncategorized = [
        r["name"]
        for r in manifest
        if r["name"] not in categorized and r["name"] not in skip_repos
    ]

    readme_parts = []

    # Header
    # Build language stats from manifest for tech stack badges
    lang_counts: dict[str, int] = {}
    for r in manifest:
        lang = r.get("language", "")
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
    top_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)

    # shields.io logo slugs for common languages
    lang_logos = {
        "Shell": ("gnu-bash", "89e051"),
        "TypeScript": ("typescript", "3178c6"),
        "Python": ("python", "3572A5"),
        "Ruby": ("ruby", "701516"),
        "Go": ("go", "00ADD8"),
        "Go Template": ("go", "00ADD8"),
        "JavaScript": ("javascript", "f1e05a"),
        "Rust": ("rust", "dea584"),
        "HTML": ("html5", "e34c26"),
        "CSS": ("css3", "563d7c"),
    }

    tech_badges = []
    for lang, _ in top_langs:
        if lang in lang_logos:
            logo, color = lang_logos[lang]
            badge_label = lang.replace(" ", "%20")
            tech_badges.append(
                f'  <img src="https://img.shields.io/badge/{badge_label}-{color}?style=flat-square&logo={logo}&logoColor=white" alt="{lang}" />'
            )

    tech_line = "\n".join(tech_badges)

    readme_parts.append(f"""<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"
      srcset="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12&height=120&section=header&text=Nathan%20Heaps&fontSize=32&animation=fadeIn&fontAlignY=30&desc=Staff%20Full-Stack%20DevOps%20Engineer&descSize=14&descAlignY=50&fontColor=fefefe">
    <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12&height=120&section=header&text=Nathan%20Heaps&fontSize=32&animation=fadeIn&fontAlignY=30&desc=Staff%20Full-Stack%20DevOps%20Engineer&descSize=14&descAlignY=50&fontColor=1d1d1d">
  </picture>
</div>

<div align="center">
  <a href="https://www.linkedin.com/in/nathanheaps/">
    <img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=flat&logo=linkedin&logoColor=white" alt="LinkedIn" />
  </a>
  <img src="https://komarev.com/ghpvc/?username=nsheaps&color=FAC151&style=flat" alt="Profile views" />
  <img src="https://img.shields.io/github/followers/nsheaps?style=flat&color=FAC151" alt="Followers" />
  <img src="https://img.shields.io/github/stars/nsheaps?style=flat&color=FAC151&affiliations=OWNER" alt="Stars" />
</div>

<br>

<div align="center">
{tech_line}
</div>

<br>

<div align="center">
  <a href="https://github.com/ryo-ma/github-profile-trophy#readme">
    <picture>
      <source media="(prefers-color-scheme: dark)"
        srcset="https://github-profile-trophy.vercel.app/?username=nsheaps&row=1&column=6&no-frame=true&no-bg=true&theme=darkhub">
      <img src="https://github-profile-trophy.vercel.app/?username=nsheaps&row=1&column=6&no-frame=true&no-bg=true">
    </picture>
  </a>
</div>

<br>

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"
      srcset="https://github-readme-stats.vercel.app/api?username=nsheaps&count_private=true&show_icons=true&theme=github_dark&hide_border=true&bg_color=00000000">
    <img height="165" src="https://github-readme-stats.vercel.app/api?username=nsheaps&count_private=true&show_icons=true&hide_border=true&bg_color=00000000&icon_color=FAC051" alt="GitHub Stats" />
  </picture>
  &nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)"
      srcset="https://github-readme-stats.vercel.app/api/top-langs/?username=nsheaps&count_private=true&hide=php&langs_count=8&layout=compact&theme=github_dark&hide_border=true&bg_color=00000000">
    <img height="165" src="https://github-readme-stats.vercel.app/api/top-langs/?username=nsheaps&count_private=true&hide=php&langs_count=8&layout=compact&hide_border=true&bg_color=00000000" alt="Top Languages" />
  </picture>
</div>

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"
      srcset="https://github-readme-streak-stats.herokuapp.com/?user=nsheaps&theme=github-dark-blue&hide_border=true&background=00000000">
    <img src="https://github-readme-streak-stats.herokuapp.com/?user=nsheaps&hide_border=true&background=00000000" alt="GitHub Streak" />
  </picture>
</div>

---

## Recent Projects
""")

    # Category sections
    for heading, repo_names in CATEGORIES.items():
        repos = [repo_map[n] for n in repo_names if n in repo_map]
        if repos:
            readme_parts.append(generate_category_section(heading, repos))

    # Uncategorized
    if uncategorized:
        uncategorized_repos = [repo_map[n] for n in uncategorized if n in repo_map]
        if uncategorized_repos:
            readme_parts.append(
                generate_category_section("Other Projects", uncategorized_repos)
            )

    # Footer
    readme_parts.append("""---

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"
      srcset="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12&height=80&section=footer&fontColor=fefefe">
    <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=12&height=80&section=footer&fontColor=1d1d1d">
  </picture>
</div>
""")

    readme = "\n".join(readme_parts)
    (REPO_DIR / "README.md").write_text(readme)
    print("Generated README.md")


if __name__ == "__main__":
    main()
