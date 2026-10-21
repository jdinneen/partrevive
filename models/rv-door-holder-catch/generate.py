"""PartRevive: RV entry-door holder catch (plunger + socket), parametric.
Run: python generate.py   (needs build123d + trimesh + numpy + matplotlib)
"""
from pathlib import Path
import numpy as np
import trimesh
from build123d import *

HERE = Path(__file__).resolve().parent
C, MIN = Align.CENTER, Align.MIN

# ---- shared helpers (mesh check + preview render) ----
def check_mesh(path):
    m = trimesh.load(path)
    ext = m.bounds[1] - m.bounds[0]
    wt = bool(m.is_watertight)
    print(f"{path.name}: bbox {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} mm  watertight={wt}  volume={m.volume:.1f} mm3")
    return m, wt


def export(shape, path):
    export_stl(shape, str(path), tolerance=0.01, angular_tolerance=0.1)
    return check_mesh(path)


def render_preview(mesh, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    tris = mesh.triangles
    n = mesh.face_normals
    light = np.array([-0.4, -0.6, 0.7]); light /= np.linalg.norm(light)
    s = np.clip(n @ light, 0, 1) * 0.6 + 0.35
    cols = np.stack([0.20 * s + 0.05, 0.45 * s + 0.08, 0.80 * s + 0.1, np.ones_like(s)], axis=1)
    cols = np.clip(cols, 0, 1)
    fig = plt.figure(figsize=(12, 9), dpi=100, facecolor="#e4e4e4")
    ax = fig.add_axes([0, 0, 1, 1], projection="3d", proj_type="ortho")
    ax.set_facecolor("#e4e4e4")
    ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolors="none", linewidth=0, antialiased=False))
    lo, hi = mesh.bounds
    c = (lo + hi) / 2
    half = (hi - lo).max() / 2
    ax.set_xlim(c[0] - half, c[0] + half); ax.set_ylim(c[1] - half, c[1] + half); ax.set_zlim(c[2] - half, c[2] + half)
    ax.set_box_aspect((1, 1, 1), zoom=1.55)
    ax.view_init(elev=35.264, azim=-45)
    ax.set_axis_off()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def revolved(pts):
    """Revolve a closed (r, z) polygon about Z."""
    f = Face(Wire.make_polygon([Vector(r, 0, z) for r, z in pts], close=True))
    return Solid.revolve(f, 360, Axis.Z)


def csk_cutter(d, head_d, length=30):
    h = (head_d - d) / 2
    shank = Pos(0, 0, -length) * Cylinder(d / 2, length + 1, align=(C, C, MIN))
    cone = Pos(0, 0, -h) * Cone(d / 2, head_d / 2, h, align=(C, C, MIN))
    top = Cylinder(head_d / 2, 1, align=(C, C, MIN))
    return shank + cone + top


def plate(h, hole_d=4.5, head_d=9.0, hole_dx=16.0, size=45.0):
    p = Box(size, size, h, align=(C, C, MIN))
    try:
        p = fillet(p.edges().filter_by(Axis.Z), 4.0)
    except Exception as e:
        print("plate fillet dropped:", e)
    for sx in (-1, 1):                       # holes 2*hole_dx = 32 mm apart, countersunk from top
        p -= Pos(sx * hole_dx, 0, h) * csk_cutter(hole_d, head_d)
    return p


def build_socket(stem_d=10.0, interference=0.4, h=12.0):
    bulb_d = stem_d + 4.0
    rb = bulb_d / 2
    rn = (bulb_d - interference) / 2         # neck is 0.4 mm (diametral) tighter than bulb
    rc = rb + 0.2                            # chamber, slight clearance
    zn = 9.2                                 # neck start
    re = rn + (h - zn - 0.8)                 # 45 deg lead-in to the top face
    cav = revolved([(0, 3.0), (rc, 3.0), (rc, zn - (rc - rn)), (rn, zn), (rn, zn + 0.8),
                    (re, h), (re, h + 1), (0, h + 1)])
    return plate(h) - cav


def build_plunger(stem_d=10.0, length=25.0, plate_t=6.0):
    rs = stem_d / 2
    rb = rs + 2.0
    bulb_len = 8.0
    L = length
    stem = revolved([(0, 0), (rs + 3, 0), (rs, 3), (rs, L - bulb_len), (rb, L - bulb_len + (rb - rs)),
                     (rb, L - 3), (rb - 2.5, L), (0, L)])
    # relief slit so the bulb can squeeze through the 0.4 mm interference
    slit = Pos(0, 0, L - 12) * Box(2 * rb + 2, 1.5, 13, align=(C, C, MIN))
    stem = stem - slit
    return plate(plate_t) + Pos(0, 0, plate_t) * stem


if __name__ == "__main__":
    ok = True
    sock = build_socket()
    plun = build_plunger()
    m, wt = export(sock, HERE / "rv-door-holder-socket.stl"); ok &= wt
    m, wt = export(plun, HERE / "rv-door-holder-plunger.stl"); ok &= wt
    both = Compound([Pos(-30, 0, 0) * sock, Pos(30, 0, 0) * plun])
    m, wt = export(both, HERE / "rv-door-holder-plate-of-both.stl"); ok &= wt
    render_preview(m, HERE / "preview.png")
    print("ALL WATERTIGHT" if ok else "WARNING: non-watertight mesh")
