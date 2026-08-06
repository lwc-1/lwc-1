#!/usr/bin/env python3

import json
import os
import re
import urllib.parse
import urllib.request


USERNAME = os.environ.get("GITHUB_USERNAME", "lwc-1")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
README_PATH = "README.md"


def request_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "lwc-1-readme-stats",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_repositories():
    repos = []
    page = 1
    while True:
        params = urllib.parse.urlencode(
            {
                "type": "owner",
                "sort": "full_name",
                "per_page": 100,
                "page": page,
            }
        )
        batch = request_json(f"https://api.github.com/users/{USERNAME}/repos?{params}")
        if not batch:
            break

        repos.extend(repo for repo in batch if not repo.get("fork"))
        page += 1

    return repos


def search_count(endpoint, query):
    params = urllib.parse.urlencode({"q": query, "per_page": 1})
    data = request_json(f"https://api.github.com/search/{endpoint}?{params}")
    return data["total_count"]


def get_totals():
    repos = get_repositories()
    return {
        "stars": sum(repo["stargazers_count"] for repo in repos),
        "commits": search_count("commits", f"author:{USERNAME}"),
        "pull_requests": search_count("issues", f"author:{USERNAME} type:pr"),
        "issues": search_count("issues", f"author:{USERNAME} type:issue"),
        "repositories": len(repos),
    }


def format_number(value):
    return f"{value:,}"


def build_stats_block(totals):
    cards = [
        ("Stars", totals["stars"]),
        ("Commits", totals["commits"]),
        ("Pull Requests", totals["pull_requests"]),
        ("Issues", totals["issues"]),
        ("Repositories", totals["repositories"]),
    ]
    card_cells = []
    for label, value in cards:
        card_cells.append(
            f"    <td align=\"center\"><b>{format_number(value)}</b><br/><sub>{label}</sub></td>"
        )

    return "\n".join(
        [
            "<!-- STATS:START -->",
            '<table align="center">',
            "  <tr>",
            *card_cells,
            "  </tr>",
            "</table>",
            "<!-- STATS:END -->",
        ]
    )


def update_readme(totals):
    with open(README_PATH, "r", encoding="utf-8") as file:
        readme = file.read()

    pattern = r"<!-- STATS:START -->.*?<!-- STATS:END -->"
    if re.search(pattern, readme, flags=re.DOTALL) is None:
        raise RuntimeError("Stats markers were not found in README.md.")

    updated = re.sub(
        pattern,
        build_stats_block(totals),
        readme,
        flags=re.DOTALL,
    )

    with open(README_PATH, "w", encoding="utf-8") as file:
        file.write(updated)


def main():
    update_readme(get_totals())


if __name__ == "__main__":
    main()
