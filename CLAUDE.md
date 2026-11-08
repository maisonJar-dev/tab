# CLAUDE.md

Instructions for AI agents (and humans) working in `tab`: a personal tracker and study helper.
This file is the single source of truth for how work is done here. Agent-specific files
(`AGENTS.md`, `.cursorrules`, etc.) should point here rather than duplicate it.

## Engineering principles

These are rules, not suggestions. When two conflict, the earlier one wins.

1. **YAGNI: don't build it until you need it.**
   No speculative abstractions, config options, plugin systems, or directories "for later".
   A feature is needed when a current task cannot be completed without it.

2. **Fail fast: explicit errors beat silent failures.**
   Validate inputs at boundaries and raise with a message that names the bad value and what was expected.
   Never swallow exceptions, return `None` to mean "something went wrong", or fall back to a default silently.

3. **Simple first: write the obvious solution, optimize only if needed.**
   "Needed" means a measured problem (profiled, timed, or a failing requirement), not a guess.

4. **DRY: extract patterns after the second duplication, not before.**
   The first copy is fine. The second copy is a signal. Extract on the third occurrence,
   or on the second if the copies must change together.

5. **Delete aggressively: less code, fewer bugs, working product.**
   Remove dead code, unused parameters, stale files, and commented-out blocks. Git remembers.

6. **Semantic naming: verbose, self-documenting names over brevity.**
   Applies to variables, parameters, functions, files, and API endpoints.
   Optimize for a reader (human or LLM) who has no other context.
   - `study_session_duration_minutes`, not `dur` or `t`
   - `GET /study-sessions/{study_session_id}/flashcards`, not `GET /s/{id}/fc`
   - Booleans read as questions: `is_session_active`, `has_completed_review`

7. **Tracer: every new major directory gets a `README.md`.**
   See [Directory READMEs](#directory-readmes) below.

## Directory READMEs

A "major directory" is any directory that holds a distinct concern (a package, service, app, or
top-level folder like `src/`, `tests/`, `scripts/`). Trivial leaf folders don't need one.

Each `README.md` is written for both a human onboarding to the code and an LLM loading it as context.
Keep it short and update it in the same commit that changes the directory's purpose or structure.
For top-level directories this is enforced by `.githooks/pre-commit` (one-time setup per clone: `git config core.hooksPath .githooks`).

Required sections:

```markdown
# <directory name>

## Purpose
One or two sentences: what problem this directory solves and why it exists.

## Contents
The files/subdirectories that matter, one line each.

## How it connects
What depends on this directory, and what this directory depends on.

## Conventions
Rules specific to this directory (only if any exist).
```

## Workflow for agents

- Read the nearest `README.md` before editing files in a directory.
- Keep changes scoped to the task. Don't refactor or "improve" unrelated code.
- When you add a dependency, a new top-level directory, or a new pattern, ask first.
- If the task reveals that one of these principles should change, propose the edit to this file instead of silently deviating.

## Git

- `main`: stable. `development`: integration branch.
- Branches are created, switched, and merged by the repo owner, not by agents.
- Commit only when asked.
