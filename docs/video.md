# Demo video script (target 3:40, hard cap 4:00)

Record as a single unedited screen capture for the demo section (rule: "unedited, live execution").

| Time | Screen | Say |
|---|---|---|
| 0:00–0:35 | Obsidian/vault folder scrolling; then `tools/stack.md` ("use the Memvid MCP server") beside `notes/changelog.md` ("Memvid removed 2026-07-03") | "This is my second brain. This note tells me to use a tool. This note says I removed it two months ago. Nothing warned me. Every note tool helps you add; none helps you delete. I had a manual checklist for this — it never ran, because I had to run it." |
| 0:35–1:05 | `docs/architecture.md` diagram | "vault-patrol is an event-driven agent. A push hits Cloud Run. Code does the mechanical checks. Gemini 3.5 gets one structured call for five kinds of semantic rot. Code verifies every quote it returns against the file. One PR. Subtraction only." |
| 1:05–1:20 | Google Cloud Console → Cloud Run → `vault-patrol` service page, URL visible | "It's running here on Cloud Run, scaled to zero until a push arrives." |
| 1:20–3:00 | Terminal: `cd vault-patrol-demo && git push` → Cloud Run logs tab refreshing → GitHub PR list → PR appears → open PR, show `MEMORY.md` diff (dead line deleted) and `PATROL_REPORT.md` table → Firestore console `patrol_runs` doc | "I push a commit to the vault. The webhook fires. Logs: clone, mechanical, one Gemini call, adjudication. And here's the PR. The dead index link is already deleted. The stale reference to Memvid: flagged with the exact quote. The pinned old model id. Three notes about commit format — merge proposal. Two notes that contradict each other on testing. And the note that says 'used daily' next to a log that says once in 17 days. The last line: how many model findings the code threw out because the quote wasn't in the file." |
| 3:00–3:40 | Back to diagram; then terminal `python -m patrol run ~/memory --no-model` | "Three design rules. The model makes one judgment; code owns every loop. Every citation is verified before a human sees it. And the action set is subtraction only — the agent cannot invent work for me. The same entry point runs locally with no cloud, so this outlives the hackathon." |

Checklist before upload: Cloud Run console visible ≥5s · .run.app URL visible · PR opened live on camera · under 4:00 · public on YouTube.
