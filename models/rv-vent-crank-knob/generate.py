"""RV roof-vent crank knob (parametric). Run: python generate.py
Requires build123d + trimesh (+ matplotlib for preview.png)."""
import math, os
from build123d import *
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- parameters (mm) ----
knob_d = 58.0
knob_h = 22.0
rim_fillet = 1.5
n_flutes = 12
flute_d = 5.0
flute_depth = 2.0
pocket_depth = 16.0
grub_d = 3.4          # tap size for an M4 grub screw (use 4.5 for a clearance hole + nut trap instead)
grub_z = 8.0          # height of grub hole above the underside


def make_knob(shaft="round", shaft_d=12.7, flat_depth=0.0, hex_af=8.0, square_s=8.0):
    R = knob_d / 2
    body = Pos(0, 0, knob_h / 2) * Cylinder(R, knob_h)
    try:
        top = body.edges().filter_by(GeomType.CIRCLE).sort_by(Axis.Z)[-1]
        body = fillet(top, rim_fillet)
    except Exception as e:  # drop the fillet rather than fight it
        print("fillet skipped:", e)
    # flutes: cylinder centre sits so the cut is flute_depth deep
    rc = R + flute_d / 2 - flute_depth
    for k in range(n_flutes):
        a = 2 * math.pi * k / n_flutes
        body -= Pos(rc * math.cos(a), rc * math.sin(a), knob_h / 2) * Cylinder(flute_d / 2, knob_h + 2)
    # shaft pocket from the underside
    if shaft == "round":
        p = Cylinder(shaft_d / 2, pocket_depth, align=(Align.CENTER, Align.CENTER, Align.MIN))
        if flat_depth > 0:
            # D-shaped: remove the sliver beyond x = r - flat_depth (flat on the +X side)
            cut = Pos(shaft_d / 2 - flat_depth, -shaft_d, -1) * Box(
                shaft_d, shaft_d * 2, pocket_depth + 2, align=(Align.MIN, Align.MIN, Align.MIN))
            p -= cut
    elif shaft == "hex":
        p = extrude(RegularPolygon(hex_af / math.sqrt(3), 6), amount=pocket_depth)
    elif shaft == "square":
        p = extrude(Rectangle(square_s, square_s), amount=pocket_depth)
    else:
        raise ValueError(shaft)
    body -= p
    # radial grub-screw hole, between two flutes, from outside into the pocket
    ang = 105.0  # 15 deg off a flute, 105 deg from the flat
    g = Rot(Z=ang) * Pos(0, 0, grub_z) * (Rot(Y=90) * Pos(0, 0, R / 2 + 0.5) * Cylinder(grub_d / 2, R + 1))
    body -= g
    return body


VARIANTS = {
    "knob_round12p7": dict(shaft="round", shaft_d=12.7, flat_depth=0.0),
    "knob_round12p7_flat1": dict(shaft="round", shaft_d=12.7, flat_depth=1.0),
    "knob_hex8": dict(shaft="hex", hex_af=8.0),
    "knob_square8": dict(shaft="square", square_s=8.0),
}


def render(mesh, path, w=1200, h=900):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    v, f = trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, max_edge=3.0)
    mesh = trimesh.Trimesh(v, f, process=False)
    n = mesh.face_normals
    light = np.array([0.4, -0.5, 0.8]); light /= np.linalg.norm(light)
    s = 0.35 + 0.65 * np.clip(n @ light, 0, 1)
    cols = np.stack([0.20 * s + 0.1, 0.45 * s + 0.1, 0.75 * s + 0.1, np.ones_like(s)], 1).clip(0, 1)
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor="#e6e6e6")
    ax = fig.add_axes([0, 0, 1, 1], projection="3d", facecolor="#e6e6e6")
    ax.add_collection3d(Poly3DCollection(v[f], facecolors=cols, edgecolors="none", linewidth=0, antialiased=False))
    c = (v.max(0) + v.min(0)) / 2; r = (v.max(0) - v.min(0)).max() / 2 * 0.95
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=35.264, azim=-45); ax.set_axis_off()
    fig.savefig(path, dpi=100, facecolor=fig.get_facecolor()); plt.close(fig)


if __name__ == "__main__":
    for name, kw in VARIANTS.items():
        part = make_knob(**kw)
        path = os.path.join(HERE, name + ".stl")
        export_stl(part, path)
        m = trimesh.load(path)
        bb = m.bounds
        print(f"{name}.stl bbox mm: {bb[1,0]-bb[0,0]:.2f} x {bb[1,1]-bb[0,1]:.2f} x {bb[1,2]-bb[0,2]:.2f}  watertight={m.is_watertight}")
    try:
        render(trimesh.load(os.path.join(HERE, "knob_round12p7_flat1.stl")), os.path.join(HERE, "preview.png"))
        print("preview.png written")
    except Exception as e:
        print("preview skipped:", e)
