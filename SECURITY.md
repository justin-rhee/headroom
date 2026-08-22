# Security policy. headroom

## Posture

headroom is provided as-is, with NO WARRANTY (see LICENSE). It is a display
tool, but it touches two things with security weight, so the boundaries are
stated plainly.

What it reads: claude-swap's JSON output (by running `cswap list --json` as a
subprocess) and, if you configure one, an OpenRouter API key from
`OPENROUTER_API_KEY` or `~/.openrouter_agent_key`. What it transmits: the
OpenRouter key goes to `openrouter.ai` only, as the Authorization header of a
key-introspection request. Nothing else leaves your machine. There is no
telemetry, no analytics, and no other network call in the script.

What it never touches: your Claude account credentials. Those live inside
claude-swap and the macOS Keychain; headroom only reads cswap's printed
output, which does not contain tokens.

Menu injection is defended: every dynamic string that reaches a menu row
(aliases, emails, provider statuses) is sanitized so SwiftBar's `|` parameter
syntax cannot be smuggled in through account data. The test suite includes a
probe that plants a malicious alias and asserts it renders as inert text.

The structural limit to state plainly: SwiftBar runs this plugin with your
user's full permissions, as it does every plugin. headroom cannot protect you
from other SwiftBar plugins or from a tampered copy of itself; install from
source you trust and read the script, it is one file.

## Validation status

The offline suite has been RUN and passes on the release commit: unit tests
for every render boundary (threshold colors flip exactly at 60 and 80, bar
clamping, title fallbacks) and end-to-end renders of each state (accounts
present, OpenRouter-only, neither tool set up, rejected key), all driven by
stubs, plus the alias-injection probe. A load-bearing mutation (the hot
threshold comparison) turns the boundary test red. Live verification is one
machine so far: macOS on the author's Mac, real cswap, real SwiftBar.

## Reporting a vulnerability

Report privately via a GitHub security advisory on this repository (Security
tab, "Report a vulnerability"). Please do not open a public issue for a
suspected vulnerability. Give a reasonable window for a fix first.
