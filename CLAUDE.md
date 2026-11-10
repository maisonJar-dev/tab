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

### Branches

- `main`: the working version. Always runs and passes tests.
- `development`: where features are integrated. After every release it equals `main`.
- `feature/<short-kebab-name>`: one per feature, branched from `development`.

### Flow

```text
feature/x ──squash──▶ development ──rebase (fast-forward)──▶ main
                         ▲                                    │
                         └─────── reset to main's head ◀──────┘   then delete feature/x
```

1. **Branch** a feature off the latest `development`.
2. **Commit** on the feature branch as work goes (only when asked; see below).
3. **Squash-merge** the feature into `development` as one commit whose message summarises the
   feature's commits, grouped by area:
   `git switch development && git merge --squash feature/x && git commit`
4. **Rebase `main`** onto `development`: `git switch main && git rebase development`.
   `main` never gets its own commits, so this is a fast-forward and rewrites no history.
   Give the [merge summary](#reports) first, every time, then **wait for the owner to
   confirm** before rebasing.
5. **Update `development`** to the head of `main` (`git reset --hard main` on `development`),
   if they differ. After step 4 they normally already match.
6. **Delete the feature branch**, locally and on the remote if it was pushed.
7. **Push** `main` and `development` (only when asked).

### Checks before each step

Each check guards a step that is hard to undo. If one fails, stop and ask; don't work around it.

- Before squashing: the feature branch is committed and clean, `ruff check`, `ruff format --check`
  and `pytest` pass, and `development` is an ancestor of the feature (`git merge-base
  --is-ancestor development feature/x`).
- Before rebasing `main`: `main` has no commits that `development` lacks
  (`git rev-list --count development..main` is `0`), so the rebase is a pure fast-forward.
  Run `pytest` on `main` afterwards.
- Before deleting the feature branch: `git diff --quiet development feature/x` succeeds
  (identical files). A squash creates a new commit, so git reports the branch as unmerged and
  `git branch -d` refuses; `git branch -D` is expected, but only after this check passes.
- Before pushing: `main` and `development` are ahead of their remotes and not behind.
  Never force-push `main` or `development`.

### Reports

**Merge summary**: before every rebase of `main` (step 4), say what is about to reach `main`,
then stop and ask for confirmation. Rebase only after the owner says yes, even when they asked
for the whole release up front; if they say no, leave `main` as it is and ask what to change.

- The commits on `development` that `main` lacks (`git log --oneline main..development`).
- What they change, in plain words, grouped by area (features, fixes, settings, docs).
- Files changed (`git diff --stat main development`).
- Anything that needs care: changed settings or progress file formats, new dependencies,
  deleted files, behaviour that changes for existing users.
- Test and lint results on `development`.

**Release report**: after a release, a table with one row per step, skipped steps included
with the reason (so it's clear every step was considered):

```markdown
| Step | Check | Result |
|---|---|---|
| 3. Squash into `development` | clean tree, ruff and pytest pass, branched from `development` | `abc1234` |
| 4. Rebase `main` | 0 commits on `main` missing from `development` | fast-forward to `abc1234` |
| 5. Update `development` | already equal to `main` | no reset needed |
| ... | ... | ... |
```

Then one line each: the commit `main`, `development` and `origin` are on; the current branch;
and the command to recover the deleted feature branch (`git branch feature/x <hash>`).

### Rules for agents

- Run branch operations (create, switch, squash, rebase, reset, delete, push) only when the
  owner asks for them. Report as in [Reports](#reports).
- Commit only when asked. Never delete or rewrite `main` or `development`.
- If a deleted feature branch is needed again, recreate it from its last commit
  (`git branch feature/x <hash>`); git keeps unreferenced commits for about 30 days.
