#!/usr/bin/env python3
"""Pin every GitHub Action in .github/workflows/ to the latest release SHA.

Templates ship known-good action versions for shape; run this at bootstrap so a
new repo starts current. For each `uses: owner/repo@ref # comment` line it finds
the latest release tag (falling back to the newest tag), resolves it to the
commit SHA, and rewrites the line as `uses: owner/repo@<sha> # <tag>`.

Requires the `gh` CLI, authenticated. Idempotent. Usage:

    python3 skills/project-bootstrap/scripts/pin-actions.py [WORKFLOW_DIR]

Defaults WORKFLOW_DIR to .github/workflows. Local (`./.github/...`) and Docker
(`docker://...`) actions are skipped.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

USES_RE = re.compile(
    r"^(?P<prefix>\s*(?:-\s*)?uses:\s*)(?P<action>[^@\s]+)@(?P<ref>\S+)(?P<rest>.*)$"
)


def gh_json(path: str) -> dict | None:
    """Return parsed JSON from `gh api PATH`, or None on any failure."""
    result = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def latest_tag(repo: str) -> str | None:
    """Latest release tag for owner/repo, falling back to the newest tag."""
    release = gh_json(f"repos/{repo}/releases/latest")
    if release and release.get("tag_name"):
        return release["tag_name"]
    tags = gh_json(f"repos/{repo}/tags?per_page=1")
    if isinstance(tags, list) and tags:
        return tags[0].get("name")
    return None


def commit_sha(repo: str, ref: str) -> str | None:
    """Resolve a tag/ref to its commit SHA (dereferences annotated tags)."""
    commit = gh_json(f"repos/{repo}/commits/{ref}")
    if commit and commit.get("sha"):
        return commit["sha"]
    return None


def resolve(action: str, cache: dict[str, tuple[str, str] | None]) -> tuple[str, str] | None:
    """Return (sha, tag) for an action repo, memoized. Subpaths share a repo."""
    repo = "/".join(action.split("/")[:2])
    if repo not in cache:
        tag = latest_tag(repo)
        sha = commit_sha(repo, tag) if tag else None
        cache[repo] = (sha, tag) if sha and tag else None
    return cache[repo]


def pin_file(path: Path, cache: dict[str, tuple[str, str] | None]) -> bool:
    changed = False
    lines = path.read_text().splitlines(keepends=True)
    for i, line in enumerate(lines):
        match = USES_RE.match(line)
        if not match:
            continue
        action = match["action"]
        if action.startswith((".", "docker:")):
            continue
        pinned = resolve(action, cache)
        if pinned is None:
            print(f"  ! could not resolve {action}", file=sys.stderr)
            continue
        sha, tag = pinned
        newline = f"{match['prefix']}{action}@{sha} # {tag}\n"
        if newline != line:
            lines[i] = newline
            changed = True
            print(f"  {action} -> {tag} ({sha[:12]})")
    if changed:
        path.write_text("".join(lines))
    return changed


def main() -> int:
    workflow_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".github/workflows")
    if not workflow_dir.is_dir():
        print(f"No workflow dir at {workflow_dir}", file=sys.stderr)
        return 1
    files = sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")])
    if not files:
        print(f"No workflow files in {workflow_dir}", file=sys.stderr)
        return 1
    cache: dict[str, tuple[str, str] | None] = {}
    any_changed = False
    for path in files:
        print(f"{path}:")
        if pin_file(path, cache):
            any_changed = True
    print("Updated." if any_changed else "Already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
