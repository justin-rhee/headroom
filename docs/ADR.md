# Architecture Decision Records (ADRs)

Why a menu bar renderer sanitizes its input, and why this tool doesn't manage your accounts.

## A menu bar item is a place where hostile input can reach a shell

SwiftBar builds each menu row from a line of text, and everything after a `|` on that line is a parameter. One of those parameters is `bash=`, which names a command to run when the row is clicked. That means any string this script prints into a row is, structurally, a chance to add parameters that were never intended.

Most of what gets printed is mine. Account aliases are not: they're whatever a user typed when they ran `cswap add`, and a name is a free-text field that reaches the renderer exactly as it was typed. So every dynamic string reaching a row gets sanitized before it's printed, and one test plants the alias `evil | bash=/bin/rm param1=-rf` and asserts the row renders as inert text. The test exists to be attacked rather than to confirm something already believed, which is why it names a real destructive command instead of a placeholder.

## The parser is pinned to what cswap actually emits, not to what its docs say

The account meters come from `cswap list --json`, and the first version of the parser was written from the documented shape. That shape was close enough to work and wrong in a way that would have surfaced later: per-model rows arrive as a list of windows each carrying `name`, which the docs describe loosely enough to read several ways.

The tests are now written against cswap's actual JSON emitter source, so what they pin is what the program produces. It also changes what an upgrade does. The parse is deliberately defensive and additive fields are ignored, so a newer cswap should keep working, and if the meters do vanish after an upgrade that's the fail-safe firing rather than data being mangled. The README says to downgrade or open an issue, because a quiet wrong number is worse than a visible missing one.

## Nothing here is ever a guess

Anything unreadable renders as "no data". Not zero, not a stale value from the last successful read, not an estimate. A meter is only useful if the number on it is real, and a menu bar is the worst possible surface for a number you can't trust, because it's glanced at rather than read and there's no room for a caveat next to it.

That rule is the same one the sibling tool follows for a different reason. [openclaw-spillway](https://github.com/justin-rhee/openclaw-spillway) acts on usage numbers and refuses to act on ones it isn't sure about; this one displays them and refuses to display ones it isn't sure about. The tools came out of the same problem and landed on the same answer independently.

## The OpenRouter key lives in a file because the environment doesn't reach a menu bar app

The obvious place for an API key is an environment variable, and `OPENROUTER_API_KEY` does work if it's genuinely in the environment. It usually isn't. macOS launches menu bar apps outside a login shell, so an export in `.zshrc` is invisible to SwiftBar and therefore to this script, which produces the confusing version of broken: the key is set, the terminal proves it, and the meter still says nothing is configured.

So the documented path is a mode 600 file, written with `pbpaste` so the key never lands in shell history. The environment variable still works and stays supported for anyone whose setup does propagate it. A rejected key reports the HTTP status on the row rather than falling back to the not-configured message, because those two states look identical from the outside and only one of them is worth acting on.

## Account handling belongs to cswap, and duplicating it would have been the worse tool

Switching Claude accounts means touching credential storage, and this script does none of that. It runs `cswap list --json` as a subprocess, renders the answer, and shells out to cswap for the switch. The Keychain access, the token handling, and the usage polling all stay in the tool that already does them.

The cost is a dependency and a version pin, and the tests carry that risk explicitly. What it buys is that a bug in this script cannot corrupt an account store, because it never opens one, and that the polling stays inside the budget cswap already respects rather than adding a second uncoordinated poller against the same API. A display tool that also managed credentials would be a larger and much more dangerous piece of software than the problem called for.
