# RV Roof Vent Crank Knob

A replacement hand knob for the crank on a manual RV roof vent (the kind you wind to raise and lower the lid). It is a round, fluted grip, 58 mm across and 22 mm tall, with a socket on the underside that slips over the crank shaft and a small side screw to lock it on. Pick the variant that matches your shaft: round (12.7 mm / 1/2 in, with or without a flat), hex 8 mm, or square 8 mm. Measure your shaft with calipers before you print; shaft sizes vary between vent brands.

## Files

| File | Socket |
|---|---|
| `knob_round12p7.stl` | round, 12.7 mm, no flat |
| `knob_round12p7_flat1.stl` | round, 12.7 mm with a 1 mm flat on one side (D-shaft) |
| `knob_hex8.stl` | hex, 8 mm across the flats |
| `knob_square8.stl` | square, 8 mm |

## Parameters (edit at the top of `generate.py`, then run `python generate.py`)

| Parameter | Default | Meaning |
|---|---|---|
| `knob_d`, `knob_h` | 58, 22 mm | knob diameter and height |
| `n_flutes`, `flute_d`, `flute_depth` | 12, 5, 2 mm | grip flutes around the rim |
| `rim_fillet` | 1.5 mm | rounding on the top edge |
| `shaft` | `"round"` | `"round"`, `"hex"` or `"square"` |
| `shaft_d` | 12.7 mm | round shaft diameter |
| `flat_depth` | 0 mm | depth of the flat on a round shaft (0 = none) |
| `hex_af` | 8 mm | hex across-flats |
| `square_s` | 8 mm | square side |
| `pocket_depth` | 16 mm | socket depth from the underside |
| `grub_d`, `grub_z` | 3.4 mm, 8 mm | M4 grub-screw hole (tap size) and its height |

Pockets are cut at the nominal size with no extra clearance. If your print is too tight, add 0.1 to 0.2 mm to the size. The side hole is 3.4 mm so an M4 grub screw can cut its own thread in plastic; change `grub_d` to 4.5 if you would rather use a clearance hole and a nut.

## Recommended print settings

- Material: ASA if the vent is in the sun, PETG otherwise.
- 0.2 mm layers, 4 walls, 40% infill.
- Orientation: print face-down, with the flat top on the bed and the socket opening facing up. No supports are needed. The layers then run around the knob, so twisting loads travel along the layers, and the first layer gives a smooth top.

## Note

This is a free design offered as-is, with no guarantee that it fits your vent. Check your shaft first.

Don't have a printer? PartRevive prints this and ships it: https://jdinneen.github.io/partrevive/parts/rv-vent-crank-knob/
