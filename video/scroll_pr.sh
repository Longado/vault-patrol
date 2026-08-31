#!/bin/zsh
sleep 10
for i in 1 2 3 4; do
  osascript -e 'tell application "System Events" to key code 121' >/dev/null 2>&1
  sleep 7
done
