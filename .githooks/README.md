# .githooks

## Purpose
Version-controlled git hooks that enforce the repo's principles (see `CLAUDE.md`) for humans and AI agents alike.
Hooks in `.git/hooks/` aren't tracked by git, so they live here instead.

## Contents
- `pre-commit`: blocks a commit if any top-level directory (dot-directories excepted) is missing a `README.md` (the Tracer rule).

## How it connects
Git runs these only after a one-time setup per clone:

```sh
git config core.hooksPath .githooks
```

## Conventions
- Each hook fails fast: non-zero exit plus a message that names what's wrong and how to fix it.
- Name variables descriptively; these scripts get read by LLMs too.
