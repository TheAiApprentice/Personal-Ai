---
name: guild-short
description: Make a channel Short the one approved way - a vertical 1080x1920 Short in the lesson-video look with the teacher's art grounded on the left, the lantern mascot with its real website flame, big text cards, word-by-word captions, the locked teacher voice, a soft music bed and a subscribe end card. Use whenever the owner asks for a Short, this week's Short, an invite Short or a new Short in that style.
---

# Short (approved format)

The owner approved this format ("I like them") for a set of invite Shorts. Every Short is made this way. An earlier
3D walk-up version (Blender, then a MetaHuman render) was scrapped; never go back to it unless the owner asks.

> The renderer, the voice job scripts and the art files named below belong to the channel's own build folder and are
> not part of this repo. This page records the format and the quality gate.

## Hard rules from the owner

- No fake walking, sliding cut-outs, wobbling or floating characters, and no mismatched background art ("slop").
  Characters stay grounded with gentle, believable motion only.
- Check every Short as **motion**, not stills, before the owner sees it. Nothing below the bar reaches him.
- The mascot only emotes, never talks. Its flame is the website's real flame: small on the wick, big inside the glass
  behind the face.
- GPUs only under a gpu-time grant or the owner's own go in chat.

## Steps

1. **Lines.** Write or take the week's lines for the teacher into the spec file, about 20-30 s of speech, ending with
   "Subscribe, and we'll see you inside." Don't send lines to the owner for review unless he asks.
2. **Voice.** Get GPU time with the **gpu-time** skill. Then:
   - list the voice jobs
   - run the voice repeat test on the voice GPU, then the repeat check. Stop if it says the voice drifted.
   - voice the jobs on that GPU with the locked voice preset. Log the PIDs, stop them by PID, release.
3. **Build.** For each Short: align the words to the audio, then build with the timing from the voice into an `.mp4`.
4. **Quality gate.** Run the QA script on the `.mp4` and look at the 4-frames-per-second sheets yourself.
   - Text: no overflow and no overlaps.
   - Characters: the teacher steady, and the flame playing in the glass and on the wick.
   - Captions: in sync with the voice.
   - Sound: -14 LUFS and no silences.
   Fix anything below the bar.
5. **Deliver.** Make 720-wide previews under 10 MB for chat, then hand them to the main session. The owner does the
   posting.
6. **Upload pack.** Every Short ships with an `upload.txt`: 3 title options (one RECOMMENDED, each ending #Shorts), a
   short description (what the teacher says, the next lesson day, the free starter skills link, the subscribe link,
   hashtags), tags and settings (Education, not made for kids, altered-content note for the AI voice). The owner asked
   for this after one batch went out without titles and descriptions.

## Pieces

- A vertical lesson-style renderer (a Python script and an HTML page).
- The teacher's art with the shoulder lantern painted out, so the mascot isn't shown twice.
- The mascot layers are ported from the site's own scripts and styles, and the flame frames come from the site's
  assets.
- The locked teacher voice is stored once and never edited.
