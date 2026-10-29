---
name: animation-qa
description: Check any Blender animation before the owner sees it - the clean-walk check (foot slide, ground contact, IK reach, bone pops, speed vs stride x cadence), the camera smoothness check (speed, acceleration, jerk, turn rate per frame, plotted), the ray-block and too-close checks, hand and prop clash checks, and a review of every frame on contact sheets that you actually look at. Use after every recorded round that moves something and before every preview or render is sent on.
---

# Animation QA

Real feedback on earlier work was "robotic walking", "camera work needs work" and a camera "too jumpy and not
smooth". These checks catch those problems with numbers first, and then by eye. The rule: **every frame is looked at
before anything is reported.** A check passing does not mean a frame looks right.

> The helper scripts named below (`walk_check`, `walk_summary`, `plot_flow`, `hand_check`, ...) belong to one
> project's build folder and are not part of this repo. The thresholds and the order of work are the useful part:
> write the same checks for your own rig, keep the thresholds, and keep the rule about looking at every frame.

Run from the build folder with the build's Blender window open (see **blender-recorded-build**). Scripts run
inside that window are called `exec` scripts; plain `python` scripts run outside it. The checks are written for one
rig with foot bones named `Foot_L/R` and `Toe_L/R`; for a new character copy them and change the rig and bone names.

## 1. Clean-walk check (every clip with feet)

Write the result of each test to a JSON file per action. Tests:

| Test | Pass |
|---|---|
| slide | a planted point (heel, ball or toe within 3 mm of the ground on two frames in a row) moves at most 2 mm per frame |
| ground | no point more than 3 mm under the ground; a planted foot no more than 1 cm above it (no float) |
| reach | the IK ankle within 1 mm of its foot control on every frame |
| pops | per deform bone, the change of acceleration stays under 6 cm and 14 degrees per frame cubed (a clean walk peaks about 5 cm / 12 deg; real faults measured 12-18 cm) |
| speed | the root's average speed on the flat matches stride x cadence (ratio near 1.0), so the feet don't skate or moonwalk |

Then print one summary line per clip. Every clip must say `pass=True`. If one fails, fix the cause (the footprint
plan, a knee pole, a riser guard). Never loosen the threshold.

## 2. Camera smoothness check (every moving camera)

Write a frame-by-frame report: speed (m/s), acceleration, jerk, turn rate (deg/s) and turn acceleration, each with
its worst frame, plus `too_close` and `blocked`. Plot it and open the picture. Look for spikes: a peak that its
neighbours don't share is a jump on screen, even when the number looks small. Targets taken from studying real
films:

- forward speed about 0.5 x the camera's height above what is under it (m/s); calm at every height
- orbit or pan under about 20 deg/s, tilt under about 12 deg/s; bank 3-5 deg only on an aerial curve
- ease every move (smootherstep); no linear starts or stops

How a clean camera was built: make one camera from pose functions, blend them in polar coordinates round the
subject's root so moves arc round it and never through it, and smooth the whole path twice (cosine window, k=8). When
the camera starts already moving, pad the pose list before frame 1 before smoothing, or the first frames spike.

## 3. Ray-block and too-close checks

Cast a ray from the target to the camera every second frame and list anything solid in between. Grass, flowers,
motes, the characters and glow volumes count as see-through. The report's `blocked` runs must be empty, or each one
must be a wipe you meant (a trunk crossing the lens on purpose). `too_close` (the camera inside the subject's body
column) must be empty. Remove particles within 0.9 m of the lens. A low camera by a path sits in the verge, so keep
it on the path edge and trim blades within 0.45 m of its path.

## 4. Hands and props (characters)

Render each hand from three sides for the key frames and open every image. Count mesh vertices that end up inside
a held pen or book: the number must be 0. Check how a prop is carried the same way.

## 4b. Leaf clearance

The ray-block check only looks from the subject back to the camera, so leaves brushing the lens slip past it. Also
run a lens-side check: cast nine rays across the lens's view out to 2.2 m on every frame and list any tree, bush,
fern or grass it touches with its frames. Move the one-off plants it lists off the set and run it again. A shared
mesh can't be moved, so trim or re-aim instead. Report what was moved and anything still touching. For a shot with
cuts, check each camera on its own frames (speed, acceleration, jerk, turn rate and the frames over 30 deg/s). A cut
is not a jolt, but shake inside a shot is a fail.

## 5. Every frame, looked at

1. The GPU grant must be current (see **gpu-time**). Render every frame small through the shot's cameras (15 percent
   size, 8 samples, in chunks of 240 frames; check the grant before each chunk and stop on NO-GO).
2. Lay the frames out on numbered contact sheets.
3. **Open every sheet** and write down, per frame range, what is wrong: pops, a frame where the head is cropped, a
   hand sweeping past the lens, something showing too early, a prop through a hand, a dark or brown frame, a mote on
   the lens, a character popping out of view. Fix, re-run the checks, look again.
4. Only then render full size, on both cards from one shared frame pool (see **blender-recorded-build**), and hand
   the preview on with the check numbers: walk summary, worst camera values, blocked and too_close, and the known
   small issues you saw and left.
