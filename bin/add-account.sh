#!/bin/bash
# Guided account add for the menubar's "+ Add account…" row.
echo "Registers the account Claude Code is CURRENTLY logged into."
echo "To add a different account: /login in Claude Code as that account first,"
echo "then run this again. (Re-adding the current account is a safe no-op.)"
echo
CSWAP="$(command -v cswap || echo "$HOME/.local/bin/cswap")"
"$CSWAP" add
echo
echo "Done. The menubar picks it up on its next refresh."
