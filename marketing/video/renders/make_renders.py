"""Turntable renders for PartRevive vertical videos. Usage: python make_renders.py [slug ...]"""
import os, sys, subprocess, glob
import numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
import shutil
FFMPEG = (glob.glob(os.path.expandvars("%LOCALAPPDATA%/Microsoft/WinGet/Packages/Gyan.FFmpeg*/*/bin/ffmpeg.exe")) or [shutil.which("ffmpeg.exe")])[0]  # needs libx264; Playwright build lacks it
FONT = r"C:\Windows\Fonts\segoeuib.ttf"
W, H, FPS, NF = 1080, 1920, 30, 90
SECS = 15
JOBS = {
 "sun-visor-clip": ("models/sun-visor-clip/sun-visor-clip_rod10.stl", "Sun visor clip", "Print in PETG, 4 walls, 40% infill"),
 "cooler-lid-hinge": ("models/cooler-lid-hinge/hinge_leaf.stl", "Cooler lid hinge", "Print in PETG, 4 walls, no supports"),
 "rv-vent-crank-knob": ("models/rv-vent-crank-knob/knob_round12p7.stl", "RV vent crank knob", "Print in ASA for sun exposure"),
}
BG, MAT = (0xe6,0xe6,0xe6), np.array([0x2f,0x6d,0xb5], float)
RW, RH, SS = W, 640, 2  # render region (middle third), supersample

def load(path):
    m = trimesh.load(os.path.join(ROOT, path), force="mesh")
    v = np.asarray(m.vertices, float)
    v = v - (v.min(0)+v.max(0))/2
    return v, np.asarray(m.faces)

def render(v, f, ang, elev=25.0):
    # Mesh z is vertical (print orientation); rotate about z, then tilt camera down
    c, s = np.cos(ang), np.sin(ang)
    Rz = np.array([[c,-s,0],[s,c,0],[0,0,1]])
    e = np.radians(elev); ce, se = np.cos(e), np.sin(e)
    # rows: screen x, depth (larger = farther), screen up; camera elevated by elev degrees
    Rx = np.array([[1,0,0],[0,ce,-se],[0,se,ce]])  # y->depth/tilt
    p = v @ Rz.T @ Rx.T   # screen x = p0, depth = p1, screen up = p2
    return p

def frame_image(v, f, ang, scale):
    p = render(v, f, ang)
    tri = p[f]
    n = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
    nl = np.linalg.norm(n, axis=1); nl[nl==0] = 1
    n = n/nl[:,None]
    n[n[:,1]>0] *= -1 if False else 1
    # orient normals toward camera (camera at -depth direction): make n[1] <= 0
    n = np.where((n[:,1]>0)[:,None], -n, n)
    light = np.array([-0.4,-0.7,0.6]); light /= np.linalg.norm(light)
    sh = 0.35 + 0.65*np.clip(n@light, 0, 1)
    depth = tri[:,:,1].mean(1)
    order = np.argsort(-depth)  # far first
    img = Image.new("RGB", (RW*SS, RH*SS), BG)
    d = ImageDraw.Draw(img)
    cx, cy = RW*SS/2, RH*SS/2
    xs = cx + tri[:,:,0]*scale*SS
    ys = cy - tri[:,:,2]*scale*SS
    for i in order:
        col = tuple(int(x) for x in np.clip(MAT*sh[i], 0, 255))
        d.polygon([(xs[i,0],ys[i,0]),(xs[i,1],ys[i,1]),(xs[i,2],ys[i,2])], fill=col, outline=col)
    return img.resize((RW, RH), Image.LANCZOS)

def caption_overlay(lines, font_size=64, y_center=None):
    """RGBA full-canvas overlay with white text in a dark semi-transparent box."""
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    font = ImageFont.truetype(FONT, font_size)
    pad, gap = 28, 14
    sizes = []
    for t in lines:
        fs = font_size
        while True:
            ft = ImageFont.truetype(FONT, fs)
            b = d.textbbox((0,0), t, font=ft)
            if b[2]-b[0] <= W-2*40-2*pad or fs < 24: break
            fs -= 2
        sizes.append((t, ft, b[2]-b[0], b[3]-b[1], b))
    total = sum(s[3]+2*pad//2 for s in sizes) + gap*(len(sizes)-1) + pad
    y = y_center - total//2
    for t, ft, w, h, b in sizes:
        bw, bh = w+2*pad, h+pad+10
        x0 = (W-bw)//2
        d.rounded_rectangle([x0, y, x0+bw, y+bh], radius=24, fill=(20,20,28,190))
        d.text((W//2 - w//2 - b[0], y + pad//2 + 2 - b[1]), t, font=ft, fill=(255,255,255,255))
        y += bh + gap
    return ov

def captions_for(t, name, mat):
    if t < 4: return [name]
    if t < 8: return ["Free design on Printables", "3D render, not a photo"]
    if t < 12: return [mat]
    return ["No printer? PartRevive prints it", "jdinneen.github.io/partrevive"]

def main(slugs):
    for slug in slugs:
        path, name, mat = JOBS[slug]
        v, f = load(path)
        ext = np.abs(v @ np.eye(3)).max()
        r = np.linalg.norm(v[:,:2],axis=1).max()  # horizontal radius
        half_h = (v[:,2].max()-v[:,2].min())/2
        ev = np.radians(25.0)
        need_h = 2*r*np.sin(ev) + 2*half_h*np.cos(ev)
        scale = 0.88*min(RW/(2*r), RH/need_h)
        cache = {}
        proc = subprocess.Popen([FFMPEG,"-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
            "-r",str(FPS),"-i","-","-c:v","libx264","-pix_fmt","yuv420p","-crf","18","-movflags","+faststart",
            os.path.join(HERE,slug+".mp4")], stdin=subprocess.PIPE)
        ov_cache = {}
        nframes = SECS*FPS
        render_cache = {}
        for i in range(nframes):
            k = i % NF  # 90-frame turntable = 3 s per turn, repeated 5x
            if k not in render_cache:
                render_cache[k] = frame_image(v, f, 2*np.pi*k/NF, scale)
            t = i/FPS
            cap = tuple(captions_for(t, name, mat))
            if cap not in ov_cache:
                ov_cache[cap] = caption_overlay(list(cap), y_center=1500)
            canvas = Image.new("RGBA", (W,H), BG+(255,))
            canvas.paste(render_cache[k], (0,(H-RH)//2))
            canvas = Image.alpha_composite(canvas, ov_cache[cap]).convert("RGB")
            if i == 0: canvas.save(os.path.join(HERE, slug+"-thumb.jpg"), quality=92)
            proc.stdin.write(canvas.tobytes())
        proc.stdin.close(); proc.wait()
    for slug in slugs:
        for fn in (slug+".mp4", slug+"-thumb.jpg"):
            p = os.path.join(HERE, fn)
            print(p, os.path.getsize(p), "bytes")
        out = subprocess.run([FFMPEG,"-i",os.path.join(HERE,slug+".mp4")],capture_output=True,text=True).stderr
        print([l.strip() for l in out.splitlines() if "Duration" in l or "Video:" in l])

if __name__ == "__main__":
    main(sys.argv[1:] or list(JOBS))
