# Devpost submission text

**Project name:** vault-patrol
**Tagline:** Your second brain rots. This agent finds the rot and opens a subtraction-only PR.
**Track:** The Taskmaster

## Inspiration
I keep a markdown memory vault that my coding agent loads every session. Over months it accumulated instructions pointing at tools I had retired, boilerplate pinning old model ids, three notes saying the same thing, and one note claiming a tool was "used daily" next to a log showing one use in 17 days. Every note tool helps you add. None helps you delete. I had a manual checklist for this; it never ran because I had to run it.

## What it does
On every push to a vault repo, vault-patrol clones the commit, runs deterministic checks (broken index links, orphans, dangling wikilinks), then asks Gemini 3.5 once — with a JSON schema — for five kinds of semantic rot: stale active references, pinned old versions, overlap clusters, hard conflicts, falsified claims. Code verifies that every evidence quote exists verbatim in the file, drops anything that does not, and opens one PR that deletes dead index lines and lists the rest with a proposed subtraction. It never creates notes or tasks.

## How we built it
Python 3.12, FastAPI on Cloud Run (webhook returns 202, patrol runs in background with CPU always allocated). Gemini 3.5 through the Google GenAI SDK with `response_schema` = a pydantic model whose first field is `reasoning`. Firestore stores each run's anchor sha, model version and prompt version so the same commit is never patrolled twice and drift is traceable. GitHub REST for branch + PR. The prompt is a versioned file in `prompts/`, not a string in code.

## Challenges
Keeping the model honest: an audit that cites text which is not in the file is worse than no audit. The fix was structural, not prompt-based — the schema requires a verbatim quote and code rejects any finding whose quote is not a substring. The PR reports the rejection count.

## What we learned
The agent got more useful the less it was allowed to do. Restricting actions to a subtraction-only enum removed the whole class of "agent invents work for me" failures.

## What's next
Run it on the real vault locally through the same entry point (`python -m patrol run <dir>`), and let the retired-tool findings drive the next cleanup.

**Built with:** Gemini 3.5, Google GenAI SDK, Cloud Run, Firestore, Secret Manager, FastAPI, Python, GitHub API
