---
description: Sync the current working-tree wiki into the demo branch and push it, so a read-only preview site connected to Vercel (or any other static host) updates to the latest content
---

# /publish-demo

> Syncs the current working tree's `wiki/` content into the `demo` branch and pushes it to the remote. `demo` is the only branch in this repo that tracks wiki content as committed files (it's gitignored on `main`) — it exists so the wiki can be viewed another way besides `tools/view.sh`'s local preview: deployed to a static host (Vercel, Netlify, GitHub Pages, …) and opened from any browser, including an iPad.

## Trigger

Manual: whenever the user says something like "update the demo site", "publish the wiki", "push to demo", or similar intent.

## Inputs

No arguments needed.

## Outputs

- An updated local `demo` branch (a new commit produced by `tools/update_demo.sh`)
- Pushed to `origin/demo`
- If a static host with auto-deploy is connected (e.g. Vercel), it picks this up and rebuilds automatically

## Wiki Interaction

### Reads
- The current working tree's `wiki/*` (the content source for the new `demo` branch commit)

### Writes
- Nothing in the working tree — `tools/update_demo.sh` operates directly on the `demo` branch's git objects via plumbing commands; it never runs `git switch` and never touches the current checkout

## Workflow

### Step 1: Confirm the working tree is the version to publish

If the user just did something that changes the wiki (`/ingest`, `/init`, etc.), confirm that finished and the current `wiki/` directory is the version they want published. No manual commit is needed from the user — `wiki/` is already untracked on `main`, and `update_demo.sh` reads straight from disk.

### Step 2: Build the demo commit

```bash
bash tools/update_demo.sh
```

- If nothing changed since the last publish, the script prints `demo is already up to date.` and exits 0 — report this plainly to the user and skip Step 3.
- Otherwise it prints the new commit's short SHA.

### Step 3: Push

```bash
git push origin demo
```

### Step 4: Report

Tell the user:
- Whether there was an actual update (or "already up to date, nothing pushed")
- If pushed: the site will typically rebuild automatically within 1-2 minutes; if they haven't connected Vercel/another static host yet, remind them that one-time setup is still needed

## Constraints

- **Never `git switch demo` or `git checkout demo`**: wiki content is gitignored on `main` and tracked on `demo`, so switching branches makes git delete the current working tree's wiki files. This skill only ever uses `tools/update_demo.sh` (a plumbing implementation) and `git push origin demo` — no checkout, ever.
- **Never edits `wiki/` content itself**: this is a pure publish step, not an editing step — content changes belong to `/ingest`, `/edit`, and other skills.
- **`demo` is updated only by this skill (or the user running `tools/update_demo.sh` manually)**: no other skill should call it in passing.

## Error Handling

- **`tools/update_demo.sh` errors** (e.g. not run from the repo root, `main` branch missing): show the error to the user verbatim; do not retry or guess a fix.
- **`git push origin demo` fails** (network, permissions): report the error; never paper over it with `--force` or similar.
- **`demo` doesn't exist yet on `origin`** (first-ever publish): `git push origin demo` creates it automatically — this is normal, not an error.

## Dependencies

### Tools (via Bash)
- `bash tools/update_demo.sh ["commit message"]` — builds/updates the local `demo` branch (plumbing, never changes the checkout)
- `git push origin demo`

### Calls no other skill, touches no files outside the wiki, needs no API key
