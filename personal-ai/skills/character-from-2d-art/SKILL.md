---
name: character-from-2d-art
description: Build a stylized 3D character in Blender that matches 2D art the owner picked - model, materials that don't look plastic, real five-finger hands with grip poses, natural prop carry, a one-number face-emotion control, the rig, and a side-by-side likeness loop against the art before anything goes to the owner. Use for any person, creature or mascot built from drawings or a model sheet (a teacher character, a lantern mascot, game inhabitants).
---

# Character from 2D art

Built once in full for a teacher character and a lantern mascot, and the owner corrected it seven times. Every
correction is a step below. The build itself runs through the **blender-recorded-build** skill: one open window,
every pass a recorded round.

> The per-build helper scripts named in passing (dimension module, hands, rig, walk, likeness) are not part of this
> repo. This page is the method.

## The owner's corrections (each one is a rule here)

| His words | What it means |
|---|---|
| "he looks too arty ... Make it look more smooth and clean. With a hint of realism" | No toon bands or ink outline. Use clean PBR with a hint of realism. |
| "fix hands, that's unacceptable as is" | Real hands, never mitts. |
| "looks plastic and robotic walking" | Real surface detail and a weighted, natural walk. |
| "why is he carrying an open book?" | Props are carried the way people really carry them. |
| "the way he holds the book is not natural", "his face and hair don't match the look" | The carry gets checked by eye from three sides, and the face gets the likeness loop. A book tucked under the arm was also rejected. |

## Steps

1. **Memory and the art.** Recall the character first. Find the picked art, open it, and write a look list: height,
   silhouette, hair (line, volume, how it is swept), face (nose, brow, cheeks, chin, smile), glasses, clothes layer by
   layer, colours, props. That list is the spec. Never guess from memory of the art.
2. **Dimensions module.** Put every size in one module: 1.8 m for a grown man, foot points (heel, ball, toe) for the
   walk check, hand sizes. Every other module reads from it.
3. **Model round** (v1 = the big shapes, tweak = the details). Props (pen, ledger, tools) are their own meshes. Tag the
   body's parts with a `part` attribute as you build so skin weights can come from the tags later.
4. **Look: clean, but not plastic.** Smooth forms (subdivision) and soft PBR, plus real micro detail:
   - skin: subsurface, pores, colour variation (rosier nose, cheeks and ears), forehead lines and crow's feet
   - hair, beard, moustache and brows: real Curves strands, clumped and swept like the art. Grey variation and strand
     sheen. Sink the non-hair vertices of the shell under the skin (a masked grid gives a stepped hairline)
   - cloth: weave, fuzz, darker in the creases, folds at elbows, waist and knees
   - metal: scratches and tarnish. Leather: creases and a worn shine. Books: matte leather, no subsurf
   - light it like the scene it lives in (bright and inviting for friendly work), never a dark grey studio only
5. **Hands.** A palm with a thenar pad and wrist, four fingers and a thumb, three segments each with knuckles and
   nails. Wrist to middle fingertip is about 0.19 m for 1.8 m. Skin like the face. Three bones per finger, thumb
   included (15 per hand). Poses (pen grip, book hold, open, flat push) are sets of curl angles blended per frame, so
   fingers really wrap what they hold. Then solve the prop where those fingers hold it, not the fingers to a floating
   prop. Check each hand from three sides, and count finger vertices inside the pen or book: it must be 0.
6. **Rig.** IK legs with knee poles, a foot control per foot with heel-to-toe roll, toe bones, grip bones for props,
   head and eye aim at one Look target, IK/FK switch on any arm that pushes or reaches. Aim knee poles from the body
   heading, not the foot axis (a pitched foot flips it). Coat tails or skirts get spring bones. A small companion
   rides a seat bone and gets its own secondary motion. For a game inhabitant: in-place loops, a tool bone and a
   carry attachment bone, separate tool and goods meshes, proven with a headless check.
7. **Face emotion control.** One topology, many expressions: build every expression from the same pieces in the same
   order, so each expression is a shape key of one mesh. One number drives them all (face = 0 rest, 1 happy, 2 sad,
   3 mad; blink separate), using drivers of the form `1-abs(f-c)`, never `max`. An animator keys one value.
8. **Natural carry.** Carry things closed and the way a person really would. A ledger hangs at the left side in the
   hand: palm and fingers on the cover, thumb round the spine, the arm hanging with a soft elbow and a smaller swing for
   the weight. Check it from the front, three-quarter and side, and look at the images. If neither the art nor the
   owner says how it is carried, ask through the main seat. Don't guess a new pose.
9. **Walk and acting.** Footprints first, then the body. Then run the clean-walk check in the **animation-qa** skill on
   every clip. An older man walks at about 95-100 steps a minute, 0.58-0.62 m steps, a light 2.5-3.5 cm bob, overlap
   (the chest after the hips, elbows and wrists lagging), and no two steps alike.
10. **Likeness loop, before anything goes to the owner.** Render the head in studio light from the front,
    three-quarter and profile. Then put the art on top and the renders below (set crop boxes per character). Open the
    image, list every difference (hairline, nose, glasses size, beard length, brows, colour), fix them in a recorded
    round, and repeat. Do the same for the full body against the art. Report an honest score out of 10. Below 8, keep
    going.
11. **Record and report** through the blender-recorded-build skill: privacy scan, `plan.md`, memory, preview to the
    main seat.
