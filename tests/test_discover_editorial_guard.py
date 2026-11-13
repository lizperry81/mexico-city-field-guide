"""Regression tests for the Discover editorial baseline guard."""
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_discover_editorial_baseline.py"

class EditorialGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "scripts").mkdir()
        shutil.copyfile(SOURCE, self.root / "scripts" / SOURCE.name)
        (self.root / "editorial").mkdir()
        self.policy = self.root / "editorial" / "DISCOVER_APPROVED_BASELINE_2026-11-13.md"
        self.policy.write_text("Approved Discover baseline\n", encoding="utf-8")
        self.git("init", "-q")
        self.git("config", "user.name", "Editorial Guard Test")
        self.git("config", "user.email", "editorial-guard@example.invalid")
        self.git("add", ".")
        self.git("commit", "-qm", "initial baseline")
    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True)
    def check(self, *args):
        return subprocess.run([sys.executable, str(self.root / "scripts" / SOURCE.name), *args],
                              cwd=self.root, capture_output=True, text=True)
    def test_unmodified_baseline_passes(self):
        self.assertEqual(self.check("--base-ref", "HEAD").returncode, 0)
    def test_policy_edit_is_rejected(self):
        self.policy.write_text("Unauthorized replacement\n", encoding="utf-8")
        self.assertNotEqual(self.check("--base-ref", "HEAD").returncode, 0)
    def test_approved_archive_checksum_passes(self):
        d = self.root / "editorial" / "approved"
        d.mkdir()
        p = d / "chapter.md"
        p.write_text("Approved prose\n", encoding="utf-8")
        (d / "chapter.md.sha256").write_text(hashlib.sha256(p.read_bytes()).hexdigest() + "  chapter.md\n")
        self.assertEqual(self.check().returncode, 0)
    def test_modified_archive_fails_checksum(self):
        d = self.root / "editorial" / "approved"
        d.mkdir()
        p = d / "chapter.md"
        p.write_text("Approved prose\n", encoding="utf-8")
        (d / "chapter.md.sha256").write_text(hashlib.sha256(p.read_bytes()).hexdigest() + "  chapter.md\n")
        p.write_text("Truncated prose\n", encoding="utf-8")
        self.assertNotEqual(self.check().returncode, 0)
    def test_new_approved_archive_in_pr_requires_review(self):
        d = self.root / "editorial" / "approved"
        d.mkdir()
        (d / "chapter.md").write_text("Proposed archive\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "proposed protected archive")
        self.assertNotEqual(self.check("--base-ref", "HEAD~1").returncode, 0)

if __name__ == "__main__":
    unittest.main()
