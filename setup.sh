#!/bin/bash
# One-step setup for headroom: checks prerequisites, installs SwiftBar if
# missing, points it at the plugin/ subfolder (ONLY the script lives there;
# SwiftBar runs every visible file in its plugin folder), hides the SwiftBar
# host icon, and launches. Safe to re-run.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ "$(uname)" != "Darwin" ]; then
  echo "headroom is macOS only (SwiftBar is a macOS menu bar host)."; exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install the Apple Command Line Tools first:"
  echo "  xcode-select --install"
  exit 1
fi
if ! [ -d /Applications/SwiftBar.app ]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "SwiftBar isn't installed and Homebrew wasn't found to install it."
    echo "Either install Homebrew (https://brew.sh) and re-run this, or"
    echo "download SwiftBar directly from https://swiftbar.app and re-run."
    exit 1
  fi
  echo "Installing SwiftBar (brew cask)..."
  brew install --cask swiftbar || { echo "FAILED: brew install --cask swiftbar"; exit 1; }
fi

osascript -e 'quit app "SwiftBar"' 2>/dev/null
sleep 1
defaults write com.ameba.SwiftBar PluginDirectory -string "$HERE/plugin"
defaults write com.ameba.SwiftBar HideSwiftBarIcon -bool true
defaults write com.ameba.SwiftBar MakePluginExecutable -bool true
chmod +x "$HERE/plugin/headroom.5m.py" "$HERE"/bin/*.sh 2>/dev/null
open -a SwiftBar
echo "OK: SwiftBar running. Plugin folder: $HERE/plugin · host icon hidden"

if ! command -v cswap >/dev/null 2>&1 && ! [ -x "$HOME/.local/bin/cswap" ]; then
  echo "OPTIONAL, for Claude account meters: uv tool install claude-swap==0.25.0"
  echo "  then log into each Claude account in Claude Code and run: cswap add"
fi
echo "OPTIONAL, for OpenRouter spend: see the OpenRouter section in README.md"
