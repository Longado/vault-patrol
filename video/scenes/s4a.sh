#!/bin/zsh
# Scene 4a — plant a real contradiction, commit, push.
cd ~/Desktop/Workspace/01_项目/vault-patrol-demo
clear; sleep 2
print -P "%F{245}\$ grep llm-wiki notes/changelog.md%f"; sleep 1
grep --color=always -n "llm-wiki" notes/changelog.md; sleep 4
print ""; print -P "%F{245}\$ echo '... run the llm-wiki daemon; it is the search backend.' >> tools/stack.md%f"; sleep 1
printf '\nFor nightly full-text indexing of every note, run the llm-wiki daemon; it is the search backend.\n' >> tools/stack.md
tail -2 tools/stack.md; sleep 4
print ""; print -P "%F{245}\$ git commit -am 'notes: point the stack at the llm-wiki daemon' && git push%f"; sleep 1
git commit -q -am "notes: point the stack at the llm-wiki daemon" && git push 2>&1 | tail -4
sleep 6
