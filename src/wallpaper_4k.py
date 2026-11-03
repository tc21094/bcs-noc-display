#!/usr/bin/env python3
"""
Renders the BCS NOC boot-splash artwork as a native 3840x2160 wallpaper.
Same layout as the boot splash (same seeds and geometry as build_theme.py),
drawn at 2x so every line, glow and letter is sharp at 4K.

usage: wallpaper_4k.py logo.png Orbitron.ttf out.png [--pulses]
"""
import math, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

LOGO_SRC, FONT, OUT = sys.argv[1:4]
PULSES = "--pulses" in sys.argv

K = 2                       # 1920x1080 design -> 3840x2160
W, H = 1920, 1080
CX = 960
WK, HK = W * K, H * K

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

# ------------------------------------------------------------ logo geometry (design units)
logo_src = Image.open(LOGO_SRC).convert("RGBA")
logo_src = logo_src.crop(logo_src.getbbox())
lw = round(logo_src.width * LOGO_H / logo_src.height)
LOGO_X0 = CX - lw // 2
LOGO_Y0 = LOGO_CY - LOGO_H // 2
LOGO_X1 = LOGO_X0 + lw
LOGO_Y1 = LOGO_Y0 + LOGO_H

# ------------------------------------------------------------ trace geometry (identical to build_theme.py)
random.seed(7)
SQ2 = math.sqrt(2)

def bus_horizontal(side, n, y_top, y_bot, x_start, bend0, step_rise, end_range):
    traces = []
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
        traces.append([(x_start, y), (bend_x, y), (bend_x + side * rise, y + dy),
                       (ex if side < 0 else W - ex, y + dy)])
    return traces

def bus_vertical(n, x_left, x_right, y_start, bend0, step_run, end_range):
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
        traces.append([(x, y_start), (x, bend_y), (x + dx, bend_y - run),
                       (x + dx, random.uniform(*end_range))])
    return traces

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
    a = (cut, p[1])
    b = (cut + sx * run, p[1] + dy)
    end_y = b[1] + (-1 if up else 1) * random.uniform(40, 120)
    end_y = max(40, min(H - 40, end_y))
    return tr[:-1] + [a, b, (b[0], end_y)]

for idx in (0, 7, 8, 15):
    traces[idx] = add_tail(traces[idx], idx in (0, 8))
traces = [[(round(x, 1), round(y, 1)) for x, y in t] for t in traces]

def P(p):
    return (p[0] * K, p[1] * K)

# ------------------------------------------------------------ background gradient
yy = np.linspace(0, 1, HK)[:, None]
base = np.zeros((HK, WK, 4), np.uint8)
for c in range(3):
    base[..., c] = (BG_TOP[c] * (1 - yy) + BG_BOT[c] * yy).astype(np.uint8)
base[..., 3] = 255
img = Image.fromarray(base, "RGBA")

# subtle vignette lift behind the logo
vy, vx = np.mgrid[0:HK, 0:WK]
d = np.hypot((vx - CX * K) / (WK * 0.5), (vy - (LOGO_CY + 60) * K) / (HK * 0.55))
lift = np.clip(1 - d, 0, 1) ** 2
vig = np.zeros((HK, WK, 4), np.uint8)
vig[..., 0], vig[..., 1], vig[..., 2] = 25, 55, 130
vig[..., 3] = (lift * 38).astype(np.uint8)
img.alpha_composite(Image.fromarray(vig, "RGBA"))

# ------------------------------------------------------------ faint background maze (same rng as splash)
bg = Image.new("RGBA", (WK, HK), (0, 0, 0, 0))
db = ImageDraw.Draw(bg)
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
        L = rng.randint(2, 7) * GRID
        nx, ny = pts[-1][0] + dx * L, pts[-1][1] + dy * L
        if in_keepout(nx, ny) or not (10 < nx < W - 10 and 10 < ny < H - 10):
            break
        pts.append((nx, ny))
        opts = [o for o in dirs if o != (dx, dy) and o != (-dx, -dy) and abs(o[0] - dx) + abs(o[1] - dy) <= 2]
        dx, dy = rng.choice(opts)
    if len(pts) < 2:
        continue
    db.line([P(p) for p in pts], fill=(60, 100, 190, 34), width=2 * K, joint="curve")
    ex, ey = P(pts[-1])
    db.ellipse([ex - 4 * K, ey - 4 * K, ex + 4 * K, ey + 4 * K], outline=(70, 115, 210, 50), width=2 * K)
for gx in range(GRID, W, GRID * 2):
    for gy in range(GRID, H, GRID * 2):
        if not in_keepout(gx, gy):
            x0, y0 = P((gx, gy))
            db.rectangle([x0, y0, x0 + K - 1, y0 + K - 1], fill=(80, 120, 210, 40))
bg.putalpha(bg.getchannel("A").point(lambda v: int(v * 0.9)))   # splash shows this layer at 90%
img.alpha_composite(bg)

# ------------------------------------------------------------ main traces (supersampled 2x on top of 4K)
SS = 2
core = Image.new("L", (WK * SS, HK * SS), 0)
dc = ImageDraw.Draw(core)
def Q(p):
    return (p[0] * K * SS, p[1] * K * SS)
u = K * SS
for pts in traces:
    dc.line([Q(p) for p in pts], fill=255, width=int(2.6 * u), joint="curve")
    sx, sy = Q(pts[0])
    if abs(pts[1][1] - pts[0][1]) < 0.5:
        dc.rectangle([sx - 5 * u, sy - 3.5 * u, sx + 5 * u, sy + 3.5 * u], fill=255)
    else:
        dc.rectangle([sx - 3.5 * u, sy - 5 * u, sx + 3.5 * u, sy + 5 * u], fill=255)
    ex, ey = Q(pts[-1])
    dc.ellipse([ex - 7.5 * u, ey - 7.5 * u, ex + 7.5 * u, ey + 7.5 * u], fill=255)
    dc.ellipse([ex - 3 * u, ey - 3 * u, ex + 3 * u, ey + 3 * u], fill=0)
core = core.resize((WK, HK), Image.LANCZOS)
glow = core.filter(ImageFilter.GaussianBlur(5 * K)).point(lambda v: int(min(255, v * 0.9)))
ca = np.asarray(core, np.float32) / 255 * 0.85
ga = np.asarray(glow, np.float32) / 255 * 0.45
oa = ca + ga * (1 - ca)
tr = np.zeros((HK, WK, 4), np.float32)
for c in range(3):
    tr[..., c] = (TRACE[c] * ca + TRACE_GLOW[c] * ga * (1 - ca)) / np.maximum(oa, 1e-6)
tr[..., 3] = oa * 255
img.alpha_composite(Image.fromarray(tr.clip(0, 255).astype(np.uint8), "RGBA"))

# ------------------------------------------------------------ optional frozen data pulses
def radial(size, stops):
    n = size
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot(x - (n - 1) / 2, y - (n - 1) / 2) / (n / 2)
    out = np.zeros((n, n, 4), np.float32)
    for c in range(4):
        out[..., c] = np.interp(r, [s[0] for s in stops], [s[1][c] for s in stops])
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")

def point_at(pts, s):
    for i in range(len(pts) - 1):
        L = math.dist(pts[i], pts[i + 1])
        if s <= L or i == len(pts) - 2:
            f = min(1, s / L) if L else 0
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f)
        s -= L

if PULSES:
    pb = radial(40 * K, [(0, (255, 255, 255, 255)), (0.18, (235, 245, 255, 255)), (0.4, (*BLUE_HOT, 150)), (1, (*TRACE_GLOW, 0))])
    pr = radial(40 * K, [(0, (255, 240, 240, 255)), (0.18, (255, 200, 205, 255)), (0.4, (*RED_HOT, 160)), (1, (*RED_HOT, 0))])
    tb = radial(22 * K, [(0, (200, 225, 255, 200)), (0.5, (*BLUE_HOT, 90)), (1, (*TRACE_GLOW, 0))])
    trd = radial(22 * K, [(0, (255, 200, 205, 200)), (0.5, (*RED_HOT, 90)), (1, (*RED_HOT, 0))])
    picks = [(1, 0.62, "b"), (4, 0.4, "r"), (9, 0.75, "b"), (12, 0.35, "b"), (14, 0.55, "r"), (17, 0.7, "b"), (20, 0.5, "b")]
    for ti, frac, col in picks:
        pts = traces[ti]
        L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        s = L * frac
        for back, im, op in ((32, trd if col == "r" else tb, 0.4), (16, trd if col == "r" else tb, 0.7), (0, pr if col == "r" else pb, 1.0)):
            x, y = point_at(pts, max(0, s - back))
            sprite = im.copy()
            sprite.putalpha(sprite.getchannel("A").point(lambda v, op=op: int(v * op)))
            img.alpha_composite(sprite, (int(x * K - sprite.width / 2), int(y * K - sprite.height / 2)))

# ------------------------------------------------------------ logo + glow at native 4K
LH = LOGO_H * K
lwk = round(logo_src.width * LH / logo_src.height)
logo = logo_src.resize((lwk, LH), Image.LANCZOS)
GPAD = 140 * K
a = logo.getchannel("A")
g = Image.new("L", (lwk + 2 * GPAD, LH + 2 * GPAD), 0)
g.paste(a, (GPAD, GPAD))
g = g.filter(ImageFilter.GaussianBlur(38 * K)).point(lambda v: min(255, int(v * 1.25)))
solid = np.asarray(a) > 20
lab, _ = ndimage.label(~solid)
border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
holes = np.isin(lab, [l for l in np.unique(lab) if l not in border and l != 0])
holes = ndimage.binary_dilation(holes, iterations=2 * K)
garr = np.asarray(g).copy()
garr[GPAD:GPAD + LH, GPAD:GPAD + lwk][holes] = 0
glow_img = Image.new("RGBA", g.size, (40, 100, 255, 0))
glow_img.putalpha(Image.fromarray(garr).point(lambda v: int(v * 0.85)))
lx = CX * K - lwk // 2
ly = LOGO_CY * K - LH // 2
img.alpha_composite(glow_img, (lx - GPAD, ly - GPAD))
img.alpha_composite(logo, (lx, ly))

# ------------------------------------------------------------ "BCS NOC" at native 4K
font = ImageFont.truetype(FONT, 92 * K)
font.set_variation_by_name("Black")
TEXT, SPACING = "BCS NOC", 20 * K
adv = [font.getlength(ch) for ch in TEXT]
asc, desc = font.getmetrics()
TP = 30 * K
t = Image.new("RGBA", (int(sum(adv) + SPACING * 6) + 2 * TP, asc + desc + 2 * TP), (0, 0, 0, 0))
dt = ImageDraw.Draw(t)
x = TP
for ch, ad in zip(TEXT, adv):
    dt.text((x, TP), ch, font=font, fill=(240, 245, 255, 255))
    x += ad + SPACING
t = t.crop(t.getbbox())
tf = Image.new("RGBA", (t.width + 2 * TP, t.height + 2 * TP), (0, 0, 0, 0))
tf.paste(t, (TP, TP))
halo = Image.new("RGBA", tf.size, (60, 120, 255, 0))
halo.putalpha(tf.getchannel("A").filter(ImageFilter.GaussianBlur(12 * K)).point(lambda v: int(v * 0.55)))
text_img = Image.alpha_composite(halo, tf)
img.alpha_composite(text_img, (CX * K - text_img.width // 2, TEXT_CY * K - text_img.height // 2))

# fine dither so the dark gradient doesn't band on big TVs
arr = np.asarray(img.convert("RGB"), np.float32)
arr += np.random.default_rng(1).uniform(-0.6, 0.6, arr.shape)
Image.fromarray(arr.clip(0, 255).astype(np.uint8)).save(OUT, optimize=True)
print("wrote", OUT)
