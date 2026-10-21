"""PartRevive: tonneau-cover prop-rod retention clip (parametric).
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


def build_clip(rod_d=8.0, wall=3.0, base=(40.0, 20.0, 3.0), hole_d=3.5, hole_dx=14.0,
               open_frac=0.85, outer_fillet=1.5):
    L, W, T = base
    r = rod_d / 2
    R = r + wall                       # jaw height = 2R = rod_d + 2*wall = rod_d + 6
    gap = open_frac * rod_d
    # raise the jaw centre so the lip tops stand rod_d + 6 mm above the base (before lip rounding)
    zc = T + rod_d + 2 * wall - (R ** 2 - (gap / 2) ** 2) ** 0.5
    b = Box(L, W, T, align=(C, C, MIN))
    try:
        b = fillet(b.edges().filter_by(Axis.Z), 2.0)
    except Exception as e:
        print("base fillet dropped:", e)
    jaw = Pos(0, 0, zc) * (Rot(90, 0, 0) * Cylinder(R, W))
    jaw += Pos(0, 0, T) * Box(2 * R, W, zc - T, align=(C, C, MIN))
    body = b + jaw
    body -= Pos(0, 0, zc) * (Rot(90, 0, 0) * Cylinder(r, W + 2))
    body -= Pos(0, 0, zc) * Box(gap, W + 2, R + 4, align=(C, C, MIN))
    for sx in (-1, 1):
        body -= Pos(sx * hole_dx, 0, -1) * Cylinder(hole_d / 2, T + 2, align=(C, C, MIN))
    # lip fillets: outer edge 1.5, inner edge 1.0; each dropped if it fails
    z_in = zc + (r ** 2 - (gap / 2) ** 2) ** 0.5
    z_out = zc + (R ** 2 - (gap / 2) ** 2) ** 0.5
    mid = (z_in + z_out) / 2
    for lo, hi, rad in ((mid, z_out + 1, outer_fillet), (zc, mid, 1.0)):
        try:
            es = body.edges().filter_by(Axis.Y).filter_by_position(Axis.Z, lo, hi)
            es = [e for e in es if abs(abs(e.center().X) - gap / 2) < 0.05]
            body = fillet(es, rad)
        except Exception as e:
            print(f"lip fillet r={rad} dropped:", e)
    # print orientation: Y (jaw axis) vertical, so every layer is the full U profile
    body = Rot(90, 0, 0) * body
    body = Pos(0, 0, -body.bounding_box().min.Z) * body
    return body


if __name__ == "__main__":
    ok = True
    for rod in (6, 8, 10):
        p = build_clip(rod_d=rod)
        m, wt = export(p, HERE / f"tonneau-prop-rod-clip_rod{rod}.stl")
        ok &= wt
        if rod == 8:
            render_preview(m, HERE / "preview.png")
    print("ALL WATERTIGHT" if ok else "WARNING: non-watertight mesh")
