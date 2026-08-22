"""Offline pressure test for headroom.

Two layers: unit tests import the plugin module directly and pin every render
boundary; end-to-end tests run the script as SwiftBar would (a subprocess)
against stubbed data and assert on the exact rows, with HOME pointed at an
empty directory so no real key file or account store can leak in.

Load-bearing mutation for the whole suite: flip `>=` to `>` in pct_color's
HOT_PCT comparison and test_color_flips_exactly_at_thresholds goes red.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "plugin", "headroom.5m.py")
STUB = os.path.join(REPO, "dev", "stub-cswap.json")


def load_module():
    spec = importlib.util.spec_from_file_location("headroom", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H = load_module()


def run_script(env_extra):
    """Run the plugin exactly as SwiftBar does, hermetically."""
    empty_home = tempfile.mkdtemp(prefix="headroom-test-home-")
    env = {
        "PATH": "/usr/bin:/bin",  # no cswap on PATH unless a stub provides data
        "HOME": empty_home,  # no real key file, no real account store
    }
    env.update(env_extra)
    out = subprocess.run(
        [sys.executable, SCRIPT], capture_output=True, text=True, timeout=30, env=env
    )
    return out.returncode, out.stdout


class UnitBoundaries(unittest.TestCase):
    def test_color_flips_exactly_at_thresholds(self):
        # The headline visual promise: red means at-or-over the hot line.
        self.assertEqual(H.pct_color(59.9), "green")
        self.assertEqual(H.pct_color(60), "orange")
        self.assertEqual(H.pct_color(79.9), "orange")
        self.assertEqual(H.pct_color(80), "red")
        self.assertEqual(H.pct_color(None), "gray")

    def test_bar_clamps_and_fills(self):
        self.assertEqual(H.bar(0), "░" * 8)
        self.assertEqual(H.bar(100), "█" * 8)
        self.assertEqual(H.bar(150), "█" * 8)
        self.assertEqual(H.bar(-5), "░" * 8)
        self.assertEqual(H.bar(None), "?" * 8)

    def test_menu_text_neutralizes_param_syntax(self):
        self.assertEqual(H.menu_text("a|b"), "a/b")
        self.assertNotIn("\n", H.menu_text("a\nb"))
        self.assertNotIn("\r", H.menu_text("a\rb"))

    def test_fmt_reset_survives_junk(self):
        self.assertEqual(H.fmt_reset(None), "")
        self.assertEqual(H.fmt_reset("not-a-date"), "")

    def test_normalize_spend_shapes(self):
        self.assertEqual(H._normalize_spend({"usage": 5, "limit": 10}), (5.0, 10.0))
        self.assertEqual(H._normalize_spend({"usage": 5}), (5.0, None))
        self.assertIsNone(H._normalize_spend({"limit": 10}))
        self.assertIsNone(H._normalize_spend({"usage": "text"}))


class UnitAccountParsing(unittest.TestCase):
    def test_scoped_real_shape_is_parsed(self):
        # cswap emits scoped as a LIST of windows carrying "name"
        # (json_output.py _scoped_window_to_json), verified against source.
        acct = {"usage": {"scoped": [{"name": "Fable", "pct": 91.0}]}}
        self.assertEqual(H.account_windows(acct), [("Fable", 91.0, None)])

    def test_last_good_usage_fallback(self):
        acct = {"lastGoodUsage": {"fiveHour": {"pct": 40.0}}}
        self.assertEqual(H.account_windows(acct), [("5h", 40.0, None)])

    def test_junk_windows_are_ignored_never_guessed(self):
        acct = {"usage": {"fiveHour": {"pct": "high"}, "scoped": [{}, 3, {"name": "x"}]}}
        self.assertEqual(H.account_windows(acct), [])


class UnitTitle(unittest.TestCase):
    def test_active_account_worst_window_wins(self):
        active = {"usage": {"fiveHour": {"pct": 34.0}, "scoped": [{"name": "F", "pct": 91.0}]}}
        self.assertEqual(H.render_title([active], active, None), "● 91%")

    def test_openrouter_only_falls_back_to_spend(self):
        self.assertEqual(H.render_title([], None, (23.71, 50.0)), "$24 of $50")
        self.assertEqual(H.render_title([], None, (5.0, None)), "$5.00")

    def test_nothing_configured_is_quiet(self):
        self.assertEqual(H.render_title([], None, None), "◌")


class UnitOpenRouterErrors(unittest.TestCase):
    def test_http_error_reports_status_code(self):
        real = H.urllib.request.urlopen

        def raise_401(*a, **k):
            raise urllib.error.HTTPError("u", 401, "unauthorized", {}, None)

        H.urllib.request.urlopen = raise_401
        try:
            os.environ["OPENROUTER_API_KEY"] = "sk-test-dead"
            os.environ.pop("HEADROOM_STUB_OPENROUTER", None)
            spend, note = H.openrouter_spend()
        finally:
            H.urllib.request.urlopen = real
            os.environ.pop("OPENROUTER_API_KEY", None)
        self.assertIsNone(spend)
        self.assertEqual(note, "http 401")


class EndToEnd(unittest.TestCase):
    def test_normal_state_renders_meters_flat(self):
        code, out = run_script(
            {"CLAUDE_USAGE_STUB": STUB, "HEADROOM_STUB_OPENROUTER": '{"usage": 1}'}
        )
        self.assertEqual(code, 0)
        self.assertIn("● 91%", out)
        self.assertIn("alice", out)
        self.assertIn("Fable", out)
        # Meters are top-level rows, never submenu ("--") rows.
        for line in out.splitlines():
            if "█" in line or "░" in line:
                self.assertFalse(line.startswith("--"), line)

    def test_openrouter_only_state(self):
        code, out = run_script(
            {
                "CLAUDE_USAGE_STUB": "missing",
                "HEADROOM_STUB_OPENROUTER": '{"usage": 23.71, "limit": 50}',
            }
        )
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("$24 of $50"))
        self.assertIn("Track your Claude account usage", out)
        self.assertIn("spend ", out)

    def test_nothing_configured_still_renders_both_sections(self):
        code, out = run_script({"CLAUDE_USAGE_STUB": "missing"})
        self.assertEqual(code, 0)
        self.assertIn("Anthropic", out)
        self.assertIn("OpenRouter", out)
        self.assertIn("Track your OpenRouter spend", out)

    def test_alias_injection_renders_inert(self):
        with open(STUB) as f:
            payload = json.load(f)
        payload["accounts"][1]["alias"] = "evil | bash=/bin/rm param1=-rf"
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(payload, tf)
            evil = tf.name
        code, out = run_script(
            {"CLAUDE_USAGE_STUB": evil, "HEADROOM_STUB_OPENROUTER": '{"usage": 1}'}
        )
        self.assertEqual(code, 0)
        evil_lines = [l for l in out.splitlines() if l.startswith("evil")]
        self.assertTrue(evil_lines, "sanitized alias row missing")
        for line in evil_lines:
            self.assertNotIn("| bash=", line)
            self.assertIn("/ bash=", line)


if __name__ == "__main__":
    unittest.main()
