#!/usr/bin/env python3
"""
Builds the BCS NOC Plymouth boot theme.

Inputs : logo PNG (transparent), Orbitron font
Output : theme/ directory  (PNG assets + bcs-noc.script + bcs-noc.plymouth)
         preview_static.png (final frame, for a quick layout check)

All geometry is authored in a 1920x1080 design space; the Plymouth script
scales everything to the real screen at boot.
"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

LOGO_SRC = sys.argv[1]
FONT = sys.argv[2]
OUT = sys.argv[3] if len(sys.argv) > 3 else "theme"
os.makedirs(OUT, exist_ok=True)

W, H = 1920, 1080
CX = 960
random.seed(7)

# ---------------------------------------------------------------- palette
BG_TOP = (7, 13, 28)
BG_BOT = (2, 5, 12)
TRACE = (52, 112, 235)
TRACE_GLOW = (30, 85, 230)
BLUE_HOT = (120, 175, 255)
RED_HOT = (235, 45, 70)

# ---------------------------------------------------------------- layout
LOGO_H = 330
LOGO_CY = 445
TEXT_CY = 705
BAR_Y = 776
BAR_W = 380

# ================================================================ logo
logo = Image.open(LOGO_SRC).convert("RGBA")
logo = logo.crop(logo.getbbox())
lw = round(logo.width * LOGO_H / logo.height)
logo = logo.resize((lw, LOGO_H), Image.LANCZOS)
logo.save(f"{OUT}/logo.png", optimize=True)
LOGO_X0 = CX - lw // 2
LOGO_Y0 = LOGO_CY - LOGO_H // 2
LOGO_X1 = LOGO_X0 + lw
LOGO_Y1 = LOGO_Y0 + LOGO_H

# glow behind logo: blurred silhouette tinted blue
GPAD = 140
a = logo.getchannel("A")
g = Image.new("L", (lw + 2 * GPAD, LOGO_H + 2 * GPAD), 0)
g.paste(a, (GPAD, GPAD))
g = g.filter(ImageFilter.GaussianBlur(38))
g = g.point(lambda v: min(255, int(v * 1.25)))
# keep the counters (enclosed transparent holes in the B) dark: no glow inside them
from scipy import ndimage
solid = np.asarray(a) > 20
lab, _ = ndimage.label(~solid)
border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
holes = np.isin(lab, [l for l in np.unique(lab) if l not in border and l != 0])
holes = ndimage.binary_dilation(holes, iterations=2)
garr = np.asarray(g).copy()
garr[GPAD:GPAD + LOGO_H, GPAD:GPAD + lw][holes] = 0
g = Image.fromarray(garr)
glow = Image.new("RGBA", g.size, (40, 100, 255, 0))
glow.putalpha(g)
glow.save(f"{OUT}/logo_glow.png", optimize=True)

# ================================================================ text
font = ImageFont.truetype(FONT, 92)
font.set_variation_by_name("Black")
TEXT = "BCS NOC"
SPACING = 20
widths = [font.getbbox(ch)[2] - font.getbbox(ch)[0] if ch != " " else 34 for ch in TEXT]
adv = [font.getlength(ch) for ch in TEXT]
tw = int(sum(adv) + SPACING * (len(TEXT) - 1))
asc, desc = font.getmetrics()
TP = 30
txt = Image.new("RGBA", (tw + 2 * TP, asc + desc + 2 * TP), (0, 0, 0, 0))
d = ImageDraw.Draw(txt)
x = TP
for ch, ad in zip(TEXT, adv):
    d.text((x, TP), ch, font=font, fill=(240, 245, 255, 255))
    x += ad + SPACING
txt = txt.crop(txt.getbbox())
txt_full = Image.new("RGBA", (txt.width + 2 * TP, txt.height + 2 * TP), (0, 0, 0, 0))
txt_full.paste(txt, (TP, TP))
# soft blue halo
halo_a = txt_full.getchannel("A").filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * 0.55))
halo = Image.new("RGBA", txt_full.size, (60, 120, 255, 0))
halo.putalpha(halo_a)
text_img = Image.alpha_composite(halo, txt_full)
text_img.save(f"{OUT}/text.png", optimize=True)

# ================================================================ small sprites
def radial(size, stops, name):
    """stops: list of (radius_frac, (r,g,b,a))"""
    n = size
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(xx - (n - 1) / 2, yy - (n - 1) / 2) / (n / 2)
    out = np.zeros((n, n, 4), np.float32)
    for c in range(4):
        rs = [s[0] for s in stops]
        vs = [s[1][c] for s in stops]
        out[..., c] = np.interp(r, rs, vs)
    Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA").save(f"{OUT}/{name}", optimize=True)

radial(40, [(0, (255, 255, 255, 255)), (0.18, (235, 245, 255, 255)), (0.4, (*BLUE_HOT, 150)),
            (1.0, (*TRACE_GLOW, 0))], "pulse_blue.png")
radial(40, [(0, (255, 240, 240, 255)), (0.18, (255, 200, 205, 255)), (0.4, (*RED_HOT, 160)),
            (1.0, (*RED_HOT, 0))], "pulse_red.png")
radial(22, [(0, (200, 225, 255, 200)), (0.5, (*BLUE_HOT, 90)), (1.0, (*TRACE_GLOW, 0))], "tail_blue.png")
radial(22, [(0, (255, 200, 205, 200)), (0.5, (*RED_HOT, 90)), (1.0, (*RED_HOT, 0))], "tail_red.png")
# ring flash where a pulse lands on a pad
n = 64
yy, xx = np.mgrid[0:n, 0:n]
r = np.hypot(xx - (n - 1) / 2, yy - (n - 1) / 2)
ring = np.exp(-((r - 20) ** 2) / (2 * 3.2 ** 2))
fl = np.zeros((n, n, 4), np.float32)
fl[..., 0], fl[..., 1], fl[..., 2] = BLUE_HOT
fl[..., 3] = ring * 230
Image.fromarray(fl.clip(0, 255).astype(np.uint8), "RGBA").save(f"{OUT}/flash.png", optimize=True)

# progress bar: dim track + 1px-wide fill that the script stretches
track = Image.new("RGBA", (BAR_W, 3), (60, 100, 200, 70))
track.save(f"{OUT}/bar_track.png")
fill = Image.new("RGBA", (4, 3), (*BLUE_HOT, 255))
fill.save(f"{OUT}/bar_fill.png")

# ================================================================ traces
SQ2 = math.sqrt(2)

def bus_horizontal(side, n, y_top, y_bot, x_start, bend0, step_rise, end_range):
    """Fan-out bus leaving the logo to the left (side=-1) or right (side=+1)."""
    traces = []
    sp = (y_bot - y_top) / (n - 1)
    delta = sp * (SQ2 - 1)
    half = n / 2
    for i in range(n):
        y = y_top + i * sp
        upper = i < half
        k = i if upper else (n - 1 - i)            # 0 = outermost
        kin = (half - 1 - k)                        # rank from the middle
        rise = (kin * 0 + (half - k)) * step_rise
        bend_x = x_start + side * (bend0 + k * delta)
        dy = -rise if upper else rise
        p0 = (x_start, y)
        p1 = (bend_x, y)
        p2 = (bend_x + side * rise, y + dy)
        ex = random.uniform(*end_range)
        p3 = (ex if side < 0 else W - ex, y + dy)
        traces.append([p0, p1, p2, p3])
    return traces

def bus_vertical(n, x_left, x_right, y_start, bend0, step_run, end_range):
    """Fan-out bus leaving the top of the logo, splitting left and right."""
    traces = []
    sp = (x_right - x_left) / (n - 1)
    delta = sp * (SQ2 - 1)
    half = n / 2
    for i in range(n):
        x = x_left + i * sp
        left = i < half
        k = i if left else (n - 1 - i)
        run = (half - k) * step_run
        bend_y = y_start - (bend0 + k * delta)
        dx = -run if left else run
        p0 = (x, y_start)
        p1 = (x, bend_y)
        p2 = (x + dx, bend_y - run)
        p3 = (x + dx, random.uniform(*end_range))
        traces.append([p0, p1, p2, p3])
    return traces

traces = []
traces += bus_horizontal(-1, 8, LOGO_Y0 + 42, LOGO_Y1 - 42, LOGO_X0 - 14, 38, 50, (120, 470))
traces += bus_horizontal(+1, 8, LOGO_Y0 + 42, LOGO_Y1 - 42, LOGO_X1 + 14, 38, 50, (120, 470))
traces += bus_vertical(6, CX - 120, CX + 120, LOGO_Y0 - 14, 26, 38, (48, 105))

# second-stage bends on a few long horizontal traces so the corners fill in
def add_tail(tr, side_x, up):
    p = tr[-1]
    q = tr[-2]
    if abs(p[0] - q[0]) < 260:
        return tr
    cut = q[0] + (p[0] - q[0]) * random.uniform(0.45, 0.7)
    run = random.uniform(70, 150)
    sx = 1 if p[0] > q[0] else -1
    dy = -run if up else run
    a = (cut, p[1])
    b = (cut + sx * run, p[1] + dy)
    end_y = b[1] + (-1 if up else 1) * random.uniform(40, 120)
    end_y = max(40, min(H - 40, end_y))
    return tr[:-1] + [a, b, (b[0], end_y)]

for idx in (0, 7, 8, 15):
    up = idx in (0, 8)
    traces[idx] = add_tail(traces[idx], 0, up)

# ---------------------------------------------------------------- render
SS = 4  # supersample
PAD = 16

def poly_len(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))

def nearest_param(px, py, pts):
    """arc-length parameter of nearest point on polyline for arrays px,py"""
    best_d = np.full(px.shape, np.inf)
    best_s = np.zeros(px.shape)
    acc = 0.0
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy
        L = math.sqrt(L2)
        t = ((px - ax) * vx + (py - ay) * vy) / L2
        t = np.clip(t, 0, 1)
        qx, qy = ax + t * vx, ay + t * vy
        dd = (px - qx) ** 2 + (py - qy) ** 2
        m = dd < best_d
        best_d[m] = dd[m]
        best_s[m] = acc + t[m] * L
        acc += L
    return best_s

CHUNK = 40
trace_meta = []
chunk_id = 0
static = Image.new("RGBA", (W, H), (0, 0, 0, 0))

for ti, pts in enumerate(traces):
    pts = [(round(x, 1), round(y, 1)) for x, y in pts]
    traces[ti] = pts
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0 = int(math.floor(min(xs))) - PAD; y0 = int(math.floor(min(ys))) - PAD
    x1 = int(math.ceil(max(xs))) + PAD; y1 = int(math.ceil(max(ys))) + PAD
    cw, ch = x1 - x0, y1 - y0

    def S(p):  # to supersampled local coords
        return ((p[0] - x0) * SS, (p[1] - y0) * SS)

    core = Image.new("L", (cw * SS, ch * SS), 0)
    dc = ImageDraw.Draw(core)
    lp = [S(p) for p in pts]
    dc.line(lp, fill=255, width=int(2.6 * SS), joint="curve")
    # start pin (small rectangle at the logo edge)
    sx, sy = S(pts[0])
    horiz = abs(pts[1][1] - pts[0][1]) < 0.5
    if horiz:
        dc.rectangle([sx - 5 * SS, sy - 3.5 * SS, sx + 5 * SS, sy + 3.5 * SS], fill=255)
    else:
        dc.rectangle([sx - 3.5 * SS, sy - 5 * SS, sx + 3.5 * SS, sy + 5 * SS], fill=255)
    # end pad: via ring
    ex, ey = S(pts[-1])
    R = 7.5 * SS
    dc.ellipse([ex - R, ey - R, ex + R, ey + R], fill=255)
    hole = Image.new("L", core.size, 0)
    dh = ImageDraw.Draw(hole)
    r2 = 3.0 * SS
    dh.ellipse([ex - r2, ey - r2, ex + r2, ey + r2], fill=255)
    core = Image.fromarray(np.clip(np.asarray(core, np.int16) - np.asarray(hole, np.int16), 0, 255).astype(np.uint8))
    core = core.resize((cw, ch), Image.LANCZOS)

    glow_a = core.filter(ImageFilter.GaussianBlur(5)).point(lambda v: int(min(255, v * 0.9)))
    arr = np.zeros((ch, cw, 4), np.float32)
    ca = np.asarray(core, np.float32) / 255 * 0.85
    ga = np.asarray(glow_a, np.float32) / 255 * 0.45
    # composite core over glow
    out_a = ca + ga * (1 - ca)
    for c in range(3):
        col = (TRACE[c] * ca + TRACE_GLOW[c] * ga * (1 - ca)) / np.maximum(out_a, 1e-6)
        arr[..., c] = col
    arr[..., 3] = out_a * 255
    img = arr.clip(0, 255).astype(np.uint8)
    full = Image.fromarray(img, "RGBA")
    static.alpha_composite(full, (x0, y0))

    # split into arc-length chunks so the trace "draws" outward from the logo
    L = poly_len(pts)
    yy, xx = np.mgrid[0:ch, 0:cw]
    s = nearest_param(xx + x0 + 0.5, yy + y0 + 0.5, pts)
    nchunks = max(1, math.ceil(L / CHUNK))
    edges = np.linspace(0, L, nchunks + 1)
    chunks = []
    for ci in range(nchunks):
        lo, hi = edges[ci], edges[ci + 1]
        m = (s >= lo) & ((s < hi) if ci < nchunks - 1 else (s <= hi + 1))
        part = img.copy()
        part[~m, 3] = 0
        if part[..., 3].max() == 0:
            continue
        pim = Image.fromarray(part, "RGBA")
        bb = pim.getbbox()
        pim = pim.crop(bb)
        fn = f"c{chunk_id:03d}.png"
        pim.save(f"{OUT}/{fn}", optimize=True)
        chunks.append((fn, x0 + bb[0], y0 + bb[1], lo, hi))
        chunk_id += 1
    trace_meta.append(dict(pts=pts, L=L, chunks=chunks))

# staggered launch times: inner traces first, rippling outward
for i, tm in enumerate(trace_meta):
    tm["t0"] = 0.55 + random.uniform(0, 0.55)
    tm["v"] = random.uniform(820, 1050)

# ================================================================ background texture
# faint, static circuit maze in the outer area for depth (never animated)
bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
db = ImageDraw.Draw(bg)
rng = random.Random(3)
def in_keepout(x, y):
    return (LOGO_X0 - 60 < x < LOGO_X1 + 60 and LOGO_Y0 - 340 < y < BAR_Y + 60) or \
           (CX - 340 < x < CX + 340 and 620 < y < 830)
GRID = 24
for _ in range(240):
    x = rng.randrange(1, W // GRID) * GRID
    y = rng.randrange(1, H // GRID) * GRID
    if in_keepout(x, y):
        continue
    pts_ = [(x, y)]
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]
    dx, dy = rng.choice(dirs[:4])
    for _s in range(rng.randint(2, 4)):
        L_ = rng.randint(2, 7) * GRID
        nx, ny = pts_[-1][0] + dx * L_, pts_[-1][1] + dy * L_
        if in_keepout(nx, ny) or not (10 < nx < W - 10 and 10 < ny < H - 10):
            break
        pts_.append((nx, ny))
        # turn 45 degrees
        opts = [d_ for d_ in dirs if d_ != (dx, dy) and d_ != (-dx, -dy) and abs(d_[0] - dx) + abs(d_[1] - dy) <= 2]
        dx, dy = rng.choice(opts)
    if len(pts_) < 2:
        continue
    db.line(pts_, fill=(60, 100, 190, 34), width=2, joint="curve")
    ex, ey = pts_[-1]
    db.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], outline=(70, 115, 210, 50), width=2)
# dot grid
for gx in range(GRID, W, GRID * 2):
    for gy in range(GRID, H, GRID * 2):
        if not in_keepout(gx, gy):
            db.point((gx, gy), fill=(80, 120, 210, 40))
bg.save(f"{OUT}/bg_circuit.png", optimize=True)

# ================================================================ static preview
prev = Image.new("RGBA", (W, H))
pa = np.zeros((H, W, 4), np.uint8)
for yv in range(H):
    t = yv / (H - 1)
    pa[yv, :, :3] = [int(BG_TOP[c] * (1 - t) + BG_BOT[c] * t) for c in range(3)]
pa[..., 3] = 255
prev = Image.fromarray(pa, "RGBA")
prev.alpha_composite(bg)
prev.alpha_composite(static)
prev.alpha_composite(glow, (LOGO_X0 - GPAD, LOGO_Y0 - GPAD))
prev.alpha_composite(logo, (LOGO_X0, LOGO_Y0))
prev.alpha_composite(text_img, (CX - text_img.width // 2, TEXT_CY - text_img.height // 2))
prev.convert("RGB").save(os.path.join(os.path.dirname(OUT) or ".", "wallpaper.jpg"), quality=90)
prev.alpha_composite(track, (CX - BAR_W // 2, BAR_Y))
prev.alpha_composite(fill.resize((int(BAR_W * 0.6), 3)), (CX - BAR_W // 2, BAR_Y))
prev.convert("RGB").save(os.path.join(os.path.dirname(OUT) or ".", "preview_static.png"))

# ================================================================ script data
def f(v):
    return f"{v:.1f}"

lines = []
lines.append(f"global.NT = {len(trace_meta)};")
for i, tm in enumerate(trace_meta):
    p = f"global.tr[{i}]"
    lines.append(f"{p}.t0 = {tm['t0']:.3f}; {p}.v = {tm['v']:.0f}; {p}.L = {f(tm['L'])}; {p}.np = {len(tm['pts'])}; {p}.nc = {len(tm['chunks'])};")
    acc = 0.0
    for j, (x, y) in enumerate(tm["pts"]):
        if j > 0:
            acc += math.dist(tm["pts"][j - 1], (x, y))
        lines.append(f"{p}.px[{j}] = {f(x)}; {p}.py[{j}] = {f(y)}; {p}.ps[{j}] = {f(acc)};")
    for j, (fn, cx_, cy_, lo, hi) in enumerate(tm["chunks"]):
        lines.append(f'{p}.cf[{j}] = "{fn}"; {p}.cx[{j}] = {cx_}; {p}.cy[{j}] = {cy_}; {p}.ca[{j}] = {f(lo)}; {p}.cb[{j}] = {f(hi)};')

layout = dict(
    LOGO_X=LOGO_X0, LOGO_Y=LOGO_Y0,
    GLOW_X=LOGO_X0 - GPAD, GLOW_Y=LOGO_Y0 - GPAD,
    TEXT_X=CX - text_img.width // 2, TEXT_Y=TEXT_CY - text_img.height // 2,
    BAR_X=CX - BAR_W // 2, BAR_Y=BAR_Y, BAR_W=BAR_W,
)
for k, v in layout.items():
    lines.append(f"global.{k} = {v};")

with open(os.path.join(os.path.dirname(OUT) or ".", "trace_data.script"), "w") as fh:
    fh.write("\n".join(lines) + "\n")

print("traces:", len(trace_meta), "chunks:", chunk_id)
