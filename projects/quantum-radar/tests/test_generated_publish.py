from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / ".github/scripts/push-generated.sh"


class GeneratedPublishTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.worker = self.root / "worker"
        self.editor = self.root / "editor"
        self.env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
        self.git(self.root, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(self.root, "clone", str(self.remote), str(self.worker))
        self.commit(self.worker, "shared.txt", "original\n")
        self.git(self.worker, "push", "origin", "HEAD:main")
        self.git(self.root, "clone", str(self.remote), str(self.editor))

    def git(self, cwd: Path, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=cwd, env=self.env, check=True,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.strip()

    def commit(self, cwd: Path, name: str, text: str) -> None:
        (cwd / name).write_text(text, encoding="utf-8")
        self.git(cwd, "add", name)
        self.git(cwd, "commit", "-m", f"Update {name}")

    def publish(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(SCRIPT), "main"], cwd=self.worker, env=self.env,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )

    def test_remote_edits_and_generated_commit_are_preserved(self) -> None:
        self.commit(self.worker, "generated.txt", "report\n")
        self.commit(self.editor, "manual.txt", "manual edit\n")
        self.git(self.editor, "push", "origin", "HEAD:main")
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.git(self.editor, "pull", "--ff-only")
        self.assertEqual((self.editor / "generated.txt").read_text(), "report\n")
        self.assertEqual((self.editor / "manual.txt").read_text(), "manual edit\n")

    def test_conflict_fails_without_overwriting_remote(self) -> None:
        self.commit(self.worker, "shared.txt", "generated\n")
        self.commit(self.editor, "shared.txt", "manual\n")
        self.git(self.editor, "push", "origin", "HEAD:main")
        remote_head = self.git(self.editor, "rev-parse", "HEAD")
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("::error::Generated changes conflict", result.stdout)
        self.assertEqual(self.git(self.root, "--git-dir", str(self.remote), "rev-parse", "main"), remote_head)
        self.assertFalse((self.worker / ".git/rebase-merge").exists())

    def test_race_between_fetch_and_push_is_retried(self) -> None:
        self.commit(self.worker, "generated.txt", "report\n")
        self.commit(self.editor, "manual.txt", "racing edit\n")
        hook = self.worker / ".git/hooks/pre-push"
        hook.write_text(
            "#!/usr/bin/env bash\nset -e\n"
            "if [ ! -f .git/race-triggered ]; then\n"
            "  touch .git/race-triggered\n"
            f"  git -C '{self.editor}' push origin HEAD:main\n"
            "fi\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("::warning::Push failed", result.stdout)
        self.git(self.editor, "pull", "--ff-only")
        self.assertEqual((self.editor / "generated.txt").read_text(), "report\n")
        self.assertEqual((self.editor / "manual.txt").read_text(), "racing edit\n")


if __name__ == "__main__":
    unittest.main()
