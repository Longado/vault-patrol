#!/bin/zsh
# Scene 1 — the pain: two notes that contradict each other, nothing warns you.
cd ~/Desktop/Workspace/01_项目/vault-patrol-demo
clear; sleep 2
print -P "%F{245}\$ find . -name '*.md' | sort%f"; sleep 1
find . -name "*.md" -not -path "./.git/*" | sort; sleep 4
print ""; print -P "%F{245}\$ cat tools/stack.md%f"; sleep 1
grep --color=always -n -i "memvid" tools/stack.md; sleep 6
print ""; print -P "%F{245}\$ cat notes/changelog.md%f"; sleep 1
grep --color=always -n -i "memvid" notes/changelog.md; sleep 8
print ""; print -P "%F{196}   two months apart. nothing warned me.%f"; sleep 8
