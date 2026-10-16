#!/usr/bin/env python3
"""Publish docs/ to GitHub Pages — no GitHub Actions anywhere in the path.

What it does:
  1. builds the graph first (scripts/build_graph.py) so the site can never ship stale data;
  2. creates the GitHub repository if it does not exist, and pushes the source branch;
  3. force-pushes the *contents* of docs/ to an orphan `gh-pages` branch;
  4. enables GitHub Pages on that branch (idempotent), then reports the project URL.

The `gh-pages` orphan push is the house pattern from Digital-Mailroom's
scripts/deploy_gh_pages.py: the published artefact is a branch, not an Action.

    uv run python scripts/deploy_gh_pages.py --repo Exios66/DMR-Graph
    uv run python scripts/deploy_gh_pages.py --repo Exios66/DMR-Graph --site-only
    uv run python scripts/deploy_gh_pages.py --repo Exios66/DMR-Graph --dry-run

Prerequisites: git, gh CLI (authenticated), uv.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DEFAULT_REPO = "Exios66/DMR-Graph"


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(cmd)}\n{result.stdout}{result.stderr}")
    return result


def gh(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return run(["gh", *args], check=check)


def repo_exists(slug: str) -> bool:
    return gh(["repo", "view", slug, "--json", "name"], check=False).returncode == 0


def ensure_repo(slug: str, dry_run: bool) -> None:
    if repo_exists(slug):
        print(f"repo exists: {slug}")
        return
    if dry_run:
        print(f"[dry-run] would create public repo {slug} and push the current branch")
        return
    print(f"creating public repo {slug}")
    run(["gh", "repo", "create", slug, "--public", "--source", str(ROOT),
         "--remote", "origin", "--push"])


def push_source(slug: str, dry_run: bool) -> None:
    remotes = run(["git", "remote"], cwd=ROOT).stdout.split()
    if "origin" not in remotes:
        if dry_run:
            print("[dry-run] would add remote origin")
            return
        run(["git", "remote", "add", "origin", f"git@github.com:{slug}.git"], cwd=ROOT)
    branch = run(["git", "branch", "--show-current"], cwd=ROOT).stdout.strip() or "main"
    if not run(["git", "status", "--porcelain"], cwd=ROOT).stdout.strip():
        if dry_run:
            print(f"[dry-run] would push {branch} to origin")
            return
        print(f"pushing {branch} → origin/{branch}")
        run(["git", "push", "-u", "origin", branch], cwd=ROOT)
    else:
        print("note: working tree has uncommitted changes — commit them first if they belong on the source branch")


def publish_site(slug: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would force-push docs/ to gh-pages of {slug}")
        return
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copytree(DOCS, work, dirs_exist_ok=True)
        run(["git", "init", "-q"], cwd=work)
        run(["git", "add", "-A"], cwd=work)
        run(["git", "-c", "user.name=dmr-graph", "-c", "user.email=dmr-graph@users.noreply.github.com",
             "commit", "-q", "-m", "Publish DMR-Graph site (docs/) to gh-pages"], cwd=work)
        run(["git", "push", "--force", f"git@github.com:{slug}.git", "HEAD:gh-pages"], cwd=work)
    print("pushed docs/ → gh-pages")


def enable_pages(slug: str) -> None:
    pages = gh(["api", f"repos/{slug}/pages"], check=False)
    if pages.returncode == 0:
        gh(["api", "-X", "PUT", f"repos/{slug}/pages",
            "-f", "source[branch]=gh-pages", "-f", "source[path]=/"])
        print("Pages: source updated to gh-pages /")
    else:
        gh(["api", "-X", "POST", f"repos/{slug}/pages",
            "-f", "source[branch]=gh-pages", "-f", "source[path]=/"])
        print("Pages: enabled on gh-pages /")


def report(slug: str) -> None:
    info = gh(["api", f"repos/{slug}/pages"], check=False)
    if info.returncode != 0:
        print("Pages status unavailable")
        return
    import json
    data = json.loads(info.stdout)
    print(f"status: {data.get('status')}  url: {data.get('html_url')}")
    if data.get("status") != "built":
        print("the first build can take a minute — re-run `gh api repos/%s/pages` to check" % slug)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"owner/name (default {DEFAULT_REPO})")
    parser.add_argument("--site-only", action="store_true",
                        help="publish docs/ only (skip repo creation and source push)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run([sys.executable, str(ROOT / "scripts" / "build_graph.py")])
    if not args.site_only:
        ensure_repo(args.repo, args.dry_run)
        push_source(args.repo, args.dry_run)
    publish_site(args.repo, args.dry_run)
    if not args.dry_run:
        enable_pages(args.repo)
        report(args.repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
