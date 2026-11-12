# How to use this kit

1. Unzip into the root of your project repo, keeping the folder structure. The `.claude` folder is hidden on most systems.
2. Open docs/SPEC.md and fill in the bracketed parts (account counts, investments).
3. Start Claude Code in the repo and type: /milestone start M1

## What each file does
- CLAUDE.md: loaded at the start of every session. Holds the 12 rules that must never be broken.
- docs/SPEC.md: the full requirements. Pulled in by CLAUDE.md.
- docs/PROGRESS.md: which milestone is approved and what is left. Claude updates it.
- docs/DECISIONS.md: a running log of design choices, so they are not re-argued later.
- .claude/skills/spec-check: checks a new feature against the spec before coding.
- .claude/skills/milestone: plan, wait for approval, build, report, stop.
- .claude/skills/drift-review: audits the code for anything that broke the rules.

## Habits that keep it on track
- Commit these files to git so changes to the spec are visible.
- Start a fresh session per milestone instead of one very long one.
- If Claude seems to have drifted, type /drift-review.
