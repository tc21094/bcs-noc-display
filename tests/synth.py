"""Synthetic hands for testing bcs-gesture: 21 MediaPipe-style landmarks for a pose, placed in the frame."""
import math

# canonical right hand, palm toward the camera, as seen in the (mirrored) camera picture,
# wrist at 0,0, one unit = wrist to middle knuckle, y down (so the fingers point to -y)
MCP = {"index": (-0.35, -0.95), "middle": (0.0, -1.0), "ring": (0.3, -0.95), "pinky": (0.55, -0.85)}
SPREAD = {"index": -0.12, "middle": 0.0, "ring": 0.1, "pinky": 0.22}


def finger(name, extended):
    mx, my = MCP[name]
    a = SPREAD[name]
    ux, uy = math.sin(a), -math.cos(a)
    if extended:
        return [(mx + ux * k, my + uy * k) for k in (0.45, 0.75, 1.0)]       # pip, dip, tip
    return [(mx + ux * 0.32, my + uy * 0.32), (mx + 0.05, my + 0.05), (mx + 0.03, my + 0.2)]   # curled into the palm


def hand(pose="open", x=0.9, y=0.5, palm=0.1, tilt=0.0, handed="Right", facing=True):
    ext = {"open": "imrp", "fist": "", "point": "i", "victory": "im", "pinch": "mrp", "other": "ip", "thumb": ""}[pose]
    pts = [(0.0, 0.0)] * 21
    pts[0] = (0.0, 0.0)
    if pose == "thumb":                                  # thumbs up: a fist with the thumb sticking up
        thumb = [(-0.3, -0.25), (-0.5, -0.55), (-0.62, -0.92), (-0.75, -1.3)]
    elif pose in ("fist", "point", "victory"):
        thumb = [(-0.3, -0.25), (-0.45, -0.45), (-0.35, -0.62), (-0.15, -0.7)]     # tucked across the palm
    else:
        thumb = [(-0.3, -0.25), (-0.55, -0.45), (-0.75, -0.65), (-0.92, -0.8)]
    for i, p in enumerate(thumb):
        pts[1 + i] = p
    for name, base in (("index", 5), ("middle", 9), ("ring", 13), ("pinky", 17)):
        pts[base] = MCP[name]
        f = finger(name, name[0] in ext)
        for i, p in enumerate(f):
            pts[base + 1 + i] = p
    if pose == "pinch":                                  # index bends to meet the thumb tip
        pts[6], pts[7], pts[8] = (-0.5, -1.25), (-0.68, -1.25), (-0.8, -1.05)
        pts[3], pts[4] = (-0.72, -0.75), (-0.82, -1.0)
    if not facing:                                       # back of the hand: thumb on the other side
        pts = [(-px, py) for px, py in pts]
    if handed == "Left":                                 # mirror image of a right hand
        pts = [(-px, py) for px, py in pts]
    world = [[round(px * 0.09, 5), round(py * 0.09, 5), 0.0] for px, py in pts]   # metres, flat hand
    c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    out = []
    for px, py in pts:
        rx, ry = px * c - py * s, px * s + py * c
        out.append([round(x + rx * palm, 5), round(y + ry * palm, 5)])
    # shift so (x, y) is the palm centre, as the engine measures it
    cx = (out[0][0] + out[5][0] + out[9][0] + out[17][0]) / 4
    cy = (out[0][1] + out[5][1] + out[9][1] + out[17][1]) / 4
    return {"pts": [[p[0] + x - cx, p[1] + y - cy] for p in out], "handed": handed, "world": world}


def foreshortened_open(x=0.9, y=0.5, palm=0.1, k=0.45):
    """An open hand tipped back so the fingers point partly at the camera: in the picture they look
    short (k = how much of their length shows), but in 3D they're straight."""
    h = hand("open", x=x, y=y, palm=palm)
    w = h["world"]
    for base in (5, 9, 13, 17):
        mx, my = h["pts"][base]
        for j in range(1, 4):
            px, py = h["pts"][base + j]
            h["pts"][base + j] = [mx + (px - mx) * k, my + (py - my) * k]
            wx, wy, _ = w[base + j]
            bx, by, _ = w[base]
            # same straight finger, rotated toward the camera
            L = math.hypot(wx - bx, wy - by)
            w[base + j] = [bx + (wx - bx) * k, by + (wy - by) * k, -L * math.sqrt(1 - k * k)]
    return h
