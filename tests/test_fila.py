"""Tests for fila. Run: python3 -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

FILA = Path(__file__).resolve().parent.parent / "fila"


CONFIG = tempfile.mkdtemp()      # registry of projects isolated from the real ~/.config


def run(cwd, *args, check=True, home=None):
    env = {**os.environ, "NO_COLOR": "1", "XDG_CONFIG_HOME": CONFIG}
    if home:
        env["HOME"] = str(home)
    env.pop("FORCE_COLOR", None)
    env.pop("FILA_ROOT", None)
    r = subprocess.run([sys.executable, str(FILA), *args], cwd=cwd, capture_output=True, text=True, env=env)
    if check and r.returncode != 0:
        raise AssertionError(f"fila {' '.join(args)} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r


class FilaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        run(self.d, "init")

    def tearDown(self):
        self.tmp.cleanup()

    def new_script(self, name, body, mid):
        p = self.d / ".fila" / "migrations" / f"{mid}_{name}.sh"
        p.write_text(f"#!/usr/bin/env bash\n# {name} description\n{body}\n")
        return p

    def status(self):
        return json.loads(run(self.d, "status", "--json").stdout)

    def test_new_creates_timestamped_files(self):
        out = run(self.d, "new", "Render the video").stdout.strip()
        self.assertRegex(out, r"^\.fila/migrations/\d{14}_render_the_video\.sh$")
        self.assertTrue(os.access(self.d / out, os.X_OK))
        out = run(self.d, "new", "review subtitles", "--md").stdout.strip()
        self.assertTrue(out.endswith("_review_subtitles.md"))
        self.assertEqual(len(self.status()["pending"]), 2)

    def test_run_in_order_and_record_ids(self):
        self.new_script("b", "echo B >> order.txt", "20260101000002")
        self.new_script("a", "echo A >> order.txt", "20260101000001")
        run(self.d, "run")
        self.assertEqual((self.d / "order.txt").read_text(), "A\nB\n")
        done = (self.d / ".fila" / "done").read_text().splitlines()
        self.assertEqual([l.split("\t")[0] for l in done], ["20260101000001", "20260101000002"])
        self.assertEqual(self.status()["pending"], [])
        run(self.d, "run")                       # second run: nothing happens
        self.assertEqual((self.d / "order.txt").read_text(), "A\nB\n")

    def test_failure_stops_queue_and_is_not_recorded(self):
        self.new_script("ok", "true", "20260101000001")
        self.new_script("boom", "exit 3", "20260101000002")
        self.new_script("after", "touch after.txt", "20260101000003")
        r = run(self.d, "run", check=False)
        self.assertEqual(r.returncode, 3)
        self.assertFalse((self.d / "after.txt").exists())
        self.assertEqual([m["id"] for m in self.status()["pending"]], ["20260101000002", "20260101000003"])

    def test_tasks_are_not_run_but_can_be_marked(self):
        (self.d / ".fila" / "migrations" / "20260101000001_review.md").write_text("# Review the cut\n")
        r = run(self.d, "run")
        self.assertIn("nothing to run", r.stdout)
        run(self.d, "done", "20260101000001")
        self.assertEqual(self.status()["pending"], [])
        run(self.d, "undo", "2026010100000")       # prefix works
        self.assertEqual(len(self.status()["pending"]), 1)

    def test_hook_is_silent_when_empty_and_json_when_pending(self):
        self.assertEqual(run(self.d, "hook").stdout, "")
        self.new_script("render", "true", "20260101000001")
        out = json.loads(run(self.d, "hook").stdout)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("20260101000001 render [script]: render description", ctx)

    def test_hook_outside_a_project_is_silent(self):
        with tempfile.TemporaryDirectory() as other:
            self.assertEqual(run(other, "hook").stdout, "")

    def test_install_hook_is_idempotent_and_keeps_settings(self):
        s = self.d / ".claude" / "settings.json"
        s.parent.mkdir()
        s.write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]}}))
        run(self.d, "install-hook")
        run(self.d, "install-hook")
        cfg = json.loads(s.read_text())
        self.assertEqual(cfg["permissions"]["allow"], ["Bash(ls)"])
        self.assertEqual(len(cfg["hooks"]["SessionStart"]), 1)

    def test_global_hook_reports_registered_projects_from_anywhere(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as elsewhere:
            cfg = Path(home) / "cfg"
            env_home = Path(home)
            self.new_script("render", "true", "20260101000001")
            r = subprocess.run([sys.executable, str(FILA), "install-hook", "--global"], cwd=self.d, text=True,
                               capture_output=True, env={**os.environ, "HOME": home, "XDG_CONFIG_HOME": str(cfg)})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((env_home / ".claude" / "settings.json").exists())
            r = subprocess.run([sys.executable, str(FILA), "hook"], cwd=elsewhere, text=True, capture_output=True,
                               env={**os.environ, "HOME": home, "XDG_CONFIG_HOME": str(cfg)})
            ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("20260101000001 render", ctx)
            self.assertIn(str(self.d.resolve()), ctx)

    def test_log_is_written(self):
        self.new_script("talk", "echo hello-from-migration", "20260101000001")
        run(self.d, "run")
        self.assertIn("hello-from-migration", run(self.d, "log", "20260101000001").stdout)

    def test_env_and_cwd(self):
        sub = self.d / "deep" / "inside"
        sub.mkdir(parents=True)
        self.new_script("env", 'echo "$FILA_ID $(pwd)" > env.txt', "20260101000001")
        run(sub, "run")                            # finds .fila/ in a parent directory
        self.assertEqual((self.d / "env.txt").read_text().strip(), f"20260101000001 {self.d.resolve()}")


if __name__ == "__main__":
    unittest.main()
