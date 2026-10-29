---
name: repo-watch
description: Weekly check of the public GitHub repos the owner told the assistant to watch, and report what changed in plain words. Use when the owner says "repos", "watch" a repo or asks for the weekly check, and at session start when `due` says a week has passed.
---

# Repo Watch

The owner's words: "keep a watch on them for sure" about one set of apps, and later "do a weekly check up on all repos
that I said to watch." For another repo he said "just watch", personal use only, never set it up.

> The watch tool and its watchlist are not part of this repo. This page is the routine.

Only repos the owner explicitly said to watch are on the list (a JSON watchlist, each entry with the memory id of his
words). A repo he only said to "keep on file" is not on it. To add one, he has to say watch; then add an entry with his
words' memory id.

Tool: `repowatch.py`. Read only, public GitHub API, no token or login, never stores a credential. State is one small
JSON file. Unauthenticated GitHub allows 60 calls an hour and a full check uses about 41 (more if anything else on the
PC calls GitHub), so run it once an hour at most. If GitHub says rate limit, the repos it could not read are marked
pending, the tool prints the time the limit resets, and the next `check` after that reads only those and completes the
check. `due` stays "due" until a check completes.

## Steps

1. `python tools/repowatch/repowatch.py due` (exit 0 = a week or more has passed, or never checked). When the owner
   asks, skip this and run the check.
2. `python tools/repowatch/repowatch.py check` (takes about 5 minutes; it paces itself for GitHub's search limit, so
   run it in the background). Exit 0 ok, 4 = some repos not read.
3. Write the report in plain words:
   - per repo: what changed since last time (stars, open issues, new release, Windows file still there);
   - the owner's stated concerns, in his own terms: crash reports fixed (crash open/closed counts and titles), a
     security fix closed (security open/closed and titles), Windows builds stable (a release with a Windows file, crash
     items that mention Windows);
   - then the verdict he asked for: whether the apps are ready for the course that would use them.
   Keep it short for a message. A long report goes out as HTML then PDF.
4. Save the finding to memory (**memory** skill), then the main session sends the report (PDF with a short note).
5. Never install, download or run any of the watched apps. Watching only.

## Weekly, no scheduled task

The owner registers scheduled tasks himself. The weekly rhythm comes from the start-up step: `repowatch.py due`, and if
it says due, this skill. `status` shows the last check without the network.
