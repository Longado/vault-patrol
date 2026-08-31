#!/bin/zsh
# Scene 5b — same entry point, no cloud.
cd ~/Desktop/Workspace/01_项目/vault-patrol
source .venv/bin/activate
clear; sleep 2
print -P "%F{245}\$ python -m patrol run ../vault-patrol-demo --no-model%f"; sleep 2
python -m patrol run ../vault-patrol-demo --no-model 2>&1 | tail -18; sleep 14
