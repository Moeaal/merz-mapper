# Instructions for Claude (Merz Mapper, EEE3094)

1. Start from `docs/MERZ_MAPPER_STATE.md`. Open other `docs/*` files only when the task needs them.
2. Code in this repo is the source of truth. Search for the specific file (grep/glob); never read the whole repo for a small question.
3. Never call a feature IMPLEMENTED or TESTED unless the code exists here / a logbook entry records the result.
4. Do not change working code, delete files, or alter hardware/architecture decisions without the student's approval. Propose changes in `docs/decisions.md` as PROPOSED.
5. After significant work: update `MERZ_MAPPER_STATE.md` (and the relevant memory file) in a few lines. The repo copy is the master; the claude.ai project doc `claude/MERZ_MAPPER_STATE.md` is a mirror - update it too when you can, or say it needs syncing.
6. Robot = main contribution; website = demonstrator. UK English; submissions in third person with IEEE references.
7. Skills come from the student's claude.ai account (signed-in sessions show them as `anthropic-skills:<name>`): start with `merz-mapper-engineering-brain`, which routes to `merz-navigation-estimation`, `merz-perception-jetson` or `ros2-engineering-skills`. Do not copy these skills into `.claude/skills/`.
8. Before researching, check `docs/RESEARCH_INDEX.md`; add new verified sources there instead of searching again later.
