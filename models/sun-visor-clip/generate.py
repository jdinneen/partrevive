"""PartRevive: universal sun-visor rod retainer clip (parametric).
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


def csk_cutter(d, head_d, length=30):
    """Countersunk screw cutter along Z, head face at z=0, shank going to -z."""
    h = (head_d - d) / 2
    shank = Pos(0, 0, -length) * Cylinder(d / 2, length + 1, align=(C, C, MIN))
    cone = Pos(0, 0, -h) * Cone(d / 2, head_d / 2, h, align=(C, C, MIN))
    top = Cylinder(head_d / 2, 1, align=(C, C, MIN))
    return shank + cone + top


def build_clip(rod_d=10.0, screw_d=4.0, wall=2.5, depth=12.0, snap=0.85,
               tab_len=14.0, tab_t=4.0, head_d=8.0):
    r = rod_d / 2
    R = r + wall
    body = Cylinder(R, depth, align=(C, C, MIN))
    body += Pos(0, -R, 0) * Box(R + tab_len, tab_t, depth, align=(MIN, MIN, MIN))
    body -= Pos(0, 0, -1) * Cylinder(r, depth + 2, align=(C, C, MIN))      # rod bore
    gap = snap * rod_d                                                       # 15% narrower than rod
    body -= Pos(0, 0, -1) * Box(gap, R + 2, depth + 2, align=(C, MIN, MIN))  # snap opening (+Y)
    # countersunk screw hole through the tab, head on the +Y face
    hole_x = R + tab_len / 2
    body -= Pos(hole_x, -R + tab_t, depth / 2) * Rot(-90, 0, 0) * csk_cutter(screw_d + 0.4, head_d)
    # fillets on snap lips (vertical edges at the opening); drop if they fail
    try:
        lips = body.edges().filter_by(Axis.Z).filter_by_position(Axis.Y, 0.1, R + 1)
        body = fillet(lips, 1.0)
    except Exception as e:
        print("lip fillet dropped:", e)
    return body


if __name__ == "__main__":
    ok = True
    for rod in (9, 10, 11, 12):
        p = build_clip(rod_d=rod)
        m, wt = export(p, HERE / f"sun-visor-clip_rod{rod}.stl")
        ok &= wt
        if rod == 10:
            render_preview(m, HERE / "preview.png")
    print("ALL WATERTIGHT" if ok else "WARNING: non-watertight mesh")
