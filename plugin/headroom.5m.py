#!/usr/bin/env python3
"""Headroom: AI usage meters in the macOS menu bar, via SwiftBar.

Anthropic section: every claude-swap account's 5-hour and weekly windows,
per-model rows, reset times. OpenRouter section: key spend against its cap.
Each section stands alone — an OpenRouter-only setup gets a real title and a
real spend bar with no Anthropic account anywhere.

Filename encodes the refresh cadence (5m). cswap itself decides when to really
hit Anthropic's usage API (its poll policy stays inside the API budget), so
this script is safe to run on every SwiftBar refresh.

Dev/testing: CLAUDE_USAGE_STUB=/path/to.json renders a canned cswap payload
(the value "missing" simulates cswap not installed), and
HEADROOM_STUB_OPENROUTER='{"usage": 12.34, "limit": 100}' stubs the spend.
"""

# <swiftbar.title>Headroom</swiftbar.title>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>

import json
import os
import shutil
import subprocess
import urllib.request
from datetime import datetime, timezone

VERSION = "0.2.2"
GITHUB_URL = "https://github.com/justin-rhee"
OPENCLAW_URL = "https://github.com/openclaw/openclaw"
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WARN_PCT = 60
HOT_PCT = 80
BAR_CELLS = 8


def _read_key_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


# OpenRouter has no quota windows; its usage is key spend. The key is read at
# runtime on this machine only: env first, then the conventional key file.
OPENROUTER_KEY_SOURCES = [
    lambda: os.environ.get("OPENROUTER_API_KEY"),
    lambda: _read_key_file(os.path.expanduser("~/.openrouter_agent_key")),
]


def _normalize_spend(data):
    usage = data.get("usage")
    limit = data.get("limit")
    if not isinstance(usage, (int, float)):
        return None
    return float(usage), float(limit) if isinstance(limit, (int, float)) else None


def openrouter_spend():
    """Return (spend, note): spend is (usage_usd, limit_usd_or_None) or None,
    and note says WHY when spend is None ("no-key", "http NNN", ...) so the
    menu can answer "why doesn't OpenRouter show as connected"."""
    stub = os.environ.get("HEADROOM_STUB_OPENROUTER")
    if stub:
        try:
            return _normalize_spend(json.loads(stub)), "stub"
        except (json.JSONDecodeError, AttributeError):
            return None, "stub unreadable"
    key = None
    for source in OPENROUTER_KEY_SOURCES:
        key = source()
        if key:
            break
    if not key:
        return None, "no-key"
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/auth/key",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.load(resp).get("data") or {}
    except urllib.error.HTTPError as e:
        return None, f"http {e.code}"
    except Exception as e:
        return None, f"network error: {type(e).__name__}"
    spend = _normalize_spend(data)
    return spend, "ok" if spend else "unexpected response shape"


CSWAP_CANDIDATES = [
    shutil.which("cswap"),
    os.path.expanduser("~/.local/bin/cswap"),
    "/opt/homebrew/bin/cswap",
]


def find_cswap():
    for c in CSWAP_CANDIDATES:
        if c and os.path.exists(c):
            return c
    return None


def load_payload():
    stub = os.environ.get("CLAUDE_USAGE_STUB")
    if stub:
        if stub == "missing":
            return None, "missing"
        try:
            with open(stub, "r", encoding="utf-8") as f:
                return json.load(f), "stub"
        except (OSError, json.JSONDecodeError) as e:
            return None, f"stub unreadable: {e}"
    cswap = find_cswap()
    if not cswap:
        return None, "missing"
    try:
        out = subprocess.run(
            [cswap, "list", "--json"],
            capture_output=True,
            text=True,
            timeout=45,
        )
        if out.returncode != 0:
            return None, f"cswap exit {out.returncode}"
        return json.loads(out.stdout), "cswap"
    except subprocess.TimeoutExpired:
        return None, "cswap timed out"
    except (json.JSONDecodeError, OSError) as e:
        return None, f"cswap unreadable: {e}"


def menu_text(s):
    """SwiftBar's row DSL splits params on '|' and rows on newlines. Any
    dynamic text (aliases, emails, provider statuses) must never reach either,
    or a crafted alias could inject menu params like bash=. Substitution, not
    escaping: SwiftBar has no escape syntax for '|' in text."""
    return str(s).replace("|", "/").replace("\n", " ").replace("\r", " ")


def pct_color(pct):
    if pct is None:
        return "gray"
    if pct >= HOT_PCT:
        return "red"
    if pct >= WARN_PCT:
        return "orange"
    return "green"


def bar(pct):
    if pct is None:
        return "?" * BAR_CELLS
    filled = round(max(0.0, min(pct, 100.0)) / 100 * BAR_CELLS)
    return "█" * filled + "░" * (BAR_CELLS - filled)


def fmt_reset(iso):
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        local = dt.astimezone()
        now = datetime.now(timezone.utc)
        if (dt - now).total_seconds() < 86400:
            return local.strftime("resets %-I:%M%p").lower()
        return local.strftime("resets %a %-I%p").lower()
    except ValueError:
        return ""


def window_pct(win):
    if not isinstance(win, dict):
        return None
    pct = win.get("pct")
    return float(pct) if isinstance(pct, (int, float)) else None


def account_windows(acct):
    """Return [(label, pct, resetIso)] for an account.

    Prefers live `usage`; falls back to `lastGoodUsage` (marked stale by the
    caller via usageStatus). Per-model weekly rows ride under `scoped` when
    cswap reports them; shape is tolerated loosely.
    """
    usage = acct.get("usage") or acct.get("lastGoodUsage") or {}
    rows = []
    for key, label in (("fiveHour", "5h"), ("sevenDay", "7d")):
        win = usage.get(key)
        pct = window_pct(win)
        if pct is not None:
            rows.append((label, pct, (win or {}).get("resetsAt")))
    scoped = usage.get("scoped")
    if isinstance(scoped, dict):
        items = scoped.items()
    elif isinstance(scoped, list):
        items = [(s.get("name") or s.get("model") or "model", s) for s in scoped if isinstance(s, dict)]
    else:
        items = []
    for name, win in items:
        pct = window_pct(win)
        if pct is not None:
            rows.append((str(name), pct, (win or {}).get("resetsAt")))
    return rows


def short_name(acct):
    alias = acct.get("alias")
    if alias:
        return menu_text(alias)
    email = str(acct.get("email") or f"account {acct.get('number', '?')}")
    return menu_text(email.split("@")[0])


def render_title(accounts, active, spend):
    """Worst Anthropic window when available; else OpenRouter spend; else quiet."""
    if active:
        rows = account_windows(active)
        worst = max((p for _, p, _ in rows), default=None)
        if worst is not None:
            glyph = "●" if worst >= HOT_PCT else "◕" if worst >= WARN_PCT else "◔"
            return f"{glyph} {worst:.0f}%"
        return f"◌ {short_name(active)}"
    if accounts:
        return "◌ no active"
    if spend is not None:
        usage, limit = spend
        return f"${usage:,.0f} of ${limit:,.0f}" if limit else f"${usage:,.2f}"
    return "◌"


def main():
    payload, source = load_payload()
    accounts = (payload.get("accounts") or []) if payload else []
    active = next((a for a in accounts if a.get("active")), None)
    spend, spend_note = openrouter_spend()
    cswap_bin = find_cswap()

    print(render_title(accounts, active, spend))
    print("---")
    print("🔄 Refresh usage | refresh=true")
    print("---")

    print("Anthropic | size=11 color=gray")
    if payload is None:
        if source == "missing":
            # Same empty-state pattern as OpenRouter: sell the value, link setup.
            print(
                f'Track your Claude account usage · click to set up | size=11 color=gray bash=/usr/bin/open param1="{REPO_DIR}/README.md" terminal=false'
            )
        else:
            print(f"usage unavailable: {menu_text(source)} | size=11 color=orange")
    elif not accounts:
        print("no accounts yet | color=gray")

    # Flat rows, no "--" prefixes for meters: SwiftBar renders "--" lines as a
    # nested submenu, and the whole point is meters visible on first click.
    # The one deliberate submenu is on each account NAME row: actions live
    # there without hiding any numbers.
    for i, acct in enumerate(accounts):
        if i > 0:
            print("---")
        name = short_name(acct)
        number = acct.get("number")
        status = acct.get("usageStatus")
        marks = []
        if acct.get("active"):
            marks.append("active")
        if acct.get("disabled"):
            marks.append("disabled")
        if status and status not in ("ok",):
            marks.append(menu_text(str(status).replace("_", " ")))
        suffix = f"  ({', '.join(marks)})" if marks else ""
        print(f"{name}{suffix} | size=13")
        if not acct.get("active") and number is not None and cswap_bin:
            print(
                f'-- Switch Claude Code to this account | bash="{cswap_bin}" param1=switch param2={number} terminal=false refresh=true'
            )

        rows = account_windows(acct)
        if not rows:
            print("no usage data | color=gray")
        for label, pct, reset in rows:
            reset_txt = fmt_reset(reset)
            tail = f"  {reset_txt}" if reset_txt else ""
            print(
                f"{menu_text(label):>5} {bar(pct)} {pct:3.0f}%{tail} | font=Menlo size=12 color={pct_color(pct)} trim=false"
            )
        age = acct.get("usageAgeSeconds") or acct.get("lastGoodAgeSeconds")
        if isinstance(age, (int, float)) and age >= 300:
            print(f"measured {int(age // 60)}m ago | size=10 color=gray")

    if source != "missing":
        print(
            f'+ Add account… | size=11 color=gray bash="{REPO_DIR}/bin/add-account.sh" terminal=true'
        )

    print("---")
    print("OpenRouter | size=11 color=gray")
    if spend is None and spend_note == "no-key":
        print(
            f'Track your OpenRouter spend · click to set up | size=11 color=gray bash=/usr/bin/open param1="{REPO_DIR}/README.md" terminal=false'
        )
    elif spend is None:
        hint = " (key rotated or revoked?)" if spend_note == "http 401" else ""
        print(f"key found, but: {menu_text(spend_note)}{hint} | size=11 color=orange")
    else:
        usage, limit = spend
        if limit:
            pct = min(usage / limit * 100, 100.0)
            print(
                f"spend {bar(pct)} ${usage:,.2f} of ${limit:,.2f} | font=Menlo size=12 color={pct_color(pct)} trim=false"
            )
        else:
            print(f"spend ${usage:,.2f} (no cap set on key) | font=Menlo size=12")

    print("---")
    if source == "stub":
        print("STUB DATA (CLAUDE_USAGE_STUB) | color=purple")
    if os.environ.get("HEADROOM_STUB_OPENROUTER"):
        print("STUB DATA (HEADROOM_STUB_OPENROUTER) | color=purple")
    print("About")
    print(f"-- Headroom v{VERSION}")
    print(f"-- by justin-rhee | href={GITHUB_URL}")
    print(f"-- 🦞 OpenClaw | href={OPENCLAW_URL}")
    print(f'Quit | bash="{REPO_DIR}/bin/quit-swiftbar.sh" terminal=false')


if __name__ == "__main__":
    main()
