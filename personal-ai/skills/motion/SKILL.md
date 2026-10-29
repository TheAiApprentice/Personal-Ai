---
name: motion
description: Rendered animation for every lesson and YouTube video made with the lesson-video skill. Each slide animates in time with the narration (bullets appear as they're said, code types on, drawings draw in, highlights sweep, soft transitions) through a motion script that the lesson builder runs automatically when it assembles a video. Use it whenever a lesson video is built, previewed or its animation needs changing, and when the owner asks about "motion", "animation" or "the rendering" of the lessons.
---

# Motion (animated lesson videos)

The owner's order: "build a motion skill that does the rendering animation for the lessons. Build it best you can."
Voice stays the free TTS clone; motion only changes the picture.

Motion is part of the one video format (lesson-video skill). It does not change the slides, the look, the narrator or
the script; the same slide is drawn on screen piece by piece, in time with the voice, and ends exactly like the still
slide.

> The builder and motion scripts named here belong to the channel's own video tools and are not part of this repo.
> This page records what moves, when, and the look rules.

## How it runs

- Full build: run the lesson builder for the lesson id (or its video stage). Motion is ON by default; a `--no-motion`
  flag, or `"motion": false` in the lesson's `meta`, gives the old still-slide video.
- Preview without spending anything (needs slides, audio and the timeline from an earlier build): run the motion
  script with a slide range. It writes a preview video and a share-size preview; a frames option also saves stills of
  those slides at 0.3 s, 1.2 s and near the end so the look can be checked.
- Always look at a few stills (start, middle, end of a slide) before sending a video.

## What moves (the plan comes from the narration)

| Slide | Motion |
|---|---|
| title | the teacher rises in, logo pops, kicker, rule draws, course, lesson number, title, meta in turn |
| section | the teacher's medallion slides in from his side, kicker/big/lead rise, the speech bubble pops when the narrator reaches the quote |
| quill | the teacher rises in, bubble or big quote appears, signature last |
| bullets, table rows, cards, mistakes, qa, checks, try | each item appears just before the narrator first says one of its key words; misses are spread evenly; the first item starts by 0.8 s |
| code | lines type on (left-to-right wipe), output panel slides up when the narrator talks about the output, notes last |
| illus / drawings | the plate pops, then every stroke draws itself in, fills fade in after |
| step sequences (same heading, `step`/`hl` moving on) | nothing re-enters; only the new highlight sweeps in, with a short 0.2 s cut |
| build (build round, split layout) | the chat is timed to the beats of the narration (see below); the work box on the left plays ONE continuous recording of the open tool from the first beat to the end of the slide, its last frame holds |
| bullets with `inset` | the framed recording panel fades in after the second item (0.6 s), then its clip plays at `rate`; its last frame holds |
| film | the film's first frame shows during the teacher's intro line, the film plays full screen right after it (no fade, nothing said over it); the slide lasts as long as the film. A `freeze` film slide holds the film's last frame for the closing note |
| end (the shared end screen, last slide of every video) | the teacher rises in, logo pops, "Thank you for watching", subscribe / next video line, tagline, the mascot waves; text comes from one shared end-screen file |
| film `freeze` slide | holds one bright frame of the film (`"still_at": seconds`), not the faded-out last frame |
| progress bar | fills from the last slide's place to this one |

### Build rounds (chat panel)

The plan turns the beats of one `build` slide into times, from the real beat starts in the audio manifest (start and
length of each voiced beat; before there is a voice they are estimated from word counts):

- The teacher's message (`q`) starts typing 0.4 s into its beat, letter by letter at 12.5 characters a second (never
  longer than the beat allows) and slides in when sent; a `card` slides in 0.5 s into its beat, tucked under the
  message above it.
- An AI reply (`ai`): typing dots 0.35 s into its beat, the reply 1.3 s later (`dots_s` sets that wait); the dots are
  fully faded 0.05 s before the reply slides in, so there is never a second avatar or label on screen; no two chat
  changes closer than 0.6 s; older bubbles scroll up, and the thread keeps 30 px of air above the input box.
- `clip_from` on the first beat: the recording is shown only from that second of the file on (the slate stays until
  then; no dead head).
- The round's clip (`clip` on the first beat) starts 0.5 s into that beat and fades in over 8 frames; a clip on a later
  beat starts 0.1 s after that beat's AI reply. `clip_start` and `clip_rate` pick the part and the speed.
- Sound: a recording with sound plays at full level in the `listen` hold after a beat and 28 % under the voice
  elsewhere; its loudness is matched to the voice using the sound itself, not the silence before it.

Bubbles use the channel's colours; ease-out slides of 0.5 s, no bounce.

Transitions: a soft 0.45 s crossfade between slides, a 0.6 s dip through the dark background into title, section,
quill and end slides, and a 0.2 s cut between steps of one sequence.

Per-slide controls in the lesson JSON (rarely needed):

- `"at": [1.0, 3.5, 6.2]`: seconds after the narration starts when each item appears.
- `"motion": "none"`: no animation on that slide.

## Look rules (keep the videos calm and readable)

1. Nothing bounces, spins or flashes. Ease-out moves only, 0.3 s or longer.
2. A thing appears when the narrator gets to it, not all at once and not long before.
3. At most a few things move at the same moment.
4. The frame (top bar, footer, logo) never moves; only the progress bar.
5. The last frame of every slide must equal the still slide (check with the stills option).
6. No camera drift or zoom on text (it blurs). Moving pictures appear only as real recordings inside the work box (the
   slide never adds AI-made motion of its own); the recorders' own camera glides (zooming to a node) are part of the
   real recording.
7. Text stays sharp: animate opacity, position and clip, never blur or scale text below 0.94.

## How it works (for fixing it)

The motion script adds a small runtime to each slide's HTML that builds Web Animations from a timing plan and pauses
them. Python seeks the page to each frame's exact time and screenshots it (headless Edge through Playwright), but only
for frames where something moves; still stretches repeat the last frame. Frames stream as JPEG straight into ffmpeg. A
16-minute lesson renders in a few minutes.

## Rules for helpers

Never close programs by name or image; stop only processes you started, by PID. No installs. Rendering costs
nothing; voicing is the free TTS clone described in the lesson-video skill (GPU only with a grant or the owner's
written override). Delete anything only with the wipe skill (Recycle Bin).

## Build round clips (how the left side is made)

The recordings are made by two recorders (one for a node-based tool page, one for a terminal), one continuous session
per round, and timed to the narration by a per-video script. That script reads the same beat times the motion plan
uses and sets how long each stretch of the recording lasts (typing, run, result, hold, sound); the recording itself is
untouched. Rebuild the clips whenever a beat's narration changes length, then re-check the stills.
