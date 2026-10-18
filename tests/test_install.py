"""Installer tests (repo only, not shipped in the skill). Run: python3 -m unittest discover -s tests"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL = os.path.join(ROOT, "install.sh")
# macOS ships bash 3.2 as /bin/bash: the tests install for real with it (empty arrays under `set -u`).
BASH = "/bin/bash" if os.path.exists("/bin/bash") else "bash"
GIT_ID = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
          "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
MANIFEST = ".mk-studio-manifest"
SOURCE_FILE = ".mk-studio-source"


def version(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip().startswith("version:"):
                return line.split(":", 1)[1].strip().strip('"')
    return None


def write_skill(checkout, name, ver):
    """A minimal skill: the installer tests must not depend on the content of any skill."""
    os.makedirs(os.path.join(checkout, "skills", name, "references"), exist_ok=True)
    with open(os.path.join(checkout, "skills", name, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write(f'---\nname: {name}\ndescription: test skill\nmetadata:\n  version: "{ver}"\n---\n# {name}\n')
    with open(os.path.join(checkout, "skills", name, "references", "a.md"), "w", encoding="utf-8") as fh:
        fh.write("a\n")


def set_version(skill_md, ver):
    with open(skill_md, encoding="utf-8") as fh:
        text = fh.read()
    with open(skill_md, "w", encoding="utf-8") as fh:
        fh.write(re.sub(r'^(\s*version:\s*)"[^"]*"', rf'\g<1>"{ver}"', text, count=1, flags=re.M))


def make_checkout(path):
    """Copy of the working tree's installer (uncommitted code included) plus minimal skills `star` and `viet`."""
    os.makedirs(os.path.join(path, "skills"))
    shutil.copy2(INSTALL, path)
    write_skill(path, "star", "0.1.0")
    write_skill(path, "viet", "0.1.0")


def snapshot(folder):
    """relative path → bytes of every file under folder ({} when missing)."""
    out = {}
    for base, _, files in os.walk(folder):
        for f in files:
            p = os.path.join(base, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, folder)] = fh.read()
    return out


class SkillCase(unittest.TestCase):
    """Checkout with skills star + viet, fake HOME, installer run by the system bash."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.checkout = os.path.join(self.tmp, "checkout")
        make_checkout(self.checkout)
        self.env = {**{k: v for k, v in os.environ.items() if k != "MK_STUDIO_UPDATED"}, "HOME": self.home, **GIT_ID}
        self.proj = os.path.join(self.tmp, "proj")
        os.makedirs(self.proj)
        subprocess.run(["git", "init", "-q", self.proj], check=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def install(self, *args):
        return subprocess.run([BASH, os.path.join(self.checkout, "install.sh"), *args],
                              capture_output=True, text=True, env=self.env)

    def ok(self, *args):
        res = self.install(*args)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        return res

    def h(self, *parts):
        return os.path.join(self.home, *parts)

    def p(self, *parts):
        return os.path.join(self.proj, *parts)

    def git(self, cwd, *args):
        subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True, env=self.env)

    def foreign(self, folder):
        os.makedirs(folder)
        with open(os.path.join(folder, "keep.txt"), "w") as fh:
            fh.write("keep")


class GlobalSkill(SkillCase):
    def test_global_install_defaults_to_star_in_both_folders(self):
        res = self.ok("--global")
        self.assertIn("star 0.1.0", res.stdout)
        for base in (".claude", ".agents"):
            dest = self.h(base, "skills", "star")
            for f in ("SKILL.md", os.path.join("references", "a.md"), MANIFEST, SOURCE_FILE):
                self.assertTrue(os.path.isfile(os.path.join(dest, f)), (dest, f))
            with open(os.path.join(dest, SOURCE_FILE), encoding="utf-8") as fh:
                self.assertEqual(fh.read().strip(), self.checkout)
            self.assertIn(f"global: {dest} (none → 0.1.0)", res.stdout)
            self.assertFalse(os.path.exists(self.h(base, "skills", "viet")))

    def test_global_install_of_another_skill_leaves_star_alone(self):
        self.ok("--global")
        before = snapshot(self.h(".claude", "skills", "star")), snapshot(self.h(".agents", "skills", "star"))
        self.ok("--global", "--skill", "viet")
        self.assertTrue(os.path.isfile(self.h(".claude", "skills", "viet", MANIFEST)))
        after = snapshot(self.h(".claude", "skills", "star")), snapshot(self.h(".agents", "skills", "star"))
        self.assertEqual(before, after)

    def test_bad_skill_arguments_are_refused_with_the_skill_list_and_install_nothing(self):
        for args in (["--global", "--skill", "khong-co"], ["--global", "--skill", "../x"], ["--global", "--skill", "-x"],
                     ["--global", "--skill"], ["--skill", "--global"], ["--global", "--skill="],
                     ["--global", "--skill", "star", "--skill", "star"], ["--global", "--skill=star", "--skill=viet"]):
            res = self.install(*args)
            self.assertEqual(res.returncode, 1, args)
            self.assertIn("star, viet", res.stderr, args)
        self.assertEqual(os.listdir(self.home), [])

    def test_global_refuses_a_folder_it_did_not_create_until_forced(self):
        self.foreign(self.h(".agents", "skills", "star"))
        res = self.install("--global")
        self.assertEqual(res.returncode, 1)
        self.assertIn("was not installed by install.sh", res.stderr)
        self.assertEqual(os.listdir(self.h(".agents", "skills", "star")), ["keep.txt"])
        self.assertFalse(os.path.exists(self.h(".claude", "skills", "star")))
        self.ok("--global", "--force")
        self.assertFalse(os.path.exists(self.h(".agents", "skills", "star", "keep.txt")))
        self.assertTrue(os.path.isfile(self.h(".agents", "skills", "star", MANIFEST)))

    def test_symlinked_skill_folder_is_refused_and_target_kept(self):
        elsewhere = os.path.join(self.tmp, "elsewhere")
        self.foreign(elsewhere)
        os.makedirs(self.h(".claude", "skills"))
        os.symlink(elsewhere, self.h(".claude", "skills", "star"))
        for args in (["--global"], ["--global", "--force"], ["--uninstall", "--global"]):
            res = self.install(*args)
            self.assertNotEqual(res.returncode, 0, args)
            self.assertIn("symlink", res.stderr)
        self.assertEqual(os.listdir(elsewhere), ["keep.txt"])
        self.assertFalse(os.path.exists(self.h(".agents")))

    def test_help_shows_the_whole_header_with_private_clone_line(self):
        res = self.ok("--help")
        self.assertIn("--skill", res.stdout)
        self.assertIn("gh repo clone mzavn/mk-studio", res.stdout)
        self.assertIn("MK_STUDIO_HOME", res.stdout)
        self.assertNotIn("curl", res.stdout)
        self.assertNotIn("set -euo", res.stdout)

    def test_installer_parses_on_system_bash(self):
        for bash in ("bash", "/bin/bash"):
            if shutil.which(bash) or os.path.exists(bash):
                self.assertEqual(subprocess.run([bash, "-n", INSTALL]).returncode, 0, bash)


class ProjectSkill(SkillCase):
    def test_project_install_copies_only_the_skill_folder(self):
        with open(self.p("AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write("# Luật\n")
        self.ok("--project", self.proj)
        self.assertTrue(os.path.isfile(self.p(".claude", "skills", "star", MANIFEST)))
        self.assertFalse(os.path.exists(self.p(".claude", "skills", "star", SOURCE_FILE)))
        self.assertEqual(sorted(os.listdir(self.proj)), [".claude", ".git", "AGENTS.md"])
        with open(self.p("AGENTS.md"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "# Luật\n")
        self.ok("--project", self.proj, "--agents-dir")
        self.assertTrue(os.path.isfile(self.p(".agents", "skills", "star", MANIFEST)))

    def test_hand_edit_in_project_copy_is_not_overwritten_until_forced(self):
        self.ok("--project", self.proj, "--agents-dir")
        for base in (".claude", ".agents"):
            skill = self.p(base, "skills", "star", "SKILL.md")
            with open(skill, "a", encoding="utf-8") as fh:
                fh.write("\nsửa tay\n")
            res = self.install("--project", self.proj)
            self.assertEqual(res.returncode, 1, base)
            self.assertIn("has edits not made by install.sh", res.stderr)
            self.assertIn("SKILL.md", res.stderr)
            with open(skill, encoding="utf-8") as fh:
                self.assertIn("sửa tay", fh.read())
            self.ok("--project", self.proj, "--force")
            with open(skill, encoding="utf-8") as fh:
                self.assertNotIn("sửa tay", fh.read())

    def test_committed_folder_without_manifest_blocks_every_destination(self):
        for foreign, other in ((".claude", ".agents"), (".agents", ".claude")):
            self.foreign(self.p(foreign, "skills", "star"))
            self.git(self.proj, "add", "-A")
            self.git(self.proj, "commit", "-q", "-m", "foreign star")
            res = self.install("--project", self.proj, "--agents-dir")
            self.assertEqual(res.returncode, 1, foreign)
            self.assertIn("was not installed by install.sh", res.stderr)
            self.assertEqual(os.listdir(self.p(foreign, "skills", "star")), ["keep.txt"])
            self.assertFalse(os.path.exists(self.p(other, "skills", "star")), foreign)
            self.git(self.proj, "rm", "-q", "-r", foreign)
            self.git(self.proj, "commit", "-q", "-m", "drop")


class UninstallSkill(SkillCase):
    def test_uninstall_removes_both_copies_and_keeps_other_skills(self):
        self.ok("--global")
        self.ok("--global", "--skill", "viet")
        self.ok("--project", self.proj, "--agents-dir")
        kept = snapshot(self.h(".claude", "skills", "viet"))
        res = self.ok("--uninstall", "--global", "--project", self.proj)
        for path in (self.h(".claude", "skills", "star"), self.h(".agents", "skills", "star"),
                     self.p(".claude", "skills", "star"), self.p(".agents", "skills", "star")):
            self.assertFalse(os.path.exists(path), path)
            self.assertIn(f"removed {path}", res.stdout)
        self.assertEqual(kept, snapshot(self.h(".claude", "skills", "viet")))

    def test_uninstall_when_nothing_installed_says_so(self):
        res = self.ok("--uninstall", "--project", self.proj)
        self.assertIn("not installed", res.stdout)
        self.assertNotIn("removed", res.stdout)

    def test_uninstall_refuses_any_copy_without_manifest_or_with_edits(self):
        self.ok("--global")
        os.remove(self.h(".claude", "skills", "star", MANIFEST))
        res = self.install("--uninstall", "--global")
        self.assertEqual(res.returncode, 1)
        self.assertIn("was not installed by install.sh", res.stderr)
        self.assertTrue(os.path.isdir(self.h(".claude", "skills", "star")))
        self.assertTrue(os.path.isdir(self.h(".agents", "skills", "star")))

        self.ok("--project", self.proj)
        with open(self.p(".claude", "skills", "star", "SKILL.md"), "a", encoding="utf-8") as fh:
            fh.write("\nsửa tay\n")
        res = self.install("--uninstall", "--project", self.proj)
        self.assertEqual(res.returncode, 1)
        self.assertIn("has edits not made by install.sh", res.stderr)
        self.assertTrue(os.path.isfile(self.p(".claude", "skills", "star", "SKILL.md")))


class UpdateSkills(SkillCase):
    """--update from a clone of a throwaway source repo built from the working tree, so uncommitted code is tested."""

    def setUp(self):
        super().setUp()
        self.source = self.checkout
        self.git(self.source, "init", "-q")
        self.commit_source("v1")
        self.checkout = os.path.join(self.tmp, "clone")
        subprocess.run(["git", "clone", "-q", self.source, self.checkout], check=True, env=self.env)

    def commit_source(self, msg):
        self.git(self.source, "add", "-A")
        self.git(self.source, "commit", "-q", "-m", msg)

    def bump_source(self, ver):
        for name in ("star", "viet"):
            set_version(os.path.join(self.source, "skills", name, "SKILL.md"), ver)
        self.commit_source(f"bump {ver}")

    def test_update_pulls_then_refreshes_every_global_skill(self):
        self.ok("--global")
        self.ok("--global", "--skill", "viet")
        self.bump_source("0.2.0")
        res = self.ok("--update")
        self.assertIn("mk-studio: ", res.stdout)
        for name in ("star", "viet"):
            for base in (".claude", ".agents"):
                self.assertIn(f"global: {self.h(base, 'skills', name)} (0.1.0 → 0.2.0)", res.stdout)
                self.assertEqual(version(self.h(base, "skills", name, "SKILL.md")), "0.2.0")

    def test_update_of_project_refreshes_only_what_is_there(self):
        self.ok("--project", self.proj, "--skill", "viet")
        self.bump_source("0.2.0")
        res = self.ok("--update", "--project", self.proj)
        self.assertIn("(0.1.0 → 0.2.0)", res.stdout)
        self.assertEqual(version(self.p(".claude", "skills", "viet", "SKILL.md")), "0.2.0")
        self.assertFalse(os.path.exists(self.p(".claude", "skills", "star")))
        self.assertFalse(os.path.exists(self.h(".claude")))

    def test_update_with_nothing_installed_installs_star(self):
        res = self.ok("--update")
        self.assertIn("star 0.1.0", res.stdout)
        self.assertTrue(os.path.isfile(self.h(".claude", "skills", "star", MANIFEST)))
        self.assertFalse(os.path.exists(self.h(".claude", "skills", "viet")))

    def test_update_with_a_skill_added_upstream_installs_it_after_pulling(self):
        write_skill(self.source, "moi", "0.1.0")
        self.commit_source("add moi")
        res = self.ok("--update", "--global", "--skill", "moi")
        self.assertTrue(os.path.isfile(self.h(".claude", "skills", "moi", MANIFEST)))
        self.assertFalse(os.path.exists(self.h(".claude", "skills", "star")))
        self.assertIn("moi 0.1.0", res.stdout)

    def test_update_with_unknown_skill_pulls_but_installs_nothing(self):
        self.bump_source("0.2.0")
        res = self.install("--update", "--skill", "khong-co")
        self.assertEqual(res.returncode, 1)
        self.assertIn("mk-studio: ", res.stdout)
        self.assertIn("star, viet", res.stderr)
        self.assertEqual(version(os.path.join(self.checkout, "skills", "star", "SKILL.md")), "0.2.0")
        self.assertEqual(os.listdir(self.home), [])

    def test_update_refuses_to_combine_with_uninstall(self):
        res = self.install("--update", "--uninstall")
        self.assertEqual(res.returncode, 1)
        self.assertIn("do not combine", res.stderr)

    def test_piped_run_installs_from_the_clone_not_the_current_directory(self):
        cwd = os.path.join(self.tmp, "repo")
        os.makedirs(os.path.join(cwd, "skills", "star"))
        with open(os.path.join(cwd, "skills", "star", "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write('---\nname: star\nmetadata:\n  version: "9.9.9"\n---\nfake\n')
        with open(INSTALL, "rb") as fh:
            script = fh.read()
        env = {**self.env, "MK_STUDIO_HOME": os.path.join(self.tmp, "home-clone"), "MK_STUDIO_REPO": self.source}
        res = subprocess.run([BASH, "-s", "--", "--global"], input=script, cwd=cwd, capture_output=True, env=env)
        self.assertEqual(res.returncode, 0, res.stderr.decode())
        self.assertEqual(version(self.h(".claude", "skills", "star", "SKILL.md")), "0.1.0")
        with open(self.h(".claude", "skills", "star", SOURCE_FILE), encoding="utf-8") as fh:
            self.assertEqual(fh.read().strip(), os.path.join(self.tmp, "home-clone"))


if __name__ == "__main__":
    unittest.main()
