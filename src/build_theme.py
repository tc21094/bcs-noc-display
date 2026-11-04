#!/usr/bin/env python3
"""
Builds the BCS NOC Plymouth boot theme.

usage: build_theme.py logo.png Orbitron.ttf OUTDIR

Writes OUTDIR/        1x artwork (1920x1080 screens)
       OUTDIR/x2/     2x artwork (4K screens) - loaded directly, never upscaled at boot
       trace_data.script, preview_static.png   (next to OUTDIR)

Everything is drawn once at 2x (3840x2160) and the 1x set is an exact 2:1
downscale, so both sets line up with the same design-space coordinates.
"""
import json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

LOGO_SRC, FONT, OUT = sys.argv[1:4]
BASE = os.path.dirname(os.path.abspath(OUT))
os.makedirs(f"{OUT}/x2", exist_ok=True)

K = 2                    # render scale
W, H = 1920, 1080        # design space
CX = 960

BG_TOP = (7, 13, 28)
BG_BOT = (2, 5, 12)
TRACE = (52, 112, 235)
TRACE_GLOW = (30, 85, 230)
BLUE_HOT = (120, 175, 255)
RED_HOT = (235, 45, 70)

LOGO_H = 330
LOGO_CY = 445
TEXT_CY = 705
BAR_Y = 776
BAR_W = 380


def save_pair(img, name):
    """img is 2x; save it to x2/ and a half-size copy to the 1x set."""
    if img.width % 2 or img.height % 2:
        pad = Image.new("RGBA", (img.width + img.width % 2, img.height + img.height % 2), (0, 0, 0, 0))
        pad.paste(img, (0, 0))
        img = pad
    img.save(f"{OUT}/x2/{name}", optimize=True)
    img.resize((img.width // 2, img.height // 2), Image.LANCZOS).save(f"{OUT}/{name}", optimize=True)
    return img


# ================================================================ logo + glow
src = Image.open(LOGO_SRC).convert("RGBA")
src = src.crop(src.getbbox())
lw = round(src.width * LOGO_H / src.height)               # design width
logo = src.resize((lw * K, LOGO_H * K), Image.LANCZOS)
save_pair(logo, "logo.png")
LOGO_X0 = CX - lw // 2
LOGO_Y0 = LOGO_CY - LOGO_H // 2
LOGO_X1 = LOGO_X0 + lw
LOGO_Y1 = LOGO_Y0 + LOGO_H

GPAD = 140
a = logo.getchannel("A")
g = Image.new("L", ((lw + 2 * GPAD) * K, (LOGO_H + 2 * GPAD) * K), 0)
g.paste(a, (GPAD * K, GPAD * K))
g = g.filter(ImageFilter.GaussianBlur(38 * K)).point(lambda v: min(255, int(v * 1.25)))
solid = np.asarray(a) > 20
lab, _ = ndimage.label(~solid)
border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
holes = np.isin(lab, [l for l in np.unique(lab) if l not in border and l != 0])
holes = ndimage.binary_dilation(holes, iterations=2 * K)
garr = np.asarray(g).copy()
garr[GPAD * K:GPAD * K + LOGO_H * K, GPAD * K:GPAD * K + lw * K][holes] = 0
glow = Image.new("RGBA", g.size, (40, 100, 255, 0))
glow.putalpha(Image.fromarray(garr))
save_pair(glow, "logo_glow.png")

# ================================================================ text
font = ImageFont.truetype(FONT, 92 * K)
font.set_variation_by_name("Black")
TEXT, SPACING = "BCS NOC", 20 * K
adv = [font.getlength(ch) for ch in TEXT]
asc, desc = font.getmetrics()
TP = 30 * K
t = Image.new("RGBA", (int(sum(adv) + SPACING * (len(TEXT) - 1)) + 2 * TP, asc + desc + 2 * TP), (0, 0, 0, 0))
dt = ImageDraw.Draw(t)
x = TP
for ch, ad in zip(TEXT, adv):
    dt.text((x, TP), ch, font=font, fill=(240, 245, 255, 255))
    x += ad + SPACING
t = t.crop(t.getbbox())
tw = t.width + 2 * TP; th = t.height + 2 * TP
tw += tw % 2; th += th % 2
tf = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
tf.paste(t, (TP, TP))
halo = Image.new("RGBA", tf.size, (60, 120, 255, 0))
halo.putalpha(tf.getchannel("A").filter(ImageFilter.GaussianBlur(12 * K)).point(lambda v: int(v * 0.55)))
text_img = save_pair(Image.alpha_composite(halo, tf), "text.png")
TEXT_W, TEXT_H = text_img.width // K, text_img.height // K

# "BCS" over "TECHNOLOGY DEPARTMENT" for the blanket; the first line matches BCS NOC exactly
def spaced(txt, fnt, sp):
    adv_ = [fnt.getlength(c_) for c_ in txt]
    w_ = int(sum(adv_) + sp * (len(txt) - 1))
    im_ = Image.new("RGBA", (w_ + 4 * K, fnt.getmetrics()[0] + fnt.getmetrics()[1] + 4 * K), (0, 0, 0, 0))
    d_ = ImageDraw.Draw(im_)
    x_ = 2 * K
    for c_, a_ in zip(txt, adv_):
        d_.text((x_, 2 * K), c_, font=fnt, fill=(240, 245, 255, 255)); x_ += a_ + sp
    return im_.crop(im_.getbbox())
sub_font = ImageFont.truetype(FONT, 38 * K)
sub_font.set_variation_by_name("Bold")
l1 = spaced("BCS", font, SPACING)
l2 = spaced("TECHNOLOGY DEPARTMENT", sub_font, 9 * K)
GAP2 = 26 * K
w2 = max(l1.width, l2.width) + 2 * TP; h2 = l1.height + GAP2 + l2.height + 2 * TP
w2 += w2 % 2; h2 += h2 % 2
t2 = Image.new("RGBA", (w2, h2), (0, 0, 0, 0))
t2.paste(l1, ((w2 - l1.width) // 2, TP))
t2.paste(l2, ((w2 - l2.width) // 2, TP + l1.height + GAP2))
halo2 = Image.new("RGBA", t2.size, (60, 120, 255, 0))
halo2.putalpha(t2.getchannel("A").filter(ImageFilter.GaussianBlur(12 * K)).point(lambda v: int(v * 0.55)))
text2_img = save_pair(Image.alpha_composite(halo2, t2), "text_dept.png")
TEXT2_W, TEXT2_H = text2_img.width // K, text2_img.height // K

# "HAPPY HOLIDAYS" for the holiday blanket (warm gold, same lettering style)
def spaced_col(txt, fnt, sp, col):
    im_ = spaced(txt, fnt, sp)
    a_ = im_.getchannel("A")
    im_ = Image.new("RGBA", im_.size, col + (0,)); im_.putalpha(a_)
    return im_
gfont = ImageFont.truetype(FONT, 34 * K)
gfont.set_variation_by_name("Bold")
gl = spaced_col("HAPPY HOLIDAYS", gfont, 12 * K, (255, 214, 130))
gw = gl.width + 2 * TP; gh = gl.height + 2 * TP
gw += gw % 2; gh += gh % 2
g3 = Image.new("RGBA", (gw, gh), (0, 0, 0, 0)); g3.paste(gl, (TP, TP))
gh3 = Image.new("RGBA", g3.size, (255, 170, 60, 0))
gh3.putalpha(g3.getchannel("A").filter(ImageFilter.GaussianBlur(10 * K)).point(lambda v: int(v * 0.6)))
save_pair(Image.alpha_composite(gh3, g3), "text_greet.png")

# ================================================================ small sprites
def radial(size, stops, name):
    n = size * K
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(xx - (n - 1) / 2, yy - (n - 1) / 2) / (n / 2)
    out = np.zeros((n, n, 4), np.float32)
    for c in range(4):
        out[..., c] = np.interp(r, [s_[0] for s_ in stops], [s_[1][c] for s_ in stops])
    save_pair(Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA"), name)

radial(40, [(0, (255, 255, 255, 255)), (0.18, (235, 245, 255, 255)), (0.4, (*BLUE_HOT, 150)), (1.0, (*TRACE_GLOW, 0))], "pulse_blue.png")
radial(40, [(0, (255, 240, 240, 255)), (0.18, (255, 200, 205, 255)), (0.4, (*RED_HOT, 160)), (1.0, (*RED_HOT, 0))], "pulse_red.png")
radial(22, [(0, (200, 225, 255, 200)), (0.5, (*BLUE_HOT, 90)), (1.0, (*TRACE_GLOW, 0))], "tail_blue.png")
radial(22, [(0, (255, 200, 205, 200)), (0.5, (*RED_HOT, 90)), (1.0, (*RED_HOT, 0))], "tail_red.png")

n = 64 * K
yy, xx = np.mgrid[0:n, 0:n]
r = np.hypot(xx - (n - 1) / 2, yy - (n - 1) / 2)
ring = np.exp(-((r - 20 * K) ** 2) / (2 * (3.2 * K) ** 2))
fl = np.zeros((n, n, 4), np.float32)
fl[..., 0], fl[..., 1], fl[..., 2] = BLUE_HOT
fl[..., 3] = ring * 230
save_pair(Image.fromarray(fl.clip(0, 255).astype(np.uint8), "RGBA"), "flash.png")

save_pair(Image.new("RGBA", (BAR_W * K, 3 * K), (60, 100, 200, 70)), "bar_track.png")
save_pair(Image.new("RGBA", (4 * K, 3 * K), (*BLUE_HOT, 255)), "bar_fill.png")

# ================================================================ trace geometry
random.seed(7)
SQ2 = math.sqrt(2)

def bus_horizontal(side, n, y_top, y_bot, x_start, bend0, step_rise, end_range):
    out = []
    sp = (y_bot - y_top) / (n - 1)
    delta = sp * (SQ2 - 1)
    half = n / 2
    for i in range(n):
        y = y_top + i * sp
        upper = i < half
        k = i if upper else (n - 1 - i)
        rise = (half - k) * step_rise
        bend_x = x_start + side * (bend0 + k * delta)
        dy = -rise if upper else rise
        ex = random.uniform(*end_range)
        out.append([(x_start, y), (bend_x, y), (bend_x + side * rise, y + dy), (ex if side < 0 else W - ex, y + dy)])
    return out

def bus_vertical(n, x_left, x_right, y_start, bend0, step_run, end_range):
    out = []
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
        out.append([(x, y_start), (x, bend_y), (x + dx, bend_y - run), (x + dx, random.uniform(*end_range))])
    return out

traces = []
traces += bus_horizontal(-1, 8, LOGO_Y0 + 42, LOGO_Y1 - 42, LOGO_X0 - 14, 38, 50, (120, 470))
traces += bus_horizontal(+1, 8, LOGO_Y0 + 42, LOGO_Y1 - 42, LOGO_X1 + 14, 38, 50, (120, 470))
traces += bus_vertical(6, CX - 120, CX + 120, LOGO_Y0 - 14, 26, 38, (48, 105))

def add_tail(tr, up):
    p, q = tr[-1], tr[-2]
    if abs(p[0] - q[0]) < 260:
        return tr
    cut = q[0] + (p[0] - q[0]) * random.uniform(0.45, 0.7)
    run = random.uniform(70, 150)
    sx = 1 if p[0] > q[0] else -1
    dy = -run if up else run
    a_ = (cut, p[1])
    b_ = (cut + sx * run, p[1] + dy)
    end_y = b_[1] + (-1 if up else 1) * random.uniform(40, 120)
    end_y = max(40, min(H - 40, end_y))
    return tr[:-1] + [a_, b_, (b_[0], end_y)]

for idx in (0, 7, 8, 15):
    traces[idx] = add_tail(traces[idx], idx in (0, 8))
traces = [[(round(x_, 1), round(y_, 1)) for x_, y_ in tr] for tr in traces]

# ================================================================ trace rendering (2x) + chunks
SS = 2          # extra supersampling on top of 2x
PAD = 16
CHUNK = 40

def poly_len(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))

def nearest_param(px, py, pts):
    best_d = np.full(px.shape, np.inf)
    best_s = np.zeros(px.shape)
    acc = 0.0
    for i in range(len(pts) - 1):
        ax, ay = pts[i]; bx, by = pts[i + 1]
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy; L = math.sqrt(L2)
        tt = np.clip(((px - ax) * vx + (py - ay) * vy) / L2, 0, 1)
        dd = (px - (ax + tt * vx)) ** 2 + (py - (ay + tt * vy)) ** 2
        m = dd < best_d
        best_d[m] = dd[m]; best_s[m] = acc + tt[m] * L
        acc += L
    return best_s

static_traces = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0))
trace_meta = []
chunk_id = 0
for pts in traces:
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0 = int(math.floor(min(xs))) - PAD; y0 = int(math.floor(min(ys))) - PAD
    x1 = int(math.ceil(max(xs))) + PAD; y1 = int(math.ceil(max(ys))) + PAD
    cw, ch = (x1 - x0) * K, (y1 - y0) * K
    u = K * SS
    def Q(p):
        return ((p[0] - x0) * u, (p[1] - y0) * u)
    core = Image.new("L", (cw * SS, ch * SS), 0)
    dc = ImageDraw.Draw(core)
    dc.line([Q(p) for p in pts], fill=255, width=int(2.6 * u), joint="curve")
    sx, sy = Q(pts[0])
    if abs(pts[1][1] - pts[0][1]) < 0.5:
        dc.rectangle([sx - 5 * u, sy - 3.5 * u, sx + 5 * u, sy + 3.5 * u], fill=255)
    else:
        dc.rectangle([sx - 3.5 * u, sy - 5 * u, sx + 3.5 * u, sy + 5 * u], fill=255)
    ex, ey = Q(pts[-1])
    dc.ellipse([ex - 7.5 * u, ey - 7.5 * u, ex + 7.5 * u, ey + 7.5 * u], fill=255)
    dc.ellipse([ex - 3 * u, ey - 3 * u, ex + 3 * u, ey + 3 * u], fill=0)
    core = core.resize((cw, ch), Image.LANCZOS)
    glow_a = core.filter(ImageFilter.GaussianBlur(5 * K)).point(lambda v: int(min(255, v * 0.9)))
    ca = np.asarray(core, np.float32) / 255 * 0.85
    ga = np.asarray(glow_a, np.float32) / 255 * 0.45
    oa = ca + ga * (1 - ca)
    arr = np.zeros((ch, cw, 4), np.float32)
    for c in range(3):
        arr[..., c] = (TRACE[c] * ca + TRACE_GLOW[c] * ga * (1 - ca)) / np.maximum(oa, 1e-6)
    arr[..., 3] = oa * 255
    img = arr.clip(0, 255).astype(np.uint8)
    static_traces.alpha_composite(Image.fromarray(img, "RGBA"), (x0 * K, y0 * K))

    L = poly_len(pts)
    gy, gx = np.mgrid[0:ch, 0:cw]
    s = nearest_param(x0 + (gx + 0.5) / K, y0 + (gy + 0.5) / K, pts)
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
        bx0, by0, bx1, by1 = pim.getbbox()
        bx0 -= bx0 % 2; by0 -= by0 % 2           # even-aligned so the 1x copy lines up exactly
        bx1 += bx1 % 2; by1 += by1 % 2
        fn = f"c{chunk_id:03d}.png"
        save_pair(pim.crop((bx0, by0, bx1, by1)), fn)
        chunks.append((fn, x0 + bx0 // K, y0 + by0 // K, lo, hi))
        chunk_id += 1
    trace_meta.append(dict(pts=pts, L=L, chunks=chunks))

for tm in trace_meta:
    tm["t0"] = 0.55 + random.uniform(0, 0.55)
    tm["v"] = random.uniform(820, 1050)

# ================================================================ background maze
# opacity is baked in so the splash never has to fade a full-screen layer
bg = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0))
db = ImageDraw.Draw(bg)
maze_lines, maze_vias, maze_dots = [], [], []
rng = random.Random(3)
def in_keepout(x, y):
    return (LOGO_X0 - 60 < x < LOGO_X1 + 60 and LOGO_Y0 - 340 < y < BAR_Y + 60) or \
           (CX - 340 < x < CX + 340 and 620 < y < 830)
GRID = 24
dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]
for _ in range(240):
    x = rng.randrange(1, W // GRID) * GRID
    y = rng.randrange(1, H // GRID) * GRID
    if in_keepout(x, y):
        continue
    pts = [(x, y)]
    dx, dy = rng.choice(dirs[:4])
    for _s in range(rng.randint(2, 4)):
        L_ = rng.randint(2, 7) * GRID
        nx, ny = pts[-1][0] + dx * L_, pts[-1][1] + dy * L_
        if in_keepout(nx, ny) or not (10 < nx < W - 10 and 10 < ny < H - 10):
            break
        pts.append((nx, ny))
        opts = [o for o in dirs if o != (dx, dy) and o != (-dx, -dy) and abs(o[0] - dx) + abs(o[1] - dy) <= 2]
        dx, dy = rng.choice(opts)
    if len(pts) < 2:
        continue
    db.line([(p[0] * K, p[1] * K) for p in pts], fill=(60, 100, 190, 34), width=2 * K, joint="curve")
    maze_lines.append(pts); maze_vias.append(pts[-1])
    ex, ey = pts[-1][0] * K, pts[-1][1] * K
    db.ellipse([ex - 4 * K, ey - 4 * K, ex + 4 * K, ey + 4 * K], outline=(70, 115, 210, 50), width=2 * K)
for gx_ in range(GRID, W, GRID * 2):
    for gy_ in range(GRID, H, GRID * 2):
        if not in_keepout(gx_, gy_):
            db.rectangle([gx_ * K, gy_ * K, gx_ * K + K - 1, gy_ * K + K - 1], fill=(80, 120, 210, 40))
            maze_dots.append((gx_, gy_))
bg.putalpha(bg.getchannel("A").point(lambda v: int(v * 0.9)))
save_pair(bg, "bg_circuit.png")

# ================================================================ static preview (1x)
yy = np.linspace(0, 1, H)[:, None]
pa = np.zeros((H, W, 4), np.uint8)
for c in range(3):
    pa[..., c] = (BG_TOP[c] * (1 - yy) + BG_BOT[c] * yy).astype(np.uint8)
pa[..., 3] = 255
prev = Image.fromarray(pa, "RGBA")
half = lambda im: im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
prev.alpha_composite(half(bg))
prev.alpha_composite(half(static_traces))
prev.alpha_composite(half(glow).point(lambda v: v), (LOGO_X0 - GPAD, LOGO_Y0 - GPAD))
prev.alpha_composite(half(logo), (LOGO_X0, LOGO_Y0))
TEXT_X = CX - TEXT_W // 2
TEXT_Y = TEXT_CY - TEXT_H // 2
prev.alpha_composite(half(text_img), (TEXT_X, TEXT_Y))
prev.convert("RGB").save(os.path.join(BASE, "preview_static.png"))
prev2 = Image.fromarray(pa, "RGBA")
prev2.alpha_composite(half(bg)); prev2.alpha_composite(half(static_traces))
prev2.alpha_composite(half(glow), (LOGO_X0 - GPAD, LOGO_Y0 - GPAD)); prev2.alpha_composite(half(logo), (LOGO_X0, LOGO_Y0))
prev2.alpha_composite(half(text2_img), (CX - text2_img.width // 4, TEXT_Y))
prev2.convert("RGB").save(os.path.join(BASE, "preview_blanket.png"))

# ================================================================ script data
def f(v):
    return f"{v:.1f}"

lines = [f"global.NT = {len(trace_meta)};"]
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
layout = dict(LOGO_X=LOGO_X0, LOGO_Y=LOGO_Y0, GLOW_X=LOGO_X0 - GPAD, GLOW_Y=LOGO_Y0 - GPAD,
              TEXT_X=TEXT_X, TEXT_Y=TEXT_Y, BAR_X=CX - BAR_W // 2, BAR_Y=BAR_Y, BAR_W=BAR_W)
for k_, v_ in layout.items():
    lines.append(f"global.{k_} = {v_};")
with open(os.path.join(BASE, "trace_data.script"), "w") as fh:
    fh.write("\n".join(lines) + "\n")
# geometry for the dashboard interlude (same layout as the boot splash)
def cum(pts):
    out, acc = [0.0], 0.0
    for i in range(1, len(pts)):
        acc += math.dist(pts[i - 1], pts[i]); out.append(round(acc, 1))
    return out
inter = dict(
    traces=[dict(p=tm["pts"], s=cum(tm["pts"]), L=round(tm["L"], 1), t0=round(tm["t0"], 3), v=round(tm["v"])) for tm in trace_meta],
    maze=maze_lines, vias=maze_vias, dots=maze_dots,
    logo=[LOGO_X0, LOGO_Y0, lw, LOGO_H], glow=[LOGO_X0 - GPAD, LOGO_Y0 - GPAD, lw + 2 * GPAD, LOGO_H + 2 * GPAD],
    text=[TEXT_X, TEXT_Y, TEXT_W, TEXT_H],
    text2=[CX - TEXT2_W // 2, TEXT_Y, TEXT2_W, TEXT2_H])
with open(os.path.join(BASE, "interlude_data.json"), "w") as fh:
    json.dump(inter, fh, separators=(",", ":"))
print("traces:", len(trace_meta), "chunks:", chunk_id)
