from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from common import ROOT, REPORTS, clip, load_yaml, stable_id, today_str, utc_now, write_text


TMP = ROOT / "tmp"


@dataclass
class CommandResult:
    command: str
    returncode: int
    seconds: float
    output: str


@dataclass
class RepoResult:
    slug: str
    branch: str
    clone_ok: bool
    setup_results: list[CommandResult]
    check_results: list[CommandResult]
    error: str = ""

    @property
    def ok(self) -> bool:
        if not self.clone_ok:
            return False
        return all(r.returncode == 0 for r in self.setup_results + self.check_results)


def run_command(cmd: str, cwd: Path) -> CommandResult:
    start = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    seconds = time.time() - start
    return CommandResult(
        command=cmd,
        returncode=proc.returncode,
        seconds=seconds,
        output=clip(proc.stdout, 3000),
    )


def clone_repo(slug: str, branch: str, token: str | None, dst: Path) -> tuple[bool, str]:
    if dst.exists():
        shutil.rmtree(dst)
    if token:
        url = f"https://x-access-token:{token}@github.com/{slug}.git"
    else:
        url = f"https://github.com/{slug}.git"
    cmd = ["git", "clone", "--depth", "1", "--branch", branch, url, str(dst)]
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode == 0, clip(proc.stdout, 3000)


def make_markdown(results: list[RepoResult]) -> str:
    now = utc_now().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Repo health report",
        "",
        f"_Generated: {now}_",
        "",
        "| Repository | Branch | Status |",
        "|---|---:|---:|",
    ]
    for r in results:
        status = "✅ pass" if r.ok else "❌ fail"
        lines.append(f"| `{r.slug}` | `{r.branch}` | {status} |")

    lines.append("")
    for r in results:
        lines.append(f"## {r.slug}")
        lines.append("")
        lines.append(f"- Branch: `{r.branch}`")
        lines.append(f"- Overall status: {'pass' if r.ok else 'fail'}")
        if r.error:
            lines.append(f"- Clone error: `{r.error}`")
        lines.append("")

        if r.setup_results:
            lines.append("### Setup")
            lines.append("")
            for item in r.setup_results:
                lines.append(f"- `{item.command}` → exit {item.returncode} in {item.seconds:.1f}s")
                if item.output:
                    lines.append("")
                    lines.append("```text")
                    lines.append(item.output)
                    lines.append("```")
            lines.append("")

        if r.check_results:
            lines.append("### Checks")
            lines.append("")
            for item in r.check_results:
                lines.append(f"- `{item.command}` → exit {item.returncode} in {item.seconds:.1f}s")
                if item.output:
                    lines.append("")
                    lines.append("```text")
                    lines.append(item.output)
                    lines.append("```")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def create_failure_issue(results: list[RepoResult], report_path: Path) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return

    failures = [r for r in results if not r.ok]
    if not failures:
        return

    title = f"Repo health failures - {today_str()}"
    run_url = None
    server = os.environ.get("GITHUB_SERVER_URL")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        run_url = f"{server}/{repo}/actions/runs/{run_id}"

    body_lines = [
        "Automated repo health check found failures.",
        "",
        "## Failed repositories",
        "",
    ]
    for r in failures:
        body_lines.append(f"- `{r.slug}` on `{r.branch}`")
    if run_url:
        body_lines.extend(["", f"Workflow run: {run_url}"])
    body_lines.extend(["", f"Report file: `{report_path.as_posix()}`"])

    requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "title": title,
            "body": "\n".join(body_lines),
            "labels": ["repo-health"],
        },
        timeout=30,
    )


def main() -> int:
    cfg = load_yaml(ROOT / "config" / "monitored_repos.yaml")
    repos = cfg.get("repos", [])
    token = os.environ.get("MONITORED_REPOS_TOKEN")

    TMP.mkdir(parents=True, exist_ok=True)
    results: list[RepoResult] = []

    for repo_cfg in repos:
        slug = repo_cfg["slug"]
        branch = repo_cfg.get("branch", "main")
        setup_cmds = list(repo_cfg.get("setup", []))
        check_cmds = list(repo_cfg.get("checks", []))
        repo_dir = TMP / stable_id(slug, branch)

        clone_ok, clone_output = clone_repo(slug, branch, token, repo_dir)
        result = RepoResult(
            slug=slug,
            branch=branch,
            clone_ok=clone_ok,
            setup_results=[],
            check_results=[],
            error="" if clone_ok else clone_output,
        )

        if clone_ok:
            for cmd in setup_cmds:
                cmd_result = run_command(cmd, repo_dir)
                result.setup_results.append(cmd_result)
                if cmd_result.returncode != 0:
                    break

            if all(r.returncode == 0 for r in result.setup_results):
                for cmd in check_cmds:
                    result.check_results.append(run_command(cmd, repo_dir))

        results.append(result)

    latest = REPORTS / "repo-health" / "latest.md"
    dated = REPORTS / "repo-health" / today_str() / "report.md"
    text = make_markdown(results)
    write_text(latest, text)
    write_text(dated, text)
    create_failure_issue(results, latest)

    failures = sum(1 for r in results if not r.ok)
    print(f"Checked {len(results)} repositories; failures={failures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
