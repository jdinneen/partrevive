"""Universal two-leaf cooler lid hinge (parametric). Run: python generate.py
Requires build123d + trimesh (+ matplotlib for preview.png)."""
import math, os
from build123d import *
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))

plate_w = 30.0
plate_t = 4.0
barrel_d = 10.0
knuckle_gap = 0.5     # axial gap between knuckles
pin_clear = 0.3       # hole = pin_d + pin_clear
screw_d = 4.5
csk_d = 9.0           # countersink head diameter (90 degree)
side_gap = 0.5        # gap between the barrel and the plate edge


def make_leaf(leaf_len=70.0, hole_spacing=50.0, pin_d=5.0, n_knuckles=6):
    """Leaf lies flat: X along the hinge, Y across, Z up. Hinge axis is the line y=0, z=barrel_d/2.
    Even n_knuckles: this leaf carries knuckles 0,2,4..; rotated 180 deg about Z through the leaf
    centre it carries 1,3,5.., so two identical leaves interleave."""
    kl = (leaf_len - (n_knuckles - 1) * knuckle_gap) / n_knuckles
    zc = barrel_d / 2
    y0 = barrel_d / 2 + side_gap
    leaf = Pos(leaf_len / 2, y0 + plate_w / 2, plate_t / 2) * Box(leaf_len, plate_w, plate_t)
    for i in range(0, n_knuckles, 2):
        cx = i * (kl + knuckle_gap) + kl / 2
        leaf += Pos(cx, (y0 + 0.5) / 2, plate_t / 2) * Box(kl, y0 + 0.5, plate_t)   # web: knuckle to plate (overlaps plate)
        leaf += Pos(cx, 0, zc) * Rot(Y=90) * Cylinder(barrel_d / 2, kl)
    leaf -= Pos(leaf_len / 2, 0, zc) * Rot(Y=90) * Cylinder((pin_d + pin_clear) / 2, leaf_len + 2)
    yc = y0 + plate_w / 2
    cs_h = (csk_d - screw_d) / 2
    for sx in (-1, 1):
        x = leaf_len / 2 + sx * hole_spacing / 2
        leaf -= Pos(x, yc, plate_t / 2) * Cylinder(screw_d / 2, plate_t + 2)
        leaf -= Pos(x, yc, plate_t - cs_h / 2 + 0.0005) * Cone(screw_d / 2, csk_d / 2, cs_h + 0.001)
    return leaf


def make_pin(pin_d=5.0, length=72.0):
    return Pos(0, 0, length / 2) * Cylinder(pin_d / 2, length)


VARIANTS = {
    # suffix: (leaf_len, hole_spacing, pin_d, n_knuckles)
    "": (70.0, 50.0, 5.0, 6),
    "_wide": (100.0, 80.0, 5.0, 8),
}


def render(meshes, path, w=1200, h=900):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor="#e6e6e6")
    ax = fig.add_axes([0, 0, 1, 1], projection="3d", facecolor="#e6e6e6")
    light = np.array([0.4, -0.5, 0.8]); light /= np.linalg.norm(light)
    allv = np.vstack([m.vertices for m, _ in meshes])
    for m, base in meshes:
        v2, f2 = trimesh.remesh.subdivide_to_size(m.vertices, m.faces, max_edge=3.0)
        m = trimesh.Trimesh(v2, f2, process=False)
        s = 0.35 + 0.65 * np.clip(m.face_normals @ light, 0, 1)
        cols = np.concatenate([(np.array(base)[None, :] * s[:, None]).clip(0, 1), np.ones((len(s), 1))], 1)
        ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolors=cols, edgecolors="none", linewidth=0, antialiased=False))
    c = (allv.max(0) + allv.min(0)) / 2; r = (allv.max(0) - allv.min(0)).max() / 2 * 0.95
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=35.264, azim=-45); ax.set_axis_off()
    fig.savefig(path, dpi=100, facecolor=fig.get_facecolor()); plt.close(fig)


def report(name, path):
    m = trimesh.load(path)
    bb = m.bounds
    print(f"{name}: bbox mm {bb[1,0]-bb[0,0]:.2f} x {bb[1,1]-bb[0,1]:.2f} x {bb[1,2]-bb[0,2]:.2f}  watertight={m.is_watertight}")
    return m


if __name__ == "__main__":
    for suffix, (L, sp, pd, nk) in VARIANTS.items():
        lp = os.path.join(HERE, f"hinge_leaf{suffix}.stl")
        pp = os.path.join(HERE, f"hinge_pin{suffix}.stl")
        export_stl(make_leaf(L, sp, pd, nk), lp)
        export_stl(make_pin(pd, L + 2), pp)
        leaf = report(f"hinge_leaf{suffix}.stl", lp)
        pin = report(f"hinge_pin{suffix}.stl", pp)
        if suffix == "":
            # assembled preview: leaf B = leaf A rotated 180 deg about Z through (L/2, 0)
            b = leaf.copy()
            b.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [0, 0, 1], [L / 2, 0, 0]))
            p = pin.copy()
            p.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
            p.apply_translation([-1, 0, barrel_d / 2])
            # sanity: pin should sit inside the barrels
            print("pin bounds x:", [round(float(v), 2) for v in p.bounds[:, 0]], "leaf x:", [round(float(v), 2) for v in leaf.bounds[:, 0]])
            try:
                print("leaf A/B overlap volume (mm^3):", round(float(leaf.intersection(b).volume), 4))
            except Exception as e:
                print("overlap check skipped:", e)
            try:
                render([(leaf, (0.2, 0.45, 0.75)), (b, (0.85, 0.5, 0.2)), (p, (0.5, 0.5, 0.5))], os.path.join(HERE, "preview.png"))
                print("preview.png written")
            except Exception as e:
                print("preview skipped:", e)
