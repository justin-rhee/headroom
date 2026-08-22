# headroom

[![tests](https://github.com/justin-rhee/headroom/actions/workflows/test.yml/badge.svg)](https://github.com/justin-rhee/headroom/actions/workflows/test.yml)

How much runway do I have right now? I was asking that several times a day and answering it the slow way: sign into one dashboard for a usage percentage, another for a spend number, lose the thread of whatever I was actually doing. Multiple Claude accounts made it worse, because the account with the answer was never the one I was logged into. None of these numbers are secret. They're just scattered, and each one lives behind its own login.

Headroom does that in one look instead, from a single Python script that lives in your macOS menu bar and shows how close you are to your Claude and OpenRouter ceilings. Claude accounts get their 5-hour and weekly windows as meters, per-model rows included. OpenRouter gets dollars spent against your key's cap. The bar title is your worst number, so most of the time the answer is one look, no click.

## Use it if

- your Claude plan's limits keep landing mid task instead of in view
- you run more than one Claude account and forget which has room
- you pay for OpenRouter by the token and want the spend where you can see it
- you'd rather glance than open a dashboard, a terminal, or a second login

## How it works

One Python script, hosted by [SwiftBar](https://swiftbar.app) (the open source menu bar host that runs a script on a schedule and renders what it prints). No build step, no daemon, nothing resident beyond SwiftBar itself.

The Anthropic half is built on [claude-swap](https://github.com/realiti4/claude-swap): headroom runs `cswap list --json` as a subprocess and renders the answer. All account storage, switching, and usage polling is cswap's work, and cswap's poll policy stays inside Anthropic's usage-API budget, so the 5-minute refresh is safe. The OpenRouter half asks OpenRouter's key-introspection endpoint what your key has spent; the key goes to openrouter.ai and nowhere else.

The two halves are independent, so you can run both, either, or neither. Each section shows its meters when configured and a one-line setup hint when not, and the bar title falls back from Claude windows to OpenRouter spend to a quiet dot. Anything missing or unreadable renders as "no data" rather than as a guess, so a meter goes quiet instead of going wrong.

Each non-active account's name row opens a submenu with "Switch Claude Code to this account", "+ Add account…" sits at the bottom of the account list, and refresh, About, and Quit do what they say.

## Install

```bash
git clone https://github.com/justin-rhee/headroom
cd headroom && bash setup.sh
```

`setup.sh` checks prerequisites (macOS, python3, Homebrew if SwiftBar needs installing), installs SwiftBar if it's missing, points it at the `plugin/` folder, hides SwiftBar's own icon so headroom is the only item you see, and launches. Safe to re-run any time.

Then pick your halves, both optional:

For Claude account meters: `uv tool install claude-swap==0.25.0`, log into an account in Claude Code, run `cswap add`. Repeat per account. Tested against claude-swap 0.25.0; cswap's JSON contract is additive and headroom parses defensively, so newer versions should keep working, and if meters vanish after an upgrade that's the fail-safe firing, not corruption. Downgrade or file an issue.

For OpenRouter spend: create or open a key at openrouter.ai/keys (give it a monthly cap), copy it, then:

```bash
pbpaste > ~/.openrouter_agent_key && chmod 600 ~/.openrouter_agent_key
```

Click 🔄 Refresh usage and the spend bar appears. The clipboard route keeps the key out of your shell history. (`OPENROUTER_API_KEY` in the environment also works, but menu bar apps don't inherit your shell profile, so the file is the reliable path.) If the key is rejected, the row says so with the HTTP status instead of pretending nothing is configured.

## What it won't do

It doesn't give you more quota or lower your bill. It shows you the numbers.

It doesn't alert. Nothing fires at a threshold yet; you have to look. A native notification at a percentage you choose is the planned next feature.

It doesn't act on what it shows. [openclaw-spillway](https://github.com/justin-rhee/openclaw-spillway) is the other half of this pair, moving an OpenClaw agent's work to a backup lane before a window runs out.

It can't see usage for providers it doesn't know. Anthropic windows come from cswap, OpenRouter spend from your key. Other providers are welcome as issues.

Only the file path works reliably for the OpenRouter key. SwiftBar launches outside your shell, so exports in `.zshrc` are invisible to it.

macOS only, by construction, since SwiftBar, the Keychain that cswap uses, and `defaults` exist nowhere else. The offline test suite also runs on Linux in CI as a code-health check, but the tool itself has one platform.

## How I tested it

16 offline tests, run them with `python3 -m unittest discover -s tests`. Unit tests pin the render boundaries. Threshold colors flip exactly at 60 and 80, bars clamp at both ends, the title falls back in the documented order, junk data parses to "no data" and never to a number. End-to-end tests run the script exactly as SwiftBar does, in a hermetic environment where no real key file or account store can leak in, and assert on the rendered rows for each state: accounts present, OpenRouter only, nothing configured, rejected key.

One test exists only to be attacked, planting an account alias that carries SwiftBar parameter syntax (`| bash=...`) and asserting the row renders as inert text. Every dynamic string that reaches a menu row is sanitized for exactly that reason.

The load-bearing mutation flips the hot-threshold comparison from `>=` to `>` in the script, and exactly one test goes red, the one named for the color promise. I ran that mutation and its revert as part of this release.

The account-parsing tests were written against claude-swap's actual JSON emitter source, not its docs: per-model rows arrive as a list of windows carrying `name`, and that's what the tests pin.

Live verification is one machine so far, my own, running real cswap against a real account with real SwiftBar, every day.

## License

MIT. See [LICENSE](LICENSE). No warranty. Security notes and how to report a problem: [SECURITY.md](SECURITY.md).

Design decisions and what changed while building it: [docs/ADR.md](docs/ADR.md).

---

This little tool is one of a handful I pulled out of my own day-to-day agent setup. I use them all myself, so when something breaks I usually notice fast. But if you run into any issues, or anything that looks off, open an issue. I read every one. More tools on my [GitHub profile](https://github.com/justin-rhee).
