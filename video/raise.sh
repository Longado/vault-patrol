#!/bin/zsh
# raise.sh <terminal|chrome> <seconds> — keeps the target app frontmost during a take
TARGET=$1; SECS=$2; END=$(( $(date +%s) + SECS ))
APP="Google Chrome"; [ "$TARGET" = "terminal" ] && APP="Terminal"
while [ $(date +%s) -lt $END ]; do
  osascript -e "tell application \"$APP\" to activate" >/dev/null 2>&1
  sleep 1
done
