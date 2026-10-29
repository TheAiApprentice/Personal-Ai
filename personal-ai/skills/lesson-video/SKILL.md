---
name: lesson-video
description: Write and build every course and YouTube video of the channel the one fixed way. Slides first (about 15 min), then the teacher says "Now watch my screen as I show you" and the video turns into build rounds (the work on the left, an animated chat between the teacher and the AI on the right), then a skill file, the wrap and the finished film. Use whenever the owner asks for a video, a video script, a lesson video, a YouTube video, or "like the other videos". Never invent a new format.
---

# Lesson video (the one way every video is made)

The owner's order: every video is made the same way. Don't change the format, the narrator, the look or the tool
between videos; if a request seems to need something different, ask him first.

The format: "the 15 minutes is for the slide show parts, the rest of the video is the length it takes to showcase the
stuff ... a back and forth between the teacher and the AI on building stuff, the AI doing something, showing it, and
the teacher giving tweaks." And: "this has to be good, top tier high quality, no AI slop."

> The builder, recorder and motion scripts named below belong to the channel's own video tools and are not part of
> this repo. This page records the format, the rules and the checks.

## What a video is

1. **Lesson slides, about 15 min (13 to 16 allowed)**: title, the teacher's hook, "By the end", the parts (each with
   "If you love this part" and "If you'd rather not": tool, cost, where it runs, who owns it, the catch), "Where AI is
   still weak". An "If you love this part" slide can carry an `inset`: a short real recording of the hand-made way.
2. **The switch**: a `quill` slide where the teacher says "Now watch my screen as I show you." The next slide is the
   first build round.
3. **Build rounds**, one per part where AI does the work (`build` slide type, split layout: the work on the left about
   70 %, a narrow chat on the right). Each round: the teacher types his ask; a short "Good ask" card; the AI replies
   after typing dots and its REAL first result shows on the left; the teacher types a tweak; a "The tweak" card; the
   AI's second reply and the REAL fixed result. He talks over all of it like normal teaching and the picture follows
   his words.
4. **Skill file**: the viewer's basic `starter/SKILL.md`, shown on screen straight from the file (`code_from`), so the
   two can never differ.
5. **Wrap**: try, mistakes, quick check, "Done when", a `quill` slide (free starter in the description), then the
   finished work (`film` slide, plays the whole film), the closing note, and the shared end screen (added
   automatically, see below).
- Build rounds are not counted in the 15 minutes; their length is whatever the real work takes.
- The teacher (an old archivist with a ledger) guides; the lantern mascot is the mascot; the narrator says
  "apprentice"/"you". The chat labels the AI plainly as "AI". Never the owner's personal name, folders or Windows user
  name on screen, in captions or in the JSON.

## The one source file

One JSON file per lesson; copy the shape of the newest finished one. Slide types:
`title section bullets table cards illus code try mistakes qa checks end quill` plus

- `build`: `{"type": "build", "round": n, "of": 8, "h", "tool", "cap", "beats": [...]}`. A beat is `{"say", and one of
  "q" (the teacher's chat message, typed letter by letter as he says it), "card": {"k", "t"}, "ai" (typing dots, then
  the AI's reply)}`; `"clip"` on the FIRST beat names the recording of the whole round (it plays from that beat to the
  end of the slide); `"listen": seconds` after a beat leaves silence so a result with sound is heard (the clip's own
  sound is full level in that hold and ducked under his voice elsewhere). `say` of the slide = the beats joined.
- `bullets` with `"inset": {"clip", "rate", "cap"}`: framed short recording on the right of the list.
- `film`: the finished film plays CLEAN, nothing said over it. Two slides: `{"type": "film", "clip", "cap", "say": <one
  short intro line>}` (the film's first frame is on screen during the line, the film starts 0.4 s after it ends, its
  own sound at full level; the slide lasts as long as the film file; the start comes from the voiced line and is stored
  in the audio manifest and timeline), then `{"type": "film", "clip": ..., "freeze": true, "cap", "say": <the closing
  note>}` = the film's last frame held while the teacher gives the note. Keep the note short: the video ends on the
  finished film.
- Build-round beat options: `"clip_from": s` on the first beat = the recording is shown from second s of the file on
  (the slate stays until then; used to cut the dead head before anything is typed, keep about 1.5 s of the open tool
  before the first change); `"dots_s": s` on an `ai` beat = the typing dots last s seconds (a real wait shown in the
  clip) before the reply bubble.
- Camera on a real recording: a crop-and-enlarge tool takes a region of the frame (smooth moves, sound copied) so a
  node's text and the result are readable in the 70 % box and a long static result slowly pushes in; a motion-profile
  tool shows where a recording is static.
- `code` with `"code_from": "starter/SKILL.md", "lines": "1-13"`.
- `meta.tts_model` names the voice preset (see the Voice section).

## The shared end screen (standard for EVERY video)

Every video ends with the same end screen: the teacher says thank you over the end card (thank you, subscribe, next
video). It is ONE file (card text + the teacher's line), appended automatically as the last slide by the lesson
builder. Do not write an end slide in a new lesson JSON; do not make a different one. After the finished film the video
goes: film, closing note (`freeze` slide), shared end screen. Optional `meta.next_video` puts the next video's title on
the card; `meta.end_screen: false` leaves it off. Change the wording once in the shared file and every later build uses
it.

## Rules from the owner's feedback on the first video made this way, for every video

- No episode number or label of any kind on screen, in captions, in narration (`meta.no_label: true`; the title slide
  and top bar then show only the title). Folder and file names keep their ids.
- The free pick is the tool we actually use (a local TTS for voice); a paid tool is the paid option, still explained.
  Never put the paid tool in the free column.
- A real result that shows a mistake (extra leg, wrong colour) must be pointed out by the teacher as something to
  catch; pick a clean result as the keeper.
- Captions cover speech only: the silent hold after a film or a sound result gets none.
- Nothing over or under the film while it plays: no `cap` on `film` slides (no text strip). The closing note holds a
  frame with the character in it (`still_at`), not an empty forest.
- The mono `share.mp4` gets +1 dB so it measures about -16.3 LUFS like the master.
- When a clip is zoomed to point out a mistake in a four-up result, hold the whole grid until the line starts, push in
  so the WHOLE picture with the mistake shows (not cropped), and only leave it after the teacher has finished the
  passage.
- The film plays clean, starts on a real picture (no fade-in from black: the slide crossfade is the entrance), and the
  closing note holds a bright frame (`"still_at": seconds` on the `freeze` slide), never the faded-out last frame. A
  character must stand on the ground (contact shadow under every paw) and pass behind things that are in front of it.
- A hand-made (DIY) drawing that is meant to show different views must be four different drawings, not one drawing
  twice.
- An AI reply bubble lands when its result is on screen (`dots_s` on the `ai` beat = the wait the clip really shows).

## How a build round is scripted and recorded (the part that must be real)

Rule: every result named in the chat is a real result on the left. No faked outputs. Do it in this order.

Rule: when any job comes with "make it a video" (or "do it as a video"), this skill applies from the very first step
of that job, and the real work is screen-recorded live as it happens, with the recorders below. Saving stills, logs
and before/afters is not a recording. Never do the work first and plan the video after.

1. **Pick the real story**: the tool's real first result and what was really wrong, the teacher's real tweak, the real
   fixed result. Check every claim against the file, not the notes: measure it (audio facts, pitch, luma, onsets,
   workflow settings inside the PNG/MP4). A claim that the file does not show is rewritten or dropped.
2. **Record ONE continuous session per round**: "we shouldn't close the app every time the teacher gives adjustments;
   keep it open and do it in there till it's all done". Open the tool once, do the first result and every tweak in it,
   close it only when the round is done. Two recorders:
   - a node-tool recorder: one open page. Steps: `load` (a workflow into the same page), `focus` (camera glides to
     nodes), `type` (typed live into a prompt box), `edit`, `run` (real Run click, real GPU job, wait shown sped up and
     marked), `result`, `play` (the sound/video plays in the node), `hold`. Replays are checked against the film files
     (image, video and audio comparisons).
   - a terminal recorder: one open terminal; every command really runs, in a staging folder so only relative file
     names show; output printed as it appeared; the result plays in a preview pane. It refuses to draw a private name;
     real folders are shown as `.` or `..`.
   - Tools that cannot be driven that way must be run by the main session; do not fake a second run.
3. **Time the recording to the narration** (needs the voiced audio): the AI starts when its beat starts, the result is
   fully on screen when the teacher names it, sound plays in the `listen` hold. Only how long each stretch lasts
   changes; the recording is untouched.
4. **Write the lines last**, each from what the clip shows. Re-check chat line, narration line and clip together
   (stills at start, middle, end of the round).
5. "How to ask" cards: `Good ask` on the first ask (what made it a good ask), `The tweak` on the second (what the
   tweak fixed).

## Loudness and captions (built into the lesson builder, every lesson)

- The finished mix is normalised with a two-pass `loudnorm` to -16 LUFS integrated, true peak at most -1.5 dBTP; check
  with `ffmpeg -i master.mp4 -af ebur128=peak=true -f null -`. `narration.wav` stays un-normalised.
- `captions.srt`: a long sentence is cut at a phrase boundary (after punctuation or before and/but/that/on/in/...),
  never after a word that needs the next one; two-line cues break the same way. Check with a scan of the cues; do not
  patch the .srt by hand.
- Running a local model in a round: use the non-interactive form with thinking off; the command keeps no memory, so the
  tweak command carries the story it is about. Retakes until the answer shows what the round teaches are real
  retakes; the narration is written from the take that is kept. Use a model server that is already running as it is;
  never start or restart someone else's app.

## Voice: the teacher = one locked preset

One command, no manual steps: `meta.tts_model` names the preset and the builder calls the voice script with it. The
recipe: a 1.7B base TTS model, in-context clone of one chosen reference clip with its exact transcript, a fixed seed
before every piece, float32, main-talker temperature 0.6 and top_p 0.8, natural pace (no stretch, pieces of at most
150 characters), then ffmpeg at 24 kHz with a low shelf (+3.5 dB at 250 Hz), a small dip at 2.2 kHz, a high shelf
(+10 dB at 5.5 kHz) and a limiter at 0.95. Costs nothing.

- **Hard locked.** Keep one master copy of the preset (recipe, reference clip, code, proof lines, a sha256 of every
  model and locked file). Never edit, move or delete it. Before voicing a video, the repeat test's three files must
  match the proof hashes; if not, stop.
- **The chosen take is made on one GPU in float32.** The recipe is pinned there (the script refuses any other GPU for
  this preset). A CPU run is byte-repeatable with itself but is a different take than the GPU one, so do not mix
  devices in one video: the device is part of each line's cache hash.
- Run heavy GPU steps only when the machine is free; the process id is appended to the video's
  `gpu_pids.txt`. Stop what you started, by PID.
- CPU (no GPU visible): a draft, not the owner's exact take. About 13 s of CPU per second of speech.
- Prove it repeats: voice 3 lines twice and check byte-identical files. Run it after any change to the voice script,
  the models or the environment, and before voicing a whole video.
- Check start, middle and end lines by pitch against the reference; re-roll an outlier.
- A voice cannot be remade from its settings (the same seed gives a new voice each run), so a chosen voice is always
  kept as audio and cloned from it.
- Making new voices: before a sample goes to the owner, save its audio and settings, regenerate the same lines and
  confirm the same voice, and voice 3 new lines to confirm it holds. Offer only voices that pass.
- Any voice change: send the owner a 20 s clip first; voice the whole video only after he says yes.

## Steps

1. Write the JSON; free checks: build the script stage, then the slides stage (fix every `OVERFLOW slide N`).
2. Record the rounds, then voice, then make the round clips, then build the lesson (`master.mp4`, `share.mp4` under
   9 MB, `captions.srt`, `timeline.json`: the slide part before the switch slide must be 13 to 16 minutes).
3. Review before anyone sees it: stills at start, middle, end of every slide and round, a 1 fps contact sheet of every
   clip, voice lines by pitch, privacy (grep the JSON, script, captions, starter file; look at the sheets).
4. Send `share.mp4` through the main session's relay; `master.mp4` stays on disk. Nothing is published.

## Rules for helpers

Never close programs by name or image; stop only processes you started, by PID. Use your own ports, each with its own
output folder. Delete only with the
wipe skill (Recycle Bin), even scratch files you made yourself. Edit files with the editor tools. No installs, no
sign-ins, no sending, nothing published.
