# How to use this kit

1. Unzip into the root of your project repo, keeping the folder structure.
2. Open docs/SPEC.md and fill in the bracketed parts (account counts, investments).
3. Start Codex in the repo and begin with `/milestone start M1`.

## What each file does
- AGENTS.md: loaded at the start of every Codex session. Holds the project rules that must never be broken.
- docs/SPEC.md: the full requirements. Pulled in by AGENTS.md.
- docs/PROGRESS.md: which milestone is approved and what is left. Codex updates it.
- docs/DECISIONS.md: a running log of design choices, so they are not re-argued later.
- Project workflows: check a new feature against the spec, record milestone approval, and review drift before closing it.

## Habits that keep it on track
- Commit these files to git so changes to the spec are visible.
- Start a fresh session per milestone instead of one very long one.
- If Claude seems to have drifted, type /drift-review.
