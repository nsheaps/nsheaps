#!/usr/bin/env python3
"""Generate an SVG heatmap of Claude Code usage from commit history.

Scans commit messages across the user's repos for claude.ai/code/session URLs
and renders a GitHub-style contribution heatmap for light and dark themes.
"""

import json
import math
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent.parent
CARDS_DIR = REPO_DIR / "cards"

USERNAME = "nsheaps"
WEEKS_TO_SHOW = 30

# ---------------------------------------------------------------------------
# What counts as "Claude Code usage" (edit this section to tune the graph)
# ---------------------------------------------------------------------------
# Commit searches are scoped to repositories owned by this account/org.
OWNER = "nsheaps"

# gh search commits caps results at 1000 per query.
SEARCH_LIMIT = 1000

# Commit identities for the AI agents and Claude itself. Each email below is
# matched as BOTH the commit author and the committer. These are the bot/agent
# git identities discovered across the nsheaps org repos:
#   - Claude Code (direct commits, e.g. cept, op-exec, gs-stack-status)
#   - Claude Code GitHub App
#   - Jack, Henry, Alex (the nsheaps AI agents)
# Add a new agent by appending its commit email here.
AGENT_COMMIT_EMAILS = [
    "noreply@anthropic.com",  # claude (direct)
    "221249200+claude-code-gather[bot]@users.noreply.github.com",  # claude (app)
    "254347511+jack-nsheaps[bot]@users.noreply.github.com",  # jack
    "246599473+henry-nsheaps[bot]@users.noreply.github.com",  # henry
    "279051173+alex-nsheaps[bot]@users.noreply.github.com",  # alex
]

# Free-text commit-message searches, filtered by a specific author login. This
# captures human commits that reference a Claude Code session (the original
# behavior of this script).
MESSAGE_SEARCHES = [
    {"author": USERNAME, "query": "claude.ai/code"},
]


def build_search_specs() -> list[dict]:
    """Assemble the list of gh-search-commits queries to run.

    Each spec is a dict whose keys map to gh search flags (any subset of
    ``author``, ``committer``, ``author_email``, ``committer_email``,
    ``query``). Specs are combined as a union and deduplicated by commit SHA,
    so a commit matching multiple specs is only counted once.
    """
    specs: list[dict] = list(MESSAGE_SEARCHES)
    for email in AGENT_COMMIT_EMAILS:
        # Author OR committer: gh ANDs flags within a query, so use two specs.
        specs.append({"author_email": email})
        specs.append({"committer_email": email})
    return specs


CELL_SIZE = 11
CELL_GAP = 3
CELL_RADIUS = 2

# Theme definitions matching the card styles
THEMES = {
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "text": "#1f2328",
        "subtext": "#656d76",
        "empty": "#ebedf0",
        "levels": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
    },
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "text": "#e6edf3",
        "subtext": "#8b949e",
        "empty": "#161b22",
        "levels": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
    },
}

MONTH_LABELS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

DAY_LABELS = ["Mon", "Wed", "Fri"]


def run_commit_search(spec: dict) -> list[dict]:
    """Run a single ``gh search commits`` query and return the parsed results.

    ``spec`` keys map onto gh flags (``author``, ``committer``,
    ``author_email``, ``committer_email``, ``query``). All searches are scoped
    to ``OWNER``.
    """
    cmd = [
        "gh",
        "search",
        "commits",
        "--owner",
        OWNER,
        "--order",
        "desc",
        "--sort",
        "committer-date",
        "--limit",
        str(SEARCH_LIMIT),
        "--json",
        "sha,commit",
    ]
    if spec.get("author"):
        cmd += ["--author", spec["author"]]
    if spec.get("committer"):
        cmd += ["--committer", spec["committer"]]
    if spec.get("author_email"):
        cmd += ["--author-email", spec["author_email"]]
    if spec.get("committer_email"):
        cmd += ["--committer-email", spec["committer_email"]]
    if spec.get("query"):
        cmd += ["--", spec["query"]]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: gh search failed for {spec}: {e.stderr}", file=sys.stderr)
        return []

    return json.loads(result.stdout)


def fetch_claude_commits() -> dict[str, int]:
    """Fetch per-day commit counts for all configured Claude Code searches.

    Runs every spec from :func:`build_search_specs` (human session-URL commits
    plus the AI agents' author/committer commits), deduplicates by commit SHA
    so each commit is counted once, and returns a dict mapping date strings
    (YYYY-MM-DD) to commit counts.
    """
    seen: dict[str, str] = {}  # commit SHA -> commit day (YYYY-MM-DD)

    for spec in build_search_specs():
        for item in run_commit_search(spec):
            committer = item.get("commit", {}).get("committer", {})
            date_str = committer.get("date", "")
            if not date_str:
                continue
            day = date_str[:10]
            # Fall back to a synthetic key if a SHA is somehow missing, so we
            # never silently drop a real commit.
            sha = item.get("sha") or f"{date_str}:{len(seen)}"
            seen[sha] = day

    counts: dict[str, int] = {}
    for day in seen.values():
        counts[day] = counts.get(day, 0) + 1

    return counts


def get_date_range(weeks: int) -> tuple[datetime, datetime]:
    """Get the date range for the heatmap grid ending today."""
    today = datetime.now()
    # End on the current day's week (Saturday end like GitHub)
    end = today
    # Go back N weeks
    start = end - timedelta(weeks=weeks)
    # Align start to Sunday
    start = start - timedelta(days=start.weekday() + 1 if start.weekday() != 6 else 0)
    return start, end


def get_level(count: int, max_count: int) -> int:
    """Map a count to a 0-4 level for the heatmap color."""
    if count == 0:
        return 0
    if max_count <= 0:
        return 1
    # Use quartile-based thresholds
    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    if ratio <= 0.50:
        return 2
    if ratio <= 0.75:
        return 3
    return 4


def escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_heatmap_svg(
    counts: dict[str, int], theme_name: str, weeks: int = WEEKS_TO_SHOW
) -> str:
    """Generate the heatmap SVG string."""
    t = THEMES[theme_name]
    start, end = get_date_range(weeks)

    # Build the grid: list of (week_col, day_row, date, count)
    grid = []
    current = start
    while current <= end:
        week_col = (current - start).days // 7
        day_row = current.weekday()  # 0=Mon, 6=Sun
        # Remap so Sunday=0, Mon=1, ..., Sat=6 (GitHub style)
        gh_row = (day_row + 1) % 7
        date_str = current.strftime("%Y-%m-%d")
        count = counts.get(date_str, 0)
        grid.append((week_col, gh_row, current, count))
        current += timedelta(days=1)

    max_count = max((c for _, _, _, c in grid), default=1)
    if max_count == 0:
        max_count = 1

    total_commits = sum(counts.get(d.strftime("%Y-%m-%d"), 0) for _, _, d, _ in grid)

    # Dimensions
    left_margin = 32  # Space for day labels
    top_margin = 22  # Space for month labels
    num_weeks = weeks + 1
    grid_width = num_weeks * (CELL_SIZE + CELL_GAP)
    grid_height = 7 * (CELL_SIZE + CELL_GAP)

    # Legend dimensions
    legend_cell_count = 5
    legend_width = legend_cell_count * (CELL_SIZE + CELL_GAP) + 60
    legend_height = CELL_SIZE + 4

    padding = 16
    title_height = 28
    legend_area_height = 28

    svg_width = left_margin + grid_width + padding * 2
    svg_height = (
        title_height + top_margin + grid_height + legend_area_height + padding * 2
    )

    parts = []

    # SVG header
    parts.append(
        f'<svg width="{svg_width}" height="{svg_height}" '
        f'viewBox="0 0 {svg_width} {svg_height}" '
        f'xmlns="http://www.w3.org/2000/svg">'
    )

    # Background
    parts.append(
        f'  <rect x="0.5" y="0.5" width="{svg_width - 1}" height="{svg_height - 1}" '
        f'rx="6" fill="{t["bg"]}" stroke="{t["border"]}" stroke-width="1" />'
    )

    # Title
    title_x = padding
    title_y = padding + 16
    parts.append(
        f'  <text x="{title_x}" y="{title_y}" fill="{t["text"]}" '
        f'font-size="14" font-weight="600" '
        f'font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
        f"Claude Code Activity</text>"
    )

    # Subtitle with total
    subtitle_x = svg_width - padding
    parts.append(
        f'  <text x="{subtitle_x}" y="{title_y}" fill="{t["subtext"]}" '
        f'font-size="11" text-anchor="end" '
        f'font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
        f"{total_commits} contributions in the last {weeks} weeks</text>"
    )

    # Grid offset
    gx = padding + left_margin
    gy = padding + title_height + top_margin

    # Month labels
    month_y = padding + title_height + 12
    last_month = -1
    for week_col, gh_row, date, _ in grid:
        if gh_row == 0 and date.month != last_month:
            label_x = gx + week_col * (CELL_SIZE + CELL_GAP)
            parts.append(
                f'  <text x="{label_x}" y="{month_y}" fill="{t["subtext"]}" '
                f'font-size="10" '
                f'font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
                f"{MONTH_LABELS[date.month - 1]}</text>"
            )
            last_month = date.month

    # Day labels (Mon, Wed, Fri)
    for label, row_idx in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
        label_y = gy + row_idx * (CELL_SIZE + CELL_GAP) + CELL_SIZE - 2
        parts.append(
            f'  <text x="{padding + 2}" y="{label_y}" fill="{t["subtext"]}" '
            f'font-size="10" '
            f'font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
            f"{label}</text>"
        )

    # Heatmap cells
    for week_col, gh_row, date, count in grid:
        x = gx + week_col * (CELL_SIZE + CELL_GAP)
        y = gy + gh_row * (CELL_SIZE + CELL_GAP)
        level = get_level(count, max_count)
        color = t["levels"][level]
        date_str = date.strftime("%Y-%m-%d")
        tooltip = f"{count} commit{'s' if count != 1 else ''} on {date_str}"
        parts.append(
            f'  <rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
            f'rx="{CELL_RADIUS}" fill="{color}">'
            f"<title>{escape_xml(tooltip)}</title></rect>"
        )

    # Legend
    legend_x = svg_width - padding - legend_width
    legend_y = gy + grid_height + 8

    parts.append(
        f'  <text x="{legend_x}" y="{legend_y + CELL_SIZE - 2}" fill="{t["subtext"]}" '
        f'font-size="10" '
        f'font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
        f"Less</text>"
    )

    for i in range(legend_cell_count):
        lx = legend_x + 30 + i * (CELL_SIZE + CELL_GAP)
        parts.append(
            f'  <rect x="{lx}" y="{legend_y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
            f'rx="{CELL_RADIUS}" fill="{t["levels"][i]}" />'
        )

    more_x = legend_x + 30 + legend_cell_count * (CELL_SIZE + CELL_GAP) + 4
    parts.append(
        f'  <text x="{more_x}" y="{legend_y + CELL_SIZE - 2}" fill="{t["subtext"]}" '
        f'font-size="10" '
        f'font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
        f"More</text>"
    )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    CARDS_DIR.mkdir(exist_ok=True)

    print("Fetching Claude Code commit data...")
    counts = fetch_claude_commits()
    print(f"Found commits on {len(counts)} distinct days")

    for theme_name in THEMES:
        svg = generate_heatmap_svg(counts, theme_name)
        path = CARDS_DIR / f"claude-usage-{theme_name}.svg"
        path.write_text(svg)
        print(f"Generated {path}")


if __name__ == "__main__":
    main()
