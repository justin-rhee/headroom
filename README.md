# headroom

[![tests](https://github.com/justin-rhee/headroom/actions/workflows/test.yml/badge.svg)](https://github.com/justin-rhee/headroom/actions/workflows/test.yml) [![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) ![platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg) ![python 3](https://img.shields.io/badge/python-3-blue.svg)

Shows how much of your Claude plan and OpenRouter budget is left, right in the Mac menu bar.

<!-- SCREENSHOT: the menu bar title plus the open menu, dark mode, captured on Justin's Mac -->

```bash
git clone https://github.com/justin-rhee/headroom
cd headroom && bash setup.sh
```

How much runway do I have right now? I was answering that several times a day the slow way: one dashboard for a usage percentage, another for spend, losing the thread of what I was doing. Running more than one Claude account made it worse, because the account with the answer was never the one logged in.

## Use it if

- your Claude plan's limits keep landing mid task instead of in view
- you run more than one Claude account and forget which has room
- you'd rather glance than open a dashboard, a terminal or a second login

## Install

`setup.sh` checks prerequisites (macOS, python3, Homebrew if SwiftBar is missing), installs [SwiftBar](https://swiftbar.app), points it at the plugin and launches. It's one Python script with no build step and no daemon, and safe to re-run. Then set up either half:

- for Claude meters: `uv tool install claude-swap==0.25.0`, log into an account in Claude Code, run `cswap add`, and repeat per account
- for OpenRouter spend: open a key at openrouter.ai/keys with a monthly cap, copy it, and run `pbpaste > ~/.openrouter_agent_key && chmod 600 ~/.openrouter_agent_key`

Click Refresh usage and the meters appear. A rejected key shows its HTTP status rather than pretending nothing is set up.

## How it works

The Claude half runs [claude-swap](https://github.com/realiti4/claude-swap)'s `cswap list --json` and draws the 5-hour and weekly windows as meters, per model. Account storage, switching and polling are all cswap's, and its polling stays inside Anthropic's usage-API budget. The OpenRouter half asks OpenRouter what your key has spent against its cap; the key goes nowhere else.

The halves are independent. The title shows your worst number, falling back from Claude windows to OpenRouter spend to a quiet dot, and anything unreadable shows as "no data" rather than a guess. Each other account's row can switch Claude Code to it.

## What it won't do

- give you more quota or lower your bill; it shows the numbers
- alert you yet, so you have to look; a notification at a percentage you pick is next
- act on what it shows; [openclaw-spillway](https://github.com/justin-rhee/openclaw-spillway) moves an OpenClaw agent's work before a window runs out
- see providers it doesn't know; other providers are welcome as issues
- read an OpenRouter key from your shell profile, since SwiftBar launches outside your shell, so the file is the reliable path
- run anywhere but macOS, since SwiftBar, the Keychain and `defaults` exist nowhere else; CI runs the tests on Linux only as a code-health check

## How I tested it

- 16 offline tests: `python3 -m unittest discover -s tests`, pinning colors that flip exactly at 60 and 80, bars clamped at both ends, and junk data parsing to "no data"
- one test plants an account name carrying SwiftBar parameter syntax and checks it renders as plain text
- flipping the hot-threshold comparison from `>=` to `>` turns exactly one test red; live use is one machine so far, every day, and design decisions are in [docs/ADR.md](docs/ADR.md)

## License

MIT. See [LICENSE](LICENSE). No warranty. Security notes and how to report a problem: [SECURITY.md](SECURITY.md).

<!-- related:start -->
## Related

- [openclaw-spillway](https://github.com/justin-rhee/openclaw-spillway): moves OpenClaw work to a backup lane before a usage window runs out

Part of a small set of tools I pulled out of my own agent harness. I use them myself and read every issue. More on my [GitHub profile](https://github.com/justin-rhee).
<!-- related:end -->
