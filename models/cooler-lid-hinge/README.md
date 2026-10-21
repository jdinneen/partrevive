# Universal Cooler Lid Hinge

A two-leaf hinge to replace a broken lid hinge on an ice chest or cooler. Two identical flat leaves, each with a row of knuckles that interleave along one long edge, are joined by a 5 mm pin. Screw each leaf to the lid and the body. The standard set fits a 70 mm hinge footprint; the "wide" set is for large coolers.

## Files

| File | What |
|---|---|
| `hinge_leaf.stl` | one leaf, 70 x 30 mm plate (print two) |
| `hinge_pin.stl` | 5 mm pin, 72 mm long |
| `hinge_leaf_wide.stl` | one wide leaf, 100 mm long, holes 80 mm apart (print two) |
| `hinge_pin_wide.stl` | 5 mm pin, 102 mm long |

Print two identical leaves. To assemble, turn one leaf 180 degrees around the vertical axis so its knuckles slot between the other leaf's, then push the pin through. The pin hole is 5.3 mm (pin diameter plus 0.3 mm clearance), so you can use the printed pin or a 5 mm (M5) bolt with a nut, or a 5 mm steel rod. A printed pin can be glued or capped with a dab of hot glue at the ends.

## Parameters (top of `generate.py`; `make_leaf(leaf_len, hole_spacing, pin_d, n_knuckles)`)

| Parameter | Default | Wide |
|---|---|---|
| `leaf_len` | 70 mm | 100 mm |
| `hole_spacing` | 50 mm | 80 mm |
| `pin_d` | 5 mm | 5 mm |
| `n_knuckles` (must be even) | 6 | 8 |

Fixed values: plate 30 x 4 mm, barrel outer diameter 10 mm, two countersunk holes for 4.5 mm screws (9 mm head), 0.5 mm gaps between knuckles, 0.3 mm pin clearance.

## Recommended print settings

- Material: ASA for sun exposure, PETG otherwise.
- 0.2 mm layers, 4 walls, 40% infill.
- Orientation: print each leaf flat on its plate, with the countersinks facing up. The layers then run along the plate, so the screw loads act within the layers, and the barrel rounds off the bed edge. The underside of each barrel is a small curved overhang; a brim helps, or print the leaf on its side (plate vertical, hinge axis along the bed) so the knuckles need no support, with the pin hole running along the layers. If you print flat and see sagging on the barrels, add a small sacrificial bridge under them and trim it off.
- Print the pin lying down, or standing up for a rounder pin.

## Note

This is a free design offered as-is, with no guarantee that it fits your cooler or carries your lid's weight. Check your hole pattern and loads first.

Don't have a printer? PartRevive prints this and ships it: https://jdinneen.github.io/partrevive/parts/cooler-lid-hinge/
