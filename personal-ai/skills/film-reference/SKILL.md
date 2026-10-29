---
name: film-reference
description: Study real film shots for a scene the owner describes and turn them into a numeric shot recipe for a Blender build - per beat the frames, camera heights, distances, lenses, easing, speed rules, forest or set density, light setup and walk timing. Private study only; nothing from the films is copied or published. Use when the owner says to get inspiration from movies, names a film or scene to feel like ("that Disney feel"), or a camera or scene keeps getting rejected.
---

# Film reference

The owner's order: "go get inspiration from movies that showcase what I have described and see how you can get it."
The first run studied 12 references and ended in a recipe that a film-style camera round was built from. Use a
finished recipe file as the model for the shape of the output.

## Rules

- **Study only.** Clips and stills are for looking at camera, light and timing. No character, design, footage, frame
  or sound from a film goes into our work or gets published. No dialogue is quoted. Any quote stays under 15 words.
  Write "feel only, everything original" in the recipe when the owner names a studio's feel.
- Stills stay in the build's `reference/stills/`, private, and are never placed in a video or sent on.
- Film times are approximate ("about"). An entry written from memory because the clip was blocked says so.
- Read-only web work. No sign-ins, no paid sources, no installs.

## Steps

1. **Memory first.** Recall the scene. Write the owner's description as numbered story beats (for a walk-up: 1 sky to
   forest, 2 twig snap, 3 walk and talk, 4 rise to reveal, 5 doors into the light), using his words.
2. **Find shots.** Search the web for well-known film moments that show each beat: an opening, a reveal, a walk and
   talk, an insert then a wide, a fly into light. Aim for 2-3 per beat and about 10-12 in all, including any film the
   owner named.
3. **Look at them.** For each clip, fetch its info and, when the stream allows it, cut stills (see the **youtube**
   skill). If the video site refuses the stream, the clip's storyboard tiles (yt-dlp format `sb0`, one small tile every
   2 s) are enough to read the camera path and light. Save them as study strips named
   `NN_<film>_<shot>.jpg`. Open each one and look.
4. **Write one entry per reference:** film and year, where (about mm:ss, clip id), which beat, the camera (move,
   height, speed, lens feel, how long, ease), light and colour, what makes it work, and "Take:" (the one thing we use).
5. **Turn it into numbers.** The recipe is for our frame size and fps (Shorts: 1080 x 1920, 30 fps):
   - general camera rules: one continuous camera or not, start already moving, speed vs height, pan and tilt limits,
     easing, bank
   - per beat: a keyframe table (frame, height, distance, pitch, lens, note), plus the frames for sound and story
     events
   - which beat stretches for a longer voice-over and which keep their frame counts
   - set or forest density targets (layers by distance, counts per area, gaps for light), light setup (sun angle,
     colour, strength, volume density and anisotropy, sky, grade), walk timing (cadence, step length, bob, sway, arm
     swing, lag), prop carry and secondary motion (hops, squash, hang)
   - any recipe item the owner has already rejected (like a tucked book) gets marked as not used
6. **Save it** as `reference/FILM_REFERENCE.md`, plus a PDF when the main seat is sending it to the owner. Save a
   project memory saying what was studied and where the recipe is.
7. **Build from it** in a recorded round (**blender-recorded-build**), and check the result against the recipe's
   numbers with the **animation-qa** skill.
