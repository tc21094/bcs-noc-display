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
    ext = {"open": "imrp", "fist": "", "point": "i", "victory": "im", "pinch": "mrp", "other": "ip"}[pose]
    pts = [(0.0, 0.0)] * 21
    pts[0] = (0.0, 0.0)
    if pose in ("fist", "point", "victory"):
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
    c, s = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    out = []
    for px, py in pts:
        rx, ry = px * c - py * s, px * s + py * c
        out.append([round(x + rx * palm, 5), round(y + ry * palm, 5)])
    # shift so (x, y) is the palm centre, as the engine measures it
    cx = (out[0][0] + out[5][0] + out[9][0] + out[17][0]) / 4
    cy = (out[0][1] + out[5][1] + out[9][1] + out[17][1]) / 4
    return {"pts": [[p[0] + x - cx, p[1] + y - cy] for p in out], "handed": handed}
