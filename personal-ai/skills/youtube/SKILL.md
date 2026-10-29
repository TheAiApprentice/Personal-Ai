---
name: youtube
description: Pull a YouTube video's info and transcript (and, when asked, the video itself and still frames) so the assistant can read and see it without the owner copying anything. Use whenever the owner sends a YouTube link (youtube.com, youtu.be, shorts) in chat and wants it watched, summarized, broken down or discussed, or says "/youtube", "watch this", "grab this video", "get the transcript".
---

# YouTube

The owner drops a link; you fetch everything yourself and then work from it. Never ask him to paste a transcript.

## Run it

From the repo root:

`python skills/youtube/scripts/yt_fetch.py "<link>"`

Add `--frames N` (say 6 to 12) when the visuals matter: thumbnails, editing, on-screen text, b-roll, how something looks.
That also downloads the video at 720p or lower. Add only `--video` if he wants the file itself. `--lang es` etc. for
another caption language. A search works too: `"ytsearch1:<words>"`.

Output goes to `data/youtube/<video_id>/` (inside the repo):

- `meta.json`: title, channel, upload date, duration, views, likes, description, chapters, tags
- `transcript.txt`: timestamped lines (auto-caption repeats already removed)
- `transcript_plain.txt`: the same words as one block
- `thumbnail.*`, and with the flags `video.mp4` and `frames/frame_NN_M-SS.jpg`

## Then

1. Read `meta.json` and `transcript.txt`. With frames, read the jpgs too; you can see them.
2. Do what he asked (summary, breakdown, hook analysis, notes). Quote video times as "2m 15s" (or "1h 4m 10s") so he can
   jump to them. Not "2:15": a chat bot's wording gate can read that as a clock time and refuse the message.
3. No transcript (captions off, or YouTube rate-limited the captions with HTTP 429): say so plainly, work from the
   description and chapters, and offer `--frames` so you can look at it. Try the captions once more a minute later if the
   problem was a 429.
4. Long write-ups go back to him as a PDF, same as any long answer.

## Notes

- Uses the `yt_dlp` Python module and ffmpeg. If `yt_dlp` starts failing on every video, YouTube changed something and it
  needs updating; ask the owner before running any install.
- Videos are downloaded only with `--video` or `--frames`. Clear old folders in `data/youtube/` when he asks; they are not
  needed after the job.
- Private, members-only and age-gated videos fail without a signed-in session. Say so; do not try to sign in.
