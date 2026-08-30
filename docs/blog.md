# I built an agent that only deletes: vault-patrol

Every note-taking tool I have used is built to help me add. None of them help me remove.
After two years of a markdown "second brain", a meaningful share of my files are lying to me.
One note says "use the Memvid MCP server for semantic search"; a changelog three folders away
says Memvid was removed in July. A starter template pins a model id from 2024 and says
"always use this model". None of this is a broken link, so no linter catches it. It is rot:
text that will mislead a future reader into acting on something no longer true.

vault-patrol is an agent for exactly that. On every push to a vault repo it clones the
repo, audits it, and opens one pull request that only takes things away. It never creates a
note or a task.

## Three rules that shaped the code

**One model judgment; code owns every loop.** The agent makes exactly one call to Gemini per
patrol. Retries, deduplication, the cap on findings, the decision whether a pull request is
warranted at all: ordinary Python. This is not frugality, it is failure math — three chained
calls at 95% reliability leave you at 86%, ten leave you at 60%. Anything a regex can answer
never reaches the model: broken index links, orphaned files and dangling `[[wikilinks]]` are
found by deterministic code. The model only gets the questions that need judgment. Is this
instruction stale, do these two notes contradict each other, is this claim falsified by a log
elsewhere.

The retry policy is worth a sentence, because I got it wrong first. Retrying "on exception"
means a bad key fails three times instead of once. The rule now: retry on 429, 5xx and
connection errors; re-raise immediately on a validation error or any other 4xx, because
those will fail identically on the next attempt.

**Every citation is verified against the file.** The model's output schema requires an
`evidence_quote` for each finding, and `reasoning` is the first field in the schema, so the
model writes its argument before committing to a verdict. Then code checks that the quote is
a verbatim substring of the file it was attributed to. If it is not, the finding is dropped
and counted. The report prints that count. A hallucinated citation cannot reach the pull
request; it can only show up as a number saying the model tried.

**Subtraction only, enforced by the type.** The action field is an enum: `delete_line`,
`mark_historical`, `merge_into`, `add_arbitration_line`, `needs_human`. There is no "create
note" and no "add task", so the agent cannot answer a messy vault by generating more vault.
Exactly one action is applied automatically — deleting an index line that points at a file
which does not exist. Everything else is a proposal for a human to accept or ignore.

## Numbers

On the demo vault, a patrol produces 4 mechanical findings and 6 semantic findings with 0
dropped, covering all five rot categories. Getting the fifth took a prompt edit rather than a
code change: a hard-coded model id with an obviously old date is rot on its own, and the
model had been waiting for a second note to contradict it. The prompt is a versioned file,
not a string in the source, so that edit is a reviewable diff.

The more instructive number came from the mechanical layer on my real vault of 208 notes. The
orphan check originally asked "does the index link to this file" and reported 76 orphans, most
of them wrong: notes are legitimately reached through other notes, or through a folder bullet
in the index. Making reachability vault-wide brought it to 46. A check that cries wolf on a
third of your files gets ignored, which is worse than not shipping it.

## The stack

FastAPI on Cloud Run, deployed from source. The GitHub webhook is HMAC-verified, returns 202
immediately and runs the patrol in the background, which is why the service needs
`--no-cpu-throttling`: otherwise the CPU is withdrawn the moment the response is sent and the
patrol freezes. The model is Gemini 3.5 Flash through Vertex AI with the Google GenAI SDK,
authenticated as the Cloud Run service account, with the pydantic report model passed directly
as the response schema. Secrets live in Secret Manager. There is no database: re-running
updates the existing pull request instead of opening a second one, so idempotency falls out of
the GitHub API.

One deployment detail is worth writing down: on Cloud Run, `GET /healthz` is answered by
Google's frontend and never reaches your container. Registered routes like `/webhook` work and
unregistered paths return your app's own 404, but `/healthz` returns Google's HTML error page.
The service answers on `/health` too.

Built for the All Things Agentic Hackathon.
